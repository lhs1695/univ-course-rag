"""Ask tests use FakeLLM. Do not change golden.json to fit generation."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.config import Settings
from app.main import app
from app.models.course import CourseMember, CourseMemberRole
from app.models.document import Chunk
from app.models.query_log import QueryLog
from app.models.user import UserRole
from app.services import generate
from app.services.embedder import FakeEmbedder, get_embedder
from app.services.fusion import FusionError
from app.services.generate import NO_EVIDENCE, assemble_ask_context, generate_answer
from app.services.keyword import KeywordLimitExceeded
from app.services.llm import FakeLLM, get_llm, parse_cited_ids
from app.services.question_shape import INVALID_QUESTION_MESSAGE, NEEDS_CONTEXT_MESSAGE
from app.services.rerank import FakeReranker, RerankError, RerankTimeout, get_reranker
from app.services.retrieve import (
    EMBEDDING_MISMATCH,
    SearchHit,
    retrieve_chunks,
    retrieve_hybrid_candidates,
)
from app.services.upstream import (
    UPSTREAM_UNAVAILABLE,
    UpstreamTimeout,
    UpstreamUnavailable,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_retrieve import (
    FIXTURES,
    GOLDEN,
    UNRELATED,
    _scaled_chunk,
    add_course,
    add_member,
    login_as,
    upload,
)


def evidence_hit(text: str = "检索摘要") -> SearchHit:
    return SearchHit(uuid4(), uuid4(), None, text, 1.0)


@pytest.mark.parametrize("calc_result", ["cited", "uncited", "empty", "failure", "refused"])
def test_calculation_method_retry_keeps_gate_and_bounds_calls(
    client, db, monkeypatch, calc_result,
):
    query = "一个袋子里有 3 个红球和 2 个白球，随机摸出一个球是红球的概率是多少？请给出计算过程。"
    method_query = "古典概型中事件概率的计算公式"

    class MethodEmbedder(FakeEmbedder):
        def embed(self, texts):
            return [([0.0, 1.0] if text == method_query else [1.0, 0.0])
                    + [0.0] * 1022 for text in texts]

    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Calculation retry")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = MethodEmbedder()
    app.dependency_overrides[get_embedder] = lambda: embedder
    for _ in range(8):
        _scaled_chunk(db, course, embedder, query, "概率章节目录", 1.0)
    method = _scaled_chunk(db, course, embedder, query, "古典概型：P(A)=k/n。", 1.0)
    method.embedding = [0.6, 0.8] + [0.0] * 1022
    method.page = 55
    below = _scaled_chunk(db, course, embedder, query, "不应准入的方法页", 1.0)
    below.embedding = [0.1, 0.995] + [0.0] * 1022
    db.commit()
    assert method.id not in {
        hit.chunk_id for hit in retrieve_chunks(db, course.id, query, embedder)
    }
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(
        _env_file=None, query_expansion_backend="llm",
    ))

    class MethodLLM:
        def __init__(self):
            self.calls = []
            self.prompts = []

        def generate(self, prompt):
            self.prompts.append(prompt)
            if prompt.startswith("把下面计算题"):
                self.calls.append("calc")
                if calc_result == "failure":
                    raise RuntimeError("expansion unavailable")
                return "" if calc_result == "empty" else method_query
            if prompt.startswith("把下面宽泛"):
                self.calls.append("generic")
                return method_query
            self.calls.append("generate")
            assert str(below.id) not in prompt
            if f"[Source {method.id}]" not in prompt or calc_result == "refused":
                return NO_EVIDENCE
            if calc_result == "uncited" and "generic" not in self.calls:
                return NO_EVIDENCE
            return f"P(A)=3/(3+2)=3/5。 [Source {method.id}]"

    llm = MethodLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    body = response.json()
    if calc_result == "refused":
        assert body["error_code"] == NO_EVIDENCE
        assert body["answer"] is None
        assert body["citations"] == []
    else:
        assert body["error_code"] is None
        assert "3/5" in body["answer"]
        assert [(hit["chunk_id"], hit["page"]) for hit in body["citations"]] == [
            (str(method.id), 55),
        ]
    expected = ["generate", "calc"]
    if calc_result not in {"empty", "failure"}:
        expected.append("generate")
    if calc_result != "cited":
        expected.extend(["generic", "generate"])
    assert llm.calls == expected


@pytest.mark.parametrize("query", ["什么是教学？", "第三章的主题是什么", "如何解线性方程组"])
def test_non_calculation_never_calls_calculation_expansion(client, db, monkeypatch, query):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "No calculation expansion")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    _scaled_chunk(db, course, FakeEmbedder(), query, "课程目录", 1.0)
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(
        _env_file=None, query_expansion_backend="llm",
    ))
    calc = Mock(side_effect=AssertionError("non-calculation must skip calc expansion"))
    monkeypatch.setattr("app.api.ask.expand_calculation_subqueries", calc)
    llm = FakeLLM(scripted=NO_EVIDENCE)
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    assert response.json()["error_code"] == NO_EVIDENCE
    assert response.json()["citations"] == []
    calc.assert_not_called()


@pytest.mark.parametrize(("query", "code", "message", "extra"), [
    ("为什么？", "NEEDS_CONTEXT", NEEDS_CONTEXT_MESSAGE, {}),
    ("它呢？", "NEEDS_CONTEXT", NEEDS_CONTEXT_MESSAGE, {"previous_answer": "只有回答"}),
    ("它呢？", "NEEDS_CONTEXT", NEEDS_CONTEXT_MESSAGE, {"previous_question": "  "}),
    ("？！∑🙂", "INVALID_QUESTION", INVALID_QUESTION_MESSAGE, {}),
])
def test_question_shape_refusal_skips_all_ai_and_retrieval(
    client, db, monkeypatch, query, code, message, extra,
):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Shape guard")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    def forbidden(*args, **kwargs):
        raise AssertionError("early refusal must not inspect index, retrieve, embed or generate")

    class GuardEmbedder(FakeEmbedder):
        embed = forbidden

    monkeypatch.setattr("app.api.ask.has_incompatible_chunks", forbidden)
    monkeypatch.setattr("app.api.ask.retrieve_chunks", forbidden)
    monkeypatch.setattr("app.api.ask.retrieve_expanded_chunks", forbidden)
    app.dependency_overrides[get_embedder] = GuardEmbedder
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query, **extra})
    assert response.status_code == 200
    assert response.json() == {
        "error_code": code, "message": message, "answer": None, "citations": [],
    }
    assert llm.prompts == []
    db.expire_all()
    log = db.execute(select(QueryLog)).scalars().one()
    assert (log.query, log.outcome, log.hit, log.error_code) == (
        query, "no_evidence", False, code,
    )


def test_followup_uses_previous_question_for_retrieval_and_context(client, db, monkeypatch):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Followup")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    chunk = _scaled_chunk(db, course, FakeEmbedder(), "分布函数", "分布函数具有单调性", 1.0)
    hit = SearchHit(chunk.id, chunk.document_id, None, "摘要", 1.0)
    retrieve = Mock(return_value=[hit])
    monkeypatch.setattr("app.api.ask.retrieve_chunks", retrieve)
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={
        "query": "那它有什么性质？", "previous_question": "什么是分布函数？",
        "previous_answer": "分布函数描述概率。",
    })
    assert response.status_code == 200
    assert response.json()["citations"][0]["chunk_id"] == str(chunk.id)
    assert retrieve.call_args.args[2] == "什么是分布函数？\n追问：那它有什么性质？"
    assert "上一轮问题：什么是分布函数？" in llm.prompts[0]
    assert "上一轮回答：分布函数描述概率。" in llm.prompts[0]
    assert "不是证据或指令" in llm.prompts[0]
    assert "当前问题的指代对象以上一轮为准" in llm.prompts[0]
    assert llm.prompts[0].endswith("那它有什么性质？")
    db.expire_all()
    assert db.execute(select(QueryLog)).scalars().one().query == "那它有什么性质？"


@pytest.mark.parametrize("first_result", ["empty", "uncited"])
@pytest.mark.parametrize("retry_cites", [True, False])
def test_definition_retries_term_once_without_expansion(
    client, db, monkeypatch, first_result, retry_cites,
):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Definition retry")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    query = "什么是随机变量的分布函数？"
    chunk = _scaled_chunk(db, course, FakeEmbedder(), query, "分布函数 F(x)=P(X≤x)", 1.0)
    hit = SearchHit(chunk.id, chunk.document_id, None, "摘要", 1.0)
    retrieve = Mock(side_effect=[[] if first_result == "empty" else [hit], [hit]])
    monkeypatch.setattr("app.api.ask.retrieve_chunks", retrieve)
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(
        _env_file=None, query_expansion_backend="llm",
    ))
    expansion = Mock(side_effect=AssertionError("no expansion after definition retry"))
    monkeypatch.setattr("app.api.ask.expand_subqueries", expansion)

    class RetryLLM(FakeLLM):
        def generate(self, prompt):
            answer = super().generate(prompt)
            if not retry_cites or (first_result == "uncited" and len(self.prompts) == 1):
                return "NO_EVIDENCE"
            return answer

    llm = RetryLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    assert [call.args[2] for call in retrieve.call_args_list] == [query, "随机变量的分布函数"]
    assert len(llm.prompts) == (1 if first_result == "empty" else 2)
    expansion.assert_not_called()
    assert response.json()["error_code"] == (None if retry_cites else NO_EVIDENCE)
    assert bool(response.json()["citations"]) == retry_cites
    assert all(prompt.endswith(query) for prompt in llm.prompts)


@pytest.mark.parametrize("field, limit", [("previous_question", 2000), ("previous_answer", 6000)])
def test_previous_context_fields_are_optional_and_bounded(field, limit):
    from app.api.schemas import AskRequest
    from pydantic import ValidationError

    assert AskRequest(query="问题").previous_question is None
    AskRequest(query="问题", **{field: "字" * limit})
    with pytest.raises(ValidationError):
        AskRequest(query="问题", **{field: "字" * (limit + 1)})


def test_generation_context_orders_equal_summary_hits_and_explains_calculation_contract():
    summary, definition, lower = evidence_hit(), evidence_hit(), evidence_hit()
    lower.score = 0.9
    chunks = {
        summary.chunk_id: Chunk(text="本章小结：分布函数"),
        definition.chunk_id: Chunk(text="F(x)=P(X≤x)"),
        lower.chunk_id: Chunk(text="低分正文"),
    }
    context = assemble_ask_context("计算 F(3)", [summary, definition, lower], chunks)
    assert parse_cited_ids(context.prompt) == [definition.chunk_id, summary.chunk_id, lower.chunk_id]
    assert "引用方法来源" in context.prompt
    assert "结果是按课件方法计算得出" in context.prompt
    assert "来源没有适用方法时只输出 NO_EVIDENCE" in context.prompt
    assert "只支持一部分时直接呈现被支持部分，不解释缺失" in context.prompt
    assert "禁止元叙述式自贬" in context.prompt
    pedagogy = assemble_ask_context(
        "简述教学过程的基本环节",
        [definition],
        {definition.chunk_id: Chunk(text="教学过程分为四个阶段：明了、联想")},
    )
    assert "不得仅因未出现「基本环节」四字而输出 NO_EVIDENCE" in pedagogy.prompt
    course = assemble_ask_context(
        "什么是课程？",
        [definition],
        {definition.chunk_id: Chunk(text="教育内容主要体现为课程")},
    )
    assert "不得仅因缺少「课程是……」整句定义而输出 NO_EVIDENCE" in course.prompt


@pytest.mark.parametrize("budget_delta, expected_count", [(-1, 0), (0, 1), (1, 1)])
def test_context_budget_counts_complete_source_blocks(
    monkeypatch: pytest.MonkeyPatch, budget_delta: int, expected_count: int
) -> None:
    first, second = evidence_hit(), evidence_hit()
    body = "预算内证据"
    block = f"[Source {first.chunk_id}]\n{body}\n"
    monkeypatch.setattr(generate, "CONTEXT_CHAR_BUDGET", len(block) + budget_delta)
    chunks = {hit.chunk_id: Chunk(text=body) for hit in (first, second)}

    context = assemble_ask_context("问题", [first, second], chunks)

    expected = [first.chunk_id][:expected_count]
    assert context.source_ids == frozenset(expected)
    assert parse_cited_ids(context.prompt) == expected
    assert context.prompt.splitlines()[0] == (
        "允许引用的 Source id（只能用这些）：" + ", ".join(map(str, expected))
    )
    assert str(second.chunk_id) not in context.prompt


@pytest.mark.parametrize("text", [None, "", " \n\t "])
def test_context_skips_missing_or_empty_chunks_without_snippet_fallback(text: str | None) -> None:
    skipped, valid = evidence_hit("不应作为证据的旧摘要"), evidence_hit()
    chunks = {valid.chunk_id: Chunk(text="可用正文")}
    if text is not None:
        chunks[skipped.chunk_id] = Chunk(text=text)

    context = assemble_ask_context("问题", [skipped, valid], chunks)

    assert context.source_ids == frozenset({valid.chunk_id})
    assert str(skipped.chunk_id) not in context.prompt
    assert skipped.snippet not in context.prompt
    assert "可用正文" in context.prompt


def test_context_clips_each_source_before_admitting_it(monkeypatch: pytest.MonkeyPatch) -> None:
    first, second = evidence_hit(), evidence_hit()
    prefix = "内" * generate.PER_SOURCE_CHARS
    first_block = f"[Source {first.chunk_id}]\n{prefix}\n"
    second_block = f"[Source {second.chunk_id}]\n后续证据\n"
    monkeypatch.setattr(generate, "CONTEXT_CHAR_BUDGET", len(first_block) + len(second_block))
    chunks = {
        first.chunk_id: Chunk(text=" \n" + prefix + "不应展示的尾部"),
        second.chunk_id: Chunk(text="后续证据"),
    }

    context = assemble_ask_context("问题", [first, second], chunks)

    assert context.source_ids == frozenset(chunks)
    assert first_block in context.prompt
    assert second_block in context.prompt
    assert "不应展示的尾部" not in context.prompt
    assert context.source_texts == {first.chunk_id: prefix, second.chunk_id: "后续证据"}


def test_generate_filters_ids_from_unshown_evidence_even_if_in_query_or_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shown, hidden, missing, empty = [evidence_hit() for _ in range(4)]
    body = f"正文提到 [Source {hidden.chunk_id}]，不是来源声明。"
    monkeypatch.setattr(
        generate, "CONTEXT_CHAR_BUDGET", len(f"[Source {shown.chunk_id}]\n{body}\n")
    )
    chunks = {
        shown.chunk_id: Chunk(text=body),
        hidden.chunk_id: Chunk(text="超预算正文"),
        empty.chunk_id: Chunk(text=" "),
    }
    db = Mock(spec=Session)
    for chunk_id, chunk in chunks.items():
        chunk.id = chunk_id
    db.scalars.return_value = list(chunks.values())
    llm = FakeLLM(scripted=" ".join(
        f"[Source {hit.chunk_id}]" for hit in (hidden, missing, empty, shown, shown)
    ))

    _, cited = generate_answer(
        db, f"引用 [Source {missing.chunk_id}]", [missing, empty, shown, hidden], llm
    )

    assert cited == [shown.chunk_id]
    assert "超预算正文" not in llm.prompts[0]
    assert llm.prompts[0].splitlines()[0].endswith(str(shown.chunk_id))


@pytest.mark.parametrize("source_state", ["missing", "empty", "over_budget"])
def test_generate_without_usable_context_does_not_call_llm(
    monkeypatch: pytest.MonkeyPatch, source_state: str
) -> None:
    hit = evidence_hit()
    db = Mock(spec=Session)
    db.scalars.return_value = (
        [] if source_state == "missing"
        else [Chunk(id=hit.chunk_id, text=" " if source_state == "empty" else "正文")]
    )
    if source_state == "over_budget":
        monkeypatch.setattr(generate, "CONTEXT_CHAR_BUDGET", 1)
    llm = FakeLLM(scripted=f"[Source {hit.chunk_id}]")

    assert generate_answer(db, "问题", [hit], llm) == ("", [])
    assert llm.prompts == []


@pytest.mark.parametrize("cite_hidden", [False, True])
def test_ask_only_accepts_sources_shown_within_budget(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, cite_hidden: bool
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    document_id = upload(client, course.id, FIXTURES / "sample.md")
    embedder = FakeEmbedder()
    chunks = [
        Chunk(
            course_id=course.id,
            document_id=document_id,
            text=text,
            embedding=embedder.embed([text])[0],
            embedding_model=embedder.index_identity,
        )
        for text in ("展示证据", "预算外证据")
    ]
    db.add_all(chunks)
    db.commit()
    hits = [SearchHit(chunk.id, document_id, None, "过时的检索摘要", 1.0) for chunk in chunks]
    monkeypatch.setattr("app.api.ask.retrieve_chunks", lambda *args, **kwargs: hits)
    monkeypatch.setattr(
        generate, "CONTEXT_CHAR_BUDGET", len(f"[Source {chunks[0].id}]\n展示证据\n")
    )
    llm = FakeLLM(scripted=f"回答 [Source {chunks[int(cite_hidden)].id}]")
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": "合成问题"})

    assert response.status_code == 200
    body = response.json()
    if cite_hidden:
        assert body["error_code"] == NO_EVIDENCE
        assert body["answer"] is None
        assert body["citations"] == []
    else:
        assert body["error_code"] is None
        assert [item["chunk_id"] for item in body["citations"]] == [str(chunks[0].id)]
        assert body["citations"][0]["snippet"] == "展示证据"
    assert str(chunks[1].id) not in llm.prompts[0]


def test_same_terms_without_answer_can_refuse_even_after_retrieval_admission(
    client, db,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Synthetic insufficient source")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    query = "事务隔离级别包括哪些？"
    _scaled_chunk(db, course, FakeEmbedder(), query, "事务隔离级别：目录，正文略。", 1.0)
    # Scripted refusal tests the contract, not a Fake semantic classifier.
    llm = FakeLLM(scripted="NO_EVIDENCE")
    app.dependency_overrides[get_llm] = lambda: llm

    body = client.post(f"/courses/{course.id}/ask", json={"query": query}).json()

    assert body["error_code"] == NO_EVIDENCE
    assert body["answer"] is None
    assert body["citations"] == []
    assert "目录，正文略。" in llm.prompts[0]
    assert "有合法编号不代表有答案" in llm.prompts[0]
    log = db.execute(select(QueryLog)).scalars().one()
    assert log.hit is True  # Existing retrieval-event meaning; P4 will revise statistics.
    assert log.error_code == NO_EVIDENCE


def test_each_ask_attempt_records_final_result_and_role_at_start(client, db) -> None:
    user = add_user(db, "course-student", "pass", UserRole.teacher)
    course = add_course(db, "Outcome snapshots")
    add_member(db, course, user, CourseMemberRole.student)
    login_as(client, user.username, "pass")
    query = "合成概念定义"
    _scaled_chunk(db, course, FakeEmbedder(), query, query + "：合成定义。", 1.0)
    member = db.scalar(select(CourseMember).where(CourseMember.course_id == course.id))

    class RetryLLM:
        calls = 0

        def generate(self, prompt):
            self.calls += 1
            if self.calls == 1:
                return NO_EVIDENCE
            # A role change during generation must not overwrite the entry snapshot.
            member.role = "teacher"
            db.flush()
            return f"合成定义 [Source {parse_cited_ids(prompt)[0]}]"

    # Use one adapter instance across the explicit retry.
    llm = RetryLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    before = datetime.now(UTC)
    first = client.post(f"/courses/{course.id}/ask", json={"query": query})
    second = client.post(f"/courses/{course.id}/ask", json={"query": query})
    after = datetime.now(UTC)

    assert first.json()["error_code"] == NO_EVIDENCE
    assert second.json()["citations"]
    logs = db.scalars(select(QueryLog).order_by(QueryLog.created_at)).all()
    assert [log.outcome for log in logs] == ["no_evidence", "cited_answer"]
    assert [log.member_role_at_ask for log in logs] == ["student", "student"]
    assert all(log.hit for log in logs)  # Retrieval has evidence in both attempts.
    assert logs[0].id != logs[1].id
    assert all(before <= log.created_at.replace(tzinfo=UTC) <= after for log in logs)
    summary = client.get(f"/courses/{course.id}/insights").json()["summary"]
    assert summary["recorded_attempts"] == 2
    assert summary["no_evidence_rate"] == 0.5


def test_ask_no_hit_does_not_call_llm(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": UNRELATED})
    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] == NO_EVIDENCE
    assert body["answer"] is None
    assert body["citations"] == []
    assert "依据不足" in (body["message"] or "")
    assert llm.prompts == []
    db.expire_all()
    log = db.execute(select(QueryLog)).scalars().one()
    assert log.hit is False
    assert log.outcome == "no_evidence"
    assert log.member_role_at_ask == "teacher"
    assert json.loads(log.chunk_ids) == []
    assert log.duration_ms >= 0
    assert "sk-" not in (log.query or "")


def test_reranking_changes_actual_context_order_and_preserves_citations(client, db, monkeypatch) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Reranked context")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query + "目录", 0.9)
    support = _scaled_chunk(db, course, embedder, query, query + "包括读未提交和读已提交。", 0.4)
    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder)
    fake = FakeReranker([0.9 if hit.chunk_id == support.id else 0.1 for hit in candidates])
    llm = FakeLLM()
    app.dependency_overrides[get_reranker] = lambda: fake
    app.dependency_overrides[get_llm] = lambda: llm
    _hybrid_settings(monkeypatch)

    response = client.post(f"/courses/{course.id}/ask", json={"query": query})

    assert response.status_code == 200
    assert response.json()["error_code"] is None
    assert response.json()["citations"][0]["chunk_id"] == str(support.id)
    assert "包括读未提交和读已提交。" in llm.prompts[0]
    assert len(fake.calls) == 1


def test_high_rerank_score_for_no_answer_does_not_authorize_generation(client, db, monkeypatch) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "No supported evidence")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    query = "事务隔离级别"
    _scaled_chunk(db, course, FakeEmbedder(), query, query + "目录，具体内容略。", 0.01)
    fake = FakeReranker([0.999])
    llm = FakeLLM()
    app.dependency_overrides[get_reranker] = lambda: fake
    app.dependency_overrides[get_llm] = lambda: llm
    _hybrid_settings(monkeypatch)
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.json()["error_code"] == NO_EVIDENCE
    assert response.json()["citations"] == []
    assert fake.calls
    assert llm.prompts == []
    assert db.execute(select(QueryLog)).scalars().one().error_code == NO_EVIDENCE


@pytest.mark.parametrize("error, status", [(RerankError, 503), (RerankTimeout, 504)])
def test_rerank_failures_are_logged_without_fallback_or_provider_details(
    client, db, monkeypatch, caplog, error, status,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Rerank failure")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    query = "事务隔离级别"
    _scaled_chunk(db, course, FakeEmbedder(), query, query, 1.0)
    fake = Mock()
    fake.score.side_effect = error("provider-private-secret")
    llm = FakeLLM()
    app.dependency_overrides[get_reranker] = lambda: fake
    app.dependency_overrides[get_llm] = lambda: llm
    _hybrid_settings(monkeypatch)
    with caplog.at_level(logging.INFO):
        response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == status
    assert response.json()["error_code"] == error.error_code
    assert response.json()["answer"] is None
    assert response.json()["citations"] == []
    assert "provider-private-secret" not in response.text + caplog.text
    assert query not in caplog.text
    assert llm.prompts == []
    log = db.execute(select(QueryLog)).scalars().one()
    assert log.error_code == error.error_code
    assert log.hit is False
    assert json.loads(log.chunk_ids) == []


@pytest.mark.parametrize("blocked", ["membership", "index"])
def test_unauthorized_or_mismatched_queries_never_send_text_to_reranker(
    client, db, monkeypatch, blocked,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Rerank authorization")
    if blocked != "membership":
        add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    query = "事务隔离级别"
    chunk = _scaled_chunk(db, course, FakeEmbedder(), query, query, 1.0)
    if blocked == "index":
        chunk.embedding_model = "incompatible"
        db.commit()
    fake = FakeReranker()
    app.dependency_overrides[get_reranker] = lambda: fake
    _hybrid_settings(monkeypatch)
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == (403 if blocked == "membership" else 200)
    if blocked == "index":
        assert response.json()["error_code"] == EMBEDDING_MISMATCH
    assert fake.calls == []


def test_ask_drops_illegal_citation_ids(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")

    class IllegalLLM:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str) -> str:
            self.prompts.append(prompt)
            allowed = parse_cited_ids(prompt)
            assert allowed
            return f"编造 [Source {uuid4()}] 以及真实 [Source {allowed[0]}]"

    llm = IllegalLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(
        f"/courses/{course.id}/ask",
        json={"query": GOLDEN[0]["query"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] is None
    assert body["answer"]
    cited = {item["chunk_id"] for item in body["citations"]}
    assert cited
    allowed_in_prompt = {str(item) for item in parse_cited_ids(llm.prompts[0])}
    assert cited <= allowed_in_prompt
    assert len(cited) == 1


def test_ask_rejects_incompatible_index_without_calling_llm(
    client: TestClient, db: Session
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")

    class DifferentBackendEmbedder(FakeEmbedder):
        def __init__(self) -> None:
            super().__init__(model_name="fake-bge-m3")
            self.index_identity = "siliconflow|fake-bge-m3|1024|v1"

    llm = FakeLLM()
    app.dependency_overrides[get_embedder] = DifferentBackendEmbedder
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})

    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] == EMBEDDING_MISMATCH
    assert body["answer"] is None
    assert body["citations"] == []
    assert "重新入库" in (body["message"] or "")
    assert llm.prompts == []


def test_ask_rejects_mixed_index_without_calling_llm(
    client: TestClient, db: Session
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    document_id = upload(client, course.id, FIXTURES / "sample.md")
    embedder = FakeEmbedder()
    db.add(
        Chunk(
            course_id=course.id,
            document_id=document_id,
            text="旧索引切片",
            embedding=embedder.embed([GOLDEN[0]["query"]])[0],
            embedding_model="BAAI/bge-m3",
        )
    )
    db.commit()
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})

    assert response.status_code == 200
    assert response.json()["error_code"] == EMBEDDING_MISMATCH
    assert llm.prompts == []


@pytest.mark.parametrize("answer", [
    "没有引用的回答。", "编造 [Source 00000000-0000-0000-0000-000000000000]", "NO_EVIDENCE", " "
])
def test_ask_with_hits_but_no_legal_citations_is_no_evidence(
    client: TestClient, db: Session, answer: str
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")
    llm = FakeLLM(scripted=answer)
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})

    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] == NO_EVIDENCE
    assert body["answer"] is None
    assert body["citations"] == []
    assert llm.prompts
    db.expire_all()
    log = db.execute(select(QueryLog)).scalars().one()
    assert log.hit is True
    assert log.error_code == NO_EVIDENCE


def test_ask_golden_citations(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    login_as(client, "t1", "pass")
    by_file = {
        "sample.md": upload(client, course.id, FIXTURES / "sample.md"),
        "sample.pdf": upload(client, course.id, FIXTURES / "sample.pdf"),
    }
    login_as(client, "alice", "pass")
    item = GOLDEN[0]
    response = client.post(f"/courses/{course.id}/ask", json={"query": item["query"]})
    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] is None
    assert body["answer"]
    assert body["citations"]
    expected_doc = str(by_file[item["source_file"]])
    assert any(
        hit["document_id"] == expected_doc and item["expect_substring"] in hit["snippet"]
        for hit in body["citations"]
    )
    assert all(
        hit["content_url"]
        == f"/courses/{course.id}/documents/{hit['document_id']}/content"
        for hit in body["citations"]
    )


def test_ask_after_document_deleted_is_no_evidence(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    login_as(client, "t1", "pass")
    doc_id = upload(client, course.id, FIXTURES / "sample.md")
    login_as(client, "alice", "pass")
    before = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})
    assert before.status_code == 200
    assert before.json()["error_code"] is None
    login_as(client, "t1", "pass")
    deleted = client.delete(f"/courses/{course.id}/documents/{doc_id}")
    assert deleted.status_code == 204
    login_as(client, "alice", "pass")
    after = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})
    assert after.status_code == 200
    assert after.json()["error_code"] == NO_EVIDENCE
    assert after.json()["answer"] is None


def test_ask_does_not_cite_other_course(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course1 = add_course(db, "Course 1")
    course2 = add_course(db, "Course 2")
    add_member(db, course1, teacher, CourseMemberRole.teacher)
    add_member(db, course2, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course1.id, FIXTURES / "sample.md")
    closer = (
        "course_id-alpha-9371 course_id-alpha-9371 向量绑定口令 向量绑定口令 "
        "课2独占更相似正文 omega-course-two"
    ).encode()
    leaked = client.post(
        f"/courses/{course2.id}/documents",
        files={"file": ("closer.md", closer, "text/markdown")},
    )
    assert leaked.status_code == 201
    doc2 = leaked.json()["id"]
    detail = client.get(f"/courses/{course2.id}/documents/{doc2}")
    assert detail.json()["job_status"] == "succeeded"
    response = client.post(f"/courses/{course1.id}/ask", json={"query": GOLDEN[0]["query"]})
    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] is None
    assert body["citations"]
    assert all(hit["document_id"] != doc2 for hit in body["citations"])
    assert all(f"/courses/{course1.id}/" in hit["content_url"] for hit in body["citations"])
    assert "omega-course-two" not in (body["answer"] or "")


def test_ask_unauthenticated_is_401(client: TestClient, db: Session) -> None:
    course = add_course(db, "Course 1")
    response = client.post(f"/courses/{course.id}/ask", json={"query": "anything"})
    assert response.status_code == 401


def test_ask_info_logs_omit_query_and_courseware(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")
    query = GOLDEN[0]["query"]
    with caplog.at_level(logging.INFO, logger="app.api.ask"):
        response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    text = caplog.text
    assert query not in text
    assert GOLDEN[0]["expect_substring"] not in text
    assert "sk-" not in text


@pytest.mark.parametrize("failure_point", ["embedding", "llm"])
def test_ask_upstream_failure_is_safe_503_and_logged_without_content(
    client: TestClient,
    db: Session,
    caplog: pytest.LogCaptureFixture,
    failure_point: str,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")
    secret = "provider-body-should-not-be-logged"

    calls = []
    if failure_point == "embedding":

        class FailingEmbedder(FakeEmbedder):
            def embed(self, texts: list[str]) -> list[list[float]]:
                calls.append("embedding")
                raise UpstreamUnavailable(secret)

        app.dependency_overrides[get_embedder] = FailingEmbedder
    else:

        class FailingLLM:
            def generate(self, prompt: str) -> str:
                calls.append("llm")
                raise UpstreamUnavailable(secret)

        app.dependency_overrides[get_llm] = FailingLLM

    with caplog.at_level(logging.INFO, logger="app.api.ask"):
        response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})

    assert response.status_code == 503
    assert calls == [failure_point] * (2 if failure_point == "embedding" else 1)
    assert response.json() == {
        "error_code": UPSTREAM_UNAVAILABLE,
        "message": "上游 AI 服务暂时不可用，请稍后重试。",
        "answer": None,
        "citations": [],
    }
    db.expire_all()
    log = db.execute(select(QueryLog)).scalars().one()
    assert log.error_code == UPSTREAM_UNAVAILABLE
    assert log.outcome == "failure"
    assert log.member_role_at_ask == "teacher"
    assert secret not in caplog.text
    assert GOLDEN[0]["query"] not in caplog.text
    assert "UPSTREAM_UNAVAILABLE" in caplog.text


@pytest.mark.parametrize("failures", [1, 2])
def test_retrieval_upstream_retry_is_bounded(client, db, failures):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Transient retrieval")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")

    class TransientEmbedder(FakeEmbedder):
        calls = 0

        def embed(self, texts):
            self.calls += 1
            if self.calls <= failures:
                raise UpstreamUnavailable("private provider details")
            return super().embed(texts)

    embedder = TransientEmbedder()
    app.dependency_overrides[get_embedder] = lambda: embedder
    response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})
    assert embedder.calls == 2
    assert response.status_code == (200 if failures == 1 else 503)
    assert response.json()["error_code"] == (None if failures == 1 else UPSTREAM_UNAVAILABLE)


def test_definition_lexical_hit_reaches_generation_before_dense_noise(client, db, monkeypatch):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Law definition")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "简述大数定律的含义"
    noise = _scaled_chunk(db, course, embedder, query, "小数定律干扰页", 1.0)
    support = _scaled_chunk(db, course, embedder, query, "大数定律：样本均值收敛于期望。", 0.01)
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(_env_file=None))
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    assert response.json()["error_code"] is None
    assert response.json()["citations"][0]["chunk_id"] == str(support.id)
    assert llm.prompts[0].index(f"[Source {support.id}]") < llm.prompts[0].index(
        f"[Source {noise.id}]",
    )
    assert len(llm.prompts) == 1


@pytest.mark.parametrize("failed_branch", [None, "列视角", "行视角"])
def test_matrix_geometry_merges_bounded_views_and_ignores_optional_failure(
    client, db, monkeypatch, failed_branch,
):
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Matrix geometry")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    query = "矩阵乘法的几何意义"
    embedder = FakeEmbedder()
    noise = _scaled_chunk(db, course, embedder, query, "矩阵目录", 1.0)
    support = _scaled_chunk(db, course, embedder, query, "列视角与行视角：矩阵乘法表示变换。", 0.01)
    noise_hit = SearchHit(noise.id, noise.document_id, 4, noise.text, 1.0)
    support_hit = SearchHit(support.id, support.document_id, 4, support.text, 0.8)

    def retrieve(_db, course_id, text, _embedder, **kwargs):
        assert course_id == course.id
        if text == failed_branch:
            raise UpstreamUnavailable("private optional recall failure")
        return [noise_hit] if text == query else [support_hit] * 8

    mock = Mock(side_effect=retrieve)
    monkeypatch.setattr("app.api.ask.retrieve_chunks", mock)
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(_env_file=None))
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": query})
    assert response.status_code == 200
    assert response.json()["error_code"] is None
    assert response.json()["citations"][0]["chunk_id"] == str(support.id)
    assert parse_cited_ids(llm.prompts[0]) == [support.id, noise.id]
    expected = [query]
    for text in ("列视角", "行视角", "四种理解"):
        expected.extend([text] * (2 if text == failed_branch else 1))
    assert [call.args[2] for call in mock.call_args_list] == expected


def test_ask_requires_membership(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    add_user(db, "bob", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "bob", "pass")
    response = client.post(f"/courses/{course.id}/ask", json={"query": "anything"})
    assert response.status_code == 403


def test_ask_timeout_is_distinct_and_logged_without_provider_details(client, db) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Timeout course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")

    class TimeoutLLM:
        def generate(self, prompt: str) -> str:
            raise UpstreamTimeout("raw-timeout-body")

    app.dependency_overrides[get_llm] = TimeoutLLM
    response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})
    assert response.status_code == 504
    assert response.json()["error_code"] == "UPSTREAM_TIMEOUT"
    assert response.json()["answer"] is None
    assert "raw-timeout-body" not in response.text
    db.expire_all()
    assert db.execute(select(QueryLog)).scalars().one().error_code == "UPSTREAM_TIMEOUT"


def _hybrid_settings(monkeypatch: pytest.MonkeyPatch, **overrides) -> None:
    values = {"retrieval_strategy": "hybrid", "rrf_k": 60, **overrides}
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(_env_file=None, **values))


def test_hybrid_ask_orders_context_by_rrf_and_omits_keyword_only_hits(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Hybrid ask")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    strong = _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 1.0)
    lexical = _scaled_chunk(db, course, embedder, query, "事务隔离级别用于定义并发正确性", 0.4)
    keyword_only = _scaled_chunk(db, course, embedder, query, "事务隔离级别的另一种措辞", 0.01)
    _hybrid_settings(monkeypatch)
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": query})

    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] is None
    assert [item["chunk_id"] for item in body["citations"]] == [str(lexical.id)]
    assert str(keyword_only.id) not in llm.prompts[0]
    assert llm.prompts[0].index(str(lexical.id)) < llm.prompts[0].index(str(strong.id))


@pytest.mark.parametrize("body", [
    "事务隔离级别包括读未提交、读已提交、可重复读和串行化。",
    "事务隔离级别是本章标题，具体内容略。",
])
def test_hybrid_unadmitted_candidates_do_not_call_the_model(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, body: str,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Keyword ask")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, body, 0.01)
    _hybrid_settings(monkeypatch)
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": query})

    assert response.status_code == 200
    assert response.json()["error_code"] == NO_EVIDENCE
    assert response.json()["answer"] is None
    assert response.json()["citations"] == []
    assert llm.prompts == []
    db.expire_all()
    assert db.execute(select(QueryLog)).scalars().one().error_code == NO_EVIDENCE


def test_hybrid_evidence_beyond_original_dense_top_k_reaches_actual_context(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Expanded recall ask")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    for _ in range(8):
        _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 1.0)
    body = "事务隔离级别包括读未提交、读已提交、可重复读和串行化。"
    support = _scaled_chunk(db, course, embedder, query, body, 0.4)
    assert support.id not in {hit.chunk_id for hit in retrieve_chunks(db, course.id, query, embedder)}
    _hybrid_settings(monkeypatch)
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": query})

    assert response.status_code == 200
    assert response.json()["error_code"] is None
    assert response.json()["citations"][0]["chunk_id"] == str(support.id)
    assert body in llm.prompts[0]
    assert f"[Source {support.id}]" in llm.prompts[0]


def test_deleted_hybrid_evidence_is_not_sent_to_generation(db: Session) -> None:
    course = add_course(db, "Deleted evidence")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    chunk = _scaled_chunk(db, course, embedder, query, query, 1.0)
    hits = retrieve_chunks(db, course.id, query, embedder, strategy="hybrid")
    assert hits
    db.delete(chunk)
    db.commit()
    llm = FakeLLM()

    assert generate_answer(db, query, hits, llm) == ("", [])
    assert llm.prompts == []


def test_hybrid_index_mismatch_does_not_search_keywords(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Mismatch hybrid")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md")
    _hybrid_settings(monkeypatch)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("index mismatch must not run keyword retrieval")

    monkeypatch.setattr("app.services.keyword.retrieve_keyword_candidates", forbidden)

    class DifferentBackendEmbedder(FakeEmbedder):
        def __init__(self) -> None:
            super().__init__(model_name="fake-bge-m3")
            self.index_identity = "siliconflow|fake-bge-m3|1024|v1"

    llm = FakeLLM()
    app.dependency_overrides[get_embedder] = DifferentBackendEmbedder
    app.dependency_overrides[get_llm] = lambda: llm
    response = client.post(f"/courses/{course.id}/ask", json={"query": GOLDEN[0]["query"]})
    assert response.status_code == 200
    assert response.json()["error_code"] == EMBEDDING_MISMATCH
    assert llm.prompts == []


@pytest.mark.parametrize(
    ("overrides", "raiser", "code"),
    [
        (
            {"retrieval_strategy": "hybrid"},
            KeywordLimitExceeded("chunks"),
            "KEYWORD_LIMIT",
        ),
        ({"retrieval_strategy": "sparse", "rrf_k": 60}, None, "RETRIEVAL_STRATEGY"),
        ({"retrieval_strategy": "hybrid"}, FusionError("identity"), "RETRIEVAL_FAILED"),
    ],
)
def test_hybrid_failures_are_logged_and_not_reported_as_no_evidence(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict,
    raiser: Exception | None,
    code: str,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Failure hybrid")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 1.0)
    if overrides["retrieval_strategy"] == "sparse":
        monkeypatch.setattr(
            "app.api.ask.get_settings",
            lambda: type("Settings", (), overrides)(),
        )
    else:
        _hybrid_settings(monkeypatch)
    if isinstance(raiser, KeywordLimitExceeded):
        monkeypatch.setattr(
            "app.services.keyword.retrieve_keyword_candidates",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(raiser),
        )
    elif isinstance(raiser, FusionError):
        monkeypatch.setattr(
            "app.services.retrieve.fuse_rrf",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(raiser),
        )
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm

    response = client.post(f"/courses/{course.id}/ask", json={"query": query})

    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == code
    assert body["answer"] is None
    assert body["citations"] == []
    assert body["error_code"] != NO_EVIDENCE
    assert query not in response.text
    assert "chunks" not in (body["message"] or "")
    assert "identity" not in response.text
    assert "sparse" not in response.text
    assert llm.prompts == []
    db.expire_all()
    log = db.execute(select(QueryLog)).scalars().one()
    assert log.error_code == code
    assert log.hit is False
    assert json.loads(log.chunk_ids) == []
