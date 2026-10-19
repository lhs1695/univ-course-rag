import json
from unittest.mock import Mock

import pytest
from app.config import Settings
from app.main import app
from app.models.course import CourseMemberRole
from app.models.document import EMBEDDING_DIM
from app.models.query_log import QueryLog
from app.models.user import UserRole
from app.services.embedder import FakeEmbedder
from app.services.generate import NO_EVIDENCE
from app.services.llm import FakeLLM, get_llm
from app.services.query_expansion import (
    expand_calculation_subqueries,
    expand_subqueries,
    is_broad_procedural,
    parse_subqueries,
)
from app.services.retrieve import cosine_similarity, retrieve_expanded_chunks
from app.services.upstream import UpstreamUnavailable
from sqlalchemy import select

from tests.conftest import add_user
from tests.test_retrieve import _scaled_chunk, add_course, add_member, login_as


def test_parse_subqueries():
    raw = "1. 原问题？\n- \n1、 子问题一\n• 子问题一\n- 子问题二\n3. 子问题三"
    assert parse_subqueries(raw, "原问题?") == ["子问题一", "子问题二"]
    assert parse_subqueries("- " + "长" * 250, "原问题") == ["长" * 200]


@pytest.mark.parametrize("query, expected", [
    ("如何解线性方程组", True),
    ("什么是工作分析（职位分析）？", False),
    ("如何" + "这是一个明确而具体的长问题" * 4, False),
    ("  求解步骤  ", True),
])
def test_is_broad_procedural(query, expected):
    assert is_broad_procedural(query) is expected


def test_expand_subqueries_and_exact_prompt():
    llm = FakeLLM(scripted="子问题一\n子问题二")
    assert expand_subqueries(" 原问题 ", llm) == ["子问题一", "子问题二"]
    assert llm.prompts == [
        "把下面宽泛的学生问题改写成2个更具体的检索子问题，每行一个，只输出子问题，不要编号，不要解释。要求：子问题必须指向具体的求解方法、算法步骤或判定准则，避免只问定义；如果该问题在教材中通常对应一种具体方法，应在子问题中写出该方法的名称。\n问题：原问题"
    ]
    assert expand_subqueries("问题", Mock(generate=Mock(side_effect=RuntimeError))) == []


def test_expand_calculation_subqueries_prompt_and_bounded_parser():
    query = "3个红球和2个白球，求红球概率"
    llm = FakeLLM(scripted=(
        f"{query}\n1. 古典概型中事件概率的计算公式？\n"
        "- 古典概型中事件概率的计算公式？\n• 等可能事件的概率公式\n第三个子问题"
    ))
    assert expand_calculation_subqueries(query, llm) == [
        "古典概型中事件概率的计算公式？", "等可能事件的概率公式",
    ]
    assert len(llm.prompts) == 1
    prompt = llm.prompts[0]
    assert "最多2个" in prompt
    assert "只输出指向方法/公式/定理名称的子问题" in prompt
    assert "不要带原题的具体数字（包括中文数字）" in prompt
    assert prompt.endswith(f"计算题：{query}")


@pytest.mark.parametrize("result", ["", "  ", RuntimeError(), UpstreamUnavailable()])
def test_calculation_expansion_failure_or_empty_degrades(result):
    llm = Mock(generate=Mock(side_effect=result) if isinstance(result, Exception)
               else Mock(return_value=result))
    assert expand_calculation_subqueries("计算1+2", llm) == []
    llm.generate.assert_called_once()


class GeometryEmbedder(FakeEmbedder):
    def embed(self, texts):
        return [([1.0, 0.0] if text == "original" else [0.0, 1.0])
                + [0.0] * (EMBEDDING_DIM - 2) for text in texts]


