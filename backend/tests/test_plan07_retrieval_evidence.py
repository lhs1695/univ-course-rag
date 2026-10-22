"""PLAN-07 offline contracts; synthetic evidence is not a quality evaluation."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.services.embedder import FakeEmbedder
from app.services.generate import NO_EVIDENCE
from app.services.retrieve import (
    HYBRID_CANDIDATE_K,
    SearchHit,
    _default_min_score,
    _select_conservative_evidence,
    cosine_similarity,
    retrieve_hybrid_candidates,
)

from tests.test_manual_verify_runner import _load_runner
from tests.test_retrieve import _scaled_chunk, add_course


@pytest.fixture(scope="module")
def runner():
    return _load_runner()


def test_serialize_retrieval_hits_keeps_document_page_score_snippet_pairs(runner):
    doc_a, doc_b, unknown = uuid4(), uuid4(), uuid4()
    chunks = [uuid4() for _ in range(3)]
    hits = [
        SearchHit(chunks[0], doc_a, 3, "alpha\r\nbeta gamma", 0.91),
        SearchHit(chunks[1], doc_b, 2, "other", 0.55),
        SearchHit(chunks[2], unknown, None, "", 0.45),
    ]
    rows = runner.serialize_retrieval_hits(
        hits, {doc_a: "synthetic-a.pdf", doc_b: "synthetic-b.pdf"}, snippet_max=10,
    )
    assert rows == [
        {"document": "synthetic-a.pdf", "page": 3, "chunk_id": str(chunks[0]),
         "score": 0.91, "snippet": "alpha\nbeta…"},
        {"document": "synthetic-b.pdf", "page": 2, "chunk_id": str(chunks[1]),
         "score": 0.55, "snippet": "other"},
        {"document": str(unknown), "page": None, "chunk_id": str(chunks[2]),
         "score": 0.45, "snippet": ""},
    ]
    assert hits[0].snippet == "alpha\r\nbeta gamma"  # diagnostics never mutate evidence
    assert runner.serialize_retrieval_hits([], {}) == []


@pytest.mark.parametrize(
    "raw,has_citation,had_hits,expected_status,expected_answer",
    [
        ("  synthetic answer  ", True, True, "answered", "synthetic answer"),
        (f"  {NO_EVIDENCE}\n", True, True, "no_evidence_marker", ""),
        (" \r\n ", True, True, "empty_output", ""),
        ("synthetic answer", False, True, "no_valid_citations", "synthetic answer"),
        ("synthetic answer", True, False, "no_retrieval_hits", ""),
    ],
)
def test_classify_generation_status(
    runner, raw, has_citation, had_hits, expected_status, expected_answer,
):
    cited_ids = [uuid4()] if has_citation else []
    status, answer, kept = runner.classify_generation(
        raw_answer=raw, cited_ids=cited_ids, had_retrieval_hits=had_hits,
    )
    assert (status, answer) == (expected_status, expected_answer)
    assert kept == (cited_ids if status == "answered" else [])
    assert runner.status_from_generation(status) == (
        "answered" if status == "answered" else "no_evidence"
    )


def test_keyword_only_below_cosine_gate_is_fused_but_not_final_evidence(db, runner):
    course = add_course(db, "PLAN-07 synthetic gate")
    embedder = FakeEmbedder()
    # Only the identity selects the live threshold; embedding remains entirely Fake.
    embedder.index_identity = "siliconflow|BAAI/bge-m3|1024|v1"
    query = "事务隔离级别"
    both = _scaled_chunk(db, course, embedder, query, query, 0.8)
    dense = _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 0.9)
    for _ in range(HYBRID_CANDIDATE_K - 2):
        _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 0.7)
    lexical = _scaled_chunk(db, course, embedder, query, query + "另一种措辞", 0.44)
    assert cosine_similarity(embedder.embed([query])[0], lexical.embedding) == pytest.approx(0.44)
    threshold = _default_min_score(embedder)
    assert threshold == 0.45

    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder)
    by_id = {hit.chunk_id: hit for hit in candidates}
    assert by_id[lexical.id].dense_rank is None
    assert by_id[lexical.id].keyword_rank is not None
    assert by_id[lexical.id].cosine_score is None  # fusion does not measure lexical-only cosine
    assert by_id[both.id].dense_rank is not None
    assert by_id[both.id].keyword_rank is not None
    assert by_id[dense.id].keyword_rank is None

    evidence = _select_conservative_evidence(candidates, top_k=2, min_score=threshold)
    assert {hit.chunk_id for hit in evidence} == {both.id, dense.id}
    assert {hit.chunk_id: hit.score for hit in evidence} == pytest.approx(
        {both.id: 0.8, dense.id: 0.9},
    )
    stats = runner.candidate_stats(candidates, {hit.chunk_id for hit in evidence}, threshold)
    assert stats["keyword_only"] == 1
    assert stats["keyword_only_in_final_evidence"] == 0


@pytest.mark.parametrize("raw_kind,expected", [
    ("marker", "no_evidence_marker"),
    ("empty", "empty_output"),
    ("foreign_citation", "no_valid_citations"),
    ("valid_citation", "answered"),
    ("upstream_failure", "system_error"),
])
def test_runner_preserves_hits_through_generation_diagnostics(runner, monkeypatch, raw_kind, expected):
    cid, did = uuid4(), uuid4()
    hit = SearchHit(cid, did, 3, "synthetic excerpt", 0.8)
    monkeypatch.setattr(runner, "_doc_names", lambda *_: {did: "synthetic.pdf"})
    monkeypatch.setattr(runner, "retrieve_chunks", lambda *_, **__: [hit])
    db = SimpleNamespace(get=lambda *_: SimpleNamespace(text="synthetic source body"))
    llm = Mock()
    if raw_kind == "upstream_failure":
        llm.generate.side_effect = runner.UpstreamUnavailable()
    else:
        llm.generate.return_value = {
            "marker": NO_EVIDENCE,
            "empty": " ",
            "foreign_citation": f"synthetic answer [Source {uuid4()}]",
            "valid_citation": f"synthetic answer [Source {cid}]",
        }[raw_kind]
    item = runner.run_case(
        db, {"id": "SYNTHETIC", "course": "test", "category": "in_course_fact",
             "query": "synthetic question", "should_refuse": False},
        uuid4(), FakeEmbedder(), llm, "dense", runner.UsageTracker(),
    )
    llm.generate.assert_called_once()
    assert item["generation_status"] == expected
    assert item["status"] == runner.status_from_generation(expected)
    assert item["retrieval_hits"] == runner.serialize_retrieval_hits([hit], {did: "synthetic.pdf"})
    assert [row["chunk_id"] for row in item["citations"]] == (
        [str(cid)] if expected == "answered" else []
    )
    assert (item["error"] is not None) is (expected == "system_error")


def test_citation_supports_and_page_ok_have_independent_counts_and_review_state(runner):
    def item(support, page, **overrides):
        return {"status": "answered", "should_refuse": False,
                "citation_supports": support, "page_ok": page, **overrides}

    items = [
        item("pass", "fail"),  # merged-page mismatch need not invalidate support
        item("fail", "pass"),  # a page match does not prove answer support
        item("pass", "pass"),
        item("pending", "unclear"),
        item("pass", "pass", status="no_evidence"),
        item("pass", "pass", status="system_error"),
        item("pass", "pass", should_refuse=True),
    ]
    assert runner.summarize_citation_metrics(items) == {
        "citation_supports": {"n": 2, "N": 4, "reviewed": 3},
        "page_ok": {"n": 2, "N": 4, "reviewed": 3},
    }
    items[0]["page_ok"] = "pass"
    assert runner.summarize_citation_metrics(items) == {
        "citation_supports": {"n": 2, "N": 4, "reviewed": 3},
        "page_ok": {"n": 3, "N": 4, "reviewed": 3},
    }
    assert runner.summarize_citation_metrics([]) == {
        "citation_supports": {"n": 0, "N": 0, "reviewed": 0},
        "page_ok": {"n": 0, "N": 0, "reviewed": 0},
    }
