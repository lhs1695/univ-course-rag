"""Offline tests for midterm manual-verify runner diagnostics (no cloud)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.services.generate import NO_EVIDENCE
from app.services.retrieve import SearchHit

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "backend" / "scripts" / "run_manual_verify_cn_v1.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_manual_verify_cn_v1", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def runner():
    return _load_runner()


def test_serialize_retrieval_hits_pairs_fields(runner):
    doc_a, doc_b = uuid4(), uuid4()
    c1, c2 = uuid4(), uuid4()
    hits = [
        SearchHit(c1, doc_a, 3, "alpha " * 80, 0.91),
        SearchHit(c2, doc_b, 12, "beta", 0.55),
    ]
    names = {doc_a: "01-prob.pdf", doc_b: "02-prob.pdf"}
    rows = runner.serialize_retrieval_hits(hits, names, snippet_max=40)
    assert len(rows) == 2
    assert rows[0]["document"] == "01-prob.pdf"
    assert rows[0]["page"] == 3
    assert rows[0]["chunk_id"] == str(c1)
    assert rows[0]["score"] == 0.91
    assert len(rows[0]["snippet"]) <= 41  # 40 + ellipsis
    assert rows[0]["snippet"].endswith("…")
    assert rows[1]["document"] == "02-prob.pdf"
    assert rows[1]["snippet"] == "beta"


@pytest.mark.parametrize(
    "raw,cited,had,expect_status,expect_answer_empty",
    [
        ("", [], False, "no_retrieval_hits", True),
        (NO_EVIDENCE, [], True, "no_evidence_marker", True),
        ("  ", [], True, "empty_output", True),
        ("有内容但无引用", [], True, "no_valid_citations", False),
        ("正常回答 [Source x]", [uuid4()], True, "answered", False),
    ],
)
def test_classify_generation_statuses(runner, raw, cited, had, expect_status, expect_answer_empty):
    status, answer, kept = runner.classify_generation(
        raw_answer=raw, cited_ids=list(cited), had_retrieval_hits=had
    )
    assert status == expect_status
    assert (answer == "") is expect_answer_empty
    if expect_status == "answered":
        assert kept == list(cited)
    else:
        assert kept == []


def test_candidate_stats_and_keyword_only_gate_note(runner):
    e1, e2, e3 = uuid4(), uuid4(), uuid4()
    candidates = [
        SimpleNamespace(chunk_id=e1, dense_rank=1, keyword_rank=2),
        SimpleNamespace(chunk_id=e2, dense_rank=3, keyword_rank=None),
        SimpleNamespace(chunk_id=e3, dense_rank=None, keyword_rank=1),
    ]
    stats = runner.candidate_stats(candidates, evidence_ids={e1}, min_score=0.45)
    assert stats["candidate_count"] == 3
    assert stats["both"] == 1
    assert stats["dense_only"] == 1
    assert stats["keyword_only"] == 1
    assert stats["keyword_only_in_final_evidence"] == 0
    assert "same candidate list" in stats["note"]


def test_hybrid_path_uses_single_candidate_retrieve(runner, monkeypatch):
    """Official hybrid evidence must not call retrieve_chunks (avoids second embed)."""
    calls = {"hybrid_candidates": 0, "retrieve_chunks": 0, "select": 0}

    cid = uuid4()
    did = uuid4()
    fused = SimpleNamespace(
        chunk_id=cid,
        document_id=did,
        page=2,
        snippet="toc",
        cosine_score=0.9,
        bm25_score=1.0,
        dense_rank=1,
        keyword_rank=1,
        rrf_score=0.1,
    )

    def fake_candidates(*args, **kwargs):
        calls["hybrid_candidates"] += 1
        return [fused]

    def fake_select(candidates, *, top_k, min_score):
        calls["select"] += 1
        return [
            SearchHit(c.chunk_id, c.document_id, c.page, c.snippet, c.cosine_score)
            for c in candidates
            if c.cosine_score is not None and c.cosine_score >= min_score
        ][:top_k]

    def fake_retrieve_chunks(*args, **kwargs):
        calls["retrieve_chunks"] += 1
        raise AssertionError("retrieve_chunks must not be used on hybrid path")

    monkeypatch.setattr(runner, "retrieve_hybrid_candidates", fake_candidates)
    monkeypatch.setattr(runner, "_select_conservative_evidence", fake_select)
    monkeypatch.setattr(runner, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(runner, "_default_min_score", lambda _e: 0.45)
    monkeypatch.setattr(runner, "_doc_names", lambda _db, _cid: {did: "01-prob.pdf"})

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            assert "Source" in prompt or prompt  # prompt exists; do not assert full text
            return f"目录四节 [Source {cid}]"

    class FakeDB:
        def get(self, model, key):
            return SimpleNamespace(id=key, text="第一节…第二节…", page=2, document_id=did)

    # assemble_ask_context / filter_citations need real wiring — stub generate path lightly
    monkeypatch.setattr(
        runner,
        "assemble_ask_context",
        lambda query, hits, chunks, **kw: SimpleNamespace(
            source_ids=[cid],
            prompt="user-prompt-omitted-in-tests",
            source_texts={cid: "第一节…"},
        ),
    )
    monkeypatch.setattr(
        runner,
        "filter_citations",
        lambda answer, source_ids: list(source_ids),
    )

    case = {
        "id": "T-HYB",
        "course": "概率论与统计学",
        "category": "in_course_fact",
        "query": "目录？",
        "should_refuse": False,
    }
    item = runner.run_case(
        FakeDB(),
        case,
        uuid4(),
        embedder=object(),
        llm=FakeLLM(),
        strategy="hybrid",
        tracker=runner.UsageTracker(),
    )
    assert calls["hybrid_candidates"] == 1
    assert calls["retrieve_chunks"] == 0
    assert calls["select"] == 1
    assert item["timing"]["diagnosis_ms"] >= 0
    assert "retrieval_ms" in item["timing"]
    assert item["retrieval_candidate_stats"]["candidate_count"] == 1
    assert item["retrieval_hits"][0]["chunk_id"] == str(cid)
    assert item["generation_status"] == "answered"
    assert item["status"] == "answered"


def test_status_from_generation_mapping(runner):
    assert runner.status_from_generation("answered") == "answered"
    assert runner.status_from_generation("system_error") == "system_error"
    assert runner.status_from_generation("no_evidence_marker") == "no_evidence"
    assert runner.status_from_generation("empty_output") == "no_evidence"