@pytest.mark.parametrize("threshold", [None, 0.45])
def test_expanded_round_robin_original_gate_scores_and_scope(db, threshold):
    embedder = GeometryEmbedder()
    course = add_course(db, "Expanded")

    def chunk(x, y, owner=course):
        item = _scaled_chunk(db, owner, embedder, "original", "body", 1)
        item.embedding = [x, y] + [0.0] * (EMBEDDING_DIM - 2)
        db.commit()
        return item

    original = chunk(1, 0)
    support = chunk(0.6, 0.8)
    below = chunk(0.1, 0.995)
    excluded = chunk(0.7, 0.9)
    chunk(0.8, 0.95, add_course(db, "Other"))
    hits = retrieve_expanded_chunks(
        db, course.id, "original", embedder, ["sub1", "sub2"],
        min_score=threshold, excluded_document_ids=[excluded.document_id],
    )
    # Depth 0: both subbranches fail the original gate; original is admitted.
    # Depth 1: the first subbranch admits support, the second is a duplicate.
    assert [hit.chunk_id for hit in hits] == [original.id, support.id]
    assert below.id not in {hit.chunk_id for hit in hits}
    assert hits[1].score == pytest.approx(cosine_similarity(
        embedder.embed(["original"])[0], support.embedding,
    ))
    assert (hits[1].page, hits[1].snippet) == (support.page, support.text)
    db.delete(below)
    db.commit()
    hits = retrieve_expanded_chunks(
        db, course.id, "original", embedder, ["sub1", "sub2"], top_k=2,
        excluded_document_ids=[excluded.document_id],
    )
    assert [hit.chunk_id for hit in hits] == [support.id, original.id]


def test_empty_subqueries_skip_all_work():
    assert retrieve_expanded_chunks(Mock(), Mock(), "query", Mock(), []) == []


class SequenceLLM:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def setup_ask(client, db, monkeypatch, query, backend="llm"):
    teacher = add_user(db, "expansion-teacher", "pass", UserRole.teacher)
    course = add_course(db, "Ask expansion")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "expansion-teacher", "pass")
    support = _scaled_chunk(db, course, FakeEmbedder(), query, "具体方法：消元后回代。", 1)
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(
        _env_file=None, query_expansion_backend=backend,
    ))
    return course, support


def test_broad_uncited_first_generation_retries_and_logs_final_hits(client, db, monkeypatch):
    query = "如何解线性方程组"
    course, support = setup_ask(client, db, monkeypatch, query)
    # An empty pre-expansion degrades; uncited generation can still retry expansion.
    llm = SequenceLLM(["", NO_EVIDENCE, "消元法步骤\n回代求解", f"回代 [Source {support.id}]"])
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    assert response.json()["error_code"] is None
    assert response.json()["citations"][0]["chunk_id"] == str(support.id)
    assert len(llm.prompts) == 4
    log = db.scalar(select(QueryLog))
    assert log.outcome == "cited_answer"
    assert json.loads(log.chunk_ids) == [str(support.id)]


@pytest.mark.parametrize("query, responses", [
    ("如何预测明天彩票", ["彩票预测步骤\n彩票预测方法", NO_EVIDENCE]),
    ("明天彩票号码是什么", [NO_EVIDENCE, "彩票预测步骤\n彩票预测方法", NO_EVIDENCE]),
])
def test_refusal_stays_no_evidence_after_expansion(client, db, monkeypatch, query, responses):
    course, _ = setup_ask(client, db, monkeypatch, query)
    llm = SequenceLLM(responses)
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.json()["error_code"] == NO_EVIDENCE
    assert response.json()["answer"] is None
    assert response.json()["citations"] == []
    assert len(llm.prompts) == len(responses)
    assert db.scalar(select(QueryLog)).outcome == "no_evidence"


def test_generation_upstream_failure_is_not_swallowed(client, db, monkeypatch):
    query = "如何解线性方程组"
    course, _ = setup_ask(client, db, monkeypatch, query)
    llm = SequenceLLM(["消元法步骤", UpstreamUnavailable()])
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 503
    assert db.scalar(select(QueryLog)).outcome == "failure"


@pytest.mark.parametrize("backend", ["disabled", "LLM", "unknown"])
def test_only_exact_llm_enables_expansion(client, db, monkeypatch, backend):
    query = "如何解线性方程组"
    course, _ = setup_ask(client, db, monkeypatch, query, backend)
    llm = SequenceLLM([NO_EVIDENCE])
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.json()["error_code"] == NO_EVIDENCE
    assert len(llm.prompts) == 1
