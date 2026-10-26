"""Offline lexical contracts on synthetic SQLite rows; no provider or real corpus."""

from dataclasses import replace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from app.models.course import Course
from app.models.document import Chunk, Document
from app.services import keyword
from app.services.keyword import (
    DEFAULT_KEYWORD_LIMITS,
    KeywordLimitExceeded,
    KeywordLimits,
    preprocess_text,
    retrieve_keyword_candidates,
)
from sqlalchemy import event
from sqlalchemy.orm import Session

INDEX = "fake|synthetic|1024|v1"


@pytest.fixture
def course_id(db: Session) -> UUID:
    course = Course(title="Synthetic lexical course")
    db.add(course)
    db.commit()
    return course.id


def add_chunk(db, course_id, text, *, identity=INDEX, chunk_id=None) -> Chunk:
    document = Document(
        course_id=course_id, uploaded_by=uuid4(), filename="synthetic.txt", storage_path="unused",
        retrieval_enabled=True,
    )
    db.add(document)
    db.flush()
    chunk = Chunk(
        id=chunk_id or uuid4(), course_id=course_id, document_id=document.id,
        page=2, text=text, embedding=[0.0] * 1024, embedding_model=identity,
    )
    db.add(chunk)
    db.commit()
    return chunk


def search(db, course_id, query, **kwargs):
    return retrieve_keyword_candidates(db, course_id, query, index_identity=INDEX, **kwargs)


@pytest.mark.parametrize("text", ["", " \n\t", "，。！？…---🙂"])
def test_preprocessing_empty_and_punctuation(text: str) -> None:
    assert preprocess_text(text) == []


def test_preprocessing_preserves_chinese_search_terms_and_ascii_identifiers() -> None:
    tokens = preprocess_text("操作系统虚拟内存，ＲＡＧ SQL C++ C# TF-IDF bge-m3 2026 3.12")
    assert {"操作系统", "虚拟内存", "rag", "sql", "c++", "c#", "tf-idf", "bge-m3", "2026", "3.12"} <= set(tokens)
    assert preprocess_text("ＲＡＧ　虚拟内存") == preprocess_text("rag 虚拟内存")
    assert preprocess_text("SQL SQL") == ["sql", "sql"]


@pytest.mark.parametrize(
    "text, options, resource",
    [
        ("private-text", {"max_chars": 2}, "text_chars"),
        ("ﬃ", {"max_chars": 1}, "normalized_chars"),
        ("alpha beta gamma", {"max_tokens": 2}, "text_tokens"),
    ],
)
def test_preprocessing_limits_fail_without_echoing_input(text, options, resource) -> None:
    with pytest.raises(KeywordLimitExceeded) as exc:
        preprocess_text(text, **options)
    assert exc.value.resource == resource
    assert text not in str(exc.value)


@pytest.mark.parametrize("field", list(keyword._CEILINGS))
@pytest.mark.parametrize("invalid", [0, True])
def test_limits_reject_disabled_or_noninteger_bounds(field, invalid) -> None:
    with pytest.raises(ValueError, match="Invalid keyword limit"):
        replace(DEFAULT_KEYWORD_LIMITS, **{field: invalid})


def test_limits_cannot_exceed_hard_ceilings() -> None:
    for field, ceiling in keyword._CEILINGS.items():
        with pytest.raises(ValueError, match="Invalid keyword limit"):
            replace(DEFAULT_KEYWORD_LIMITS, **{field: ceiling + 1})


def test_empty_corpus_does_not_construct_bm25(db, course_id, monkeypatch) -> None:
    monkeypatch.setattr(keyword, "BM25Okapi", lambda *args, **kwargs: pytest.fail("empty BM25"))
    assert search(db, course_id, "alpha") == []
    add_chunk(db, course_id, "，。 \n")
    assert search(db, course_id, "alpha") == []


def test_no_token_overlap_returns_no_fixed_top_n(db, course_id, monkeypatch) -> None:
    add_chunk(db, course_id, "alpha beta")
    monkeypatch.setattr(keyword, "BM25Okapi", lambda *args, **kwargs: pytest.fail("no-overlap BM25"))
    assert search(db, course_id, "unrelatedzz9") == []


@pytest.mark.parametrize("extra_document", [False, True])
def test_nonpositive_scores_are_not_discarded_and_unmatched_rows_are_excluded(
    db, course_id, extra_document
) -> None:
    matching = add_chunk(db, course_id, "alpha")
    if extra_document:
        add_chunk(db, course_id, "beta")
    hits = search(db, course_id, "alpha")
    assert [hit.chunk_id for hit in hits] == [matching.id]
    assert hits[0].bm25_score == 0 if extra_document else hits[0].bm25_score < 0
    assert not hasattr(hits[0], "score")


def test_keyword_ranking_top_k_and_source_metadata(db, course_id) -> None:
    strong = add_chunk(db, course_id, "needle needle needle")
    weak = add_chunk(db, course_id, "needle filler")
    for text in ("alpha", "beta", "gamma"):
        add_chunk(db, course_id, text)
    hits = search(db, course_id, "NEEDLE", top_k=2)
    assert [hit.chunk_id for hit in hits] == [strong.id, weak.id]
    assert hits[0].bm25_score > hits[1].bm25_score > 0
    assert hits[0].document_id == strong.document_id
    assert hits[0].page == 2
    assert hits[0].snippet == strong.text
    assert search(db, course_id, "needle", top_k=1) == hits[:1]
    assert search(db, course_id, "needle needle", top_k=2) == hits


def test_ties_are_deterministic_by_chunk_id(db, course_id) -> None:
    second = add_chunk(db, course_id, "alpha", chunk_id=UUID(int=2))
    first = add_chunk(db, course_id, "alpha", chunk_id=UUID(int=1))
    expected = [first.id, second.id]
    assert [hit.chunk_id for hit in search(db, course_id, "alpha")] == expected
    assert [hit.chunk_id for hit in search(db, course_id, "alpha")] == expected


def test_mixed_language_query_uses_the_same_preprocessing_as_documents(db, course_id) -> None:
    matching = add_chunk(db, course_id, "虚拟内存 RAG C++ 2026")
    add_chunk(db, course_id, "调度 CPU")
    assert [hit.chunk_id for hit in search(db, course_id, "ＲＡＧ 虚拟内存")] == [matching.id]


def test_course_index_and_document_filters_precede_loading_and_resource_limits(db, course_id) -> None:
    matching = add_chunk(db, course_id, "alpha")
    excluded = add_chunk(db, course_id, "alpha " * 2000)
    add_chunk(db, course_id, "alpha " * 2000, identity="legacy-index")
    other = Course(title="Other course")
    db.add(other)
    db.commit()
    add_chunk(db, other.id, "alpha " * 2000)
    hits = search(
        db, course_id, "alpha", excluded_document_ids={excluded.document_id},
        limits=KeywordLimits(max_chunks=1, max_chunk_chars=5, max_corpus_chars=5),
    )
    assert [hit.chunk_id for hit in hits] == [matching.id]
    assert search(db, course_id, "alpha", excluded_document_ids={matching.document_id, excluded.document_id}) == []


def test_deletion_text_and_index_changes_are_visible_without_stale_result_cache(db, course_id) -> None:
    chunk = add_chunk(db, course_id, "alpha")
    assert search(db, course_id, "alpha")
    chunk.text = "beta"
    db.commit()
    assert search(db, course_id, "alpha") == []
    assert search(db, course_id, "beta")
    chunk.embedding_model = "other-index"
    db.commit()
    assert search(db, course_id, "beta") == []
    assert retrieve_keyword_candidates(db, course_id, "beta", index_identity="other-index")
    db.delete(chunk)
    db.commit()
    assert retrieve_keyword_candidates(db, course_id, "beta", index_identity="other-index") == []


@pytest.mark.parametrize("query", ["", "，。", "alpha"])
def test_empty_query_and_zero_top_k_do_not_read_database(query) -> None:
    db = Mock(spec=Session)
    assert search(db, uuid4(), query, top_k=0 if query == "alpha" else 8) == []
    db.execute.assert_not_called()


@pytest.mark.parametrize("top_k", [-1, 101, True])
def test_invalid_candidate_limits_fail_before_database_access(top_k) -> None:
    db = Mock(spec=Session)
    with pytest.raises(ValueError, match="candidate limit"):
        search(db, uuid4(), "alpha", top_k=top_k)
    db.execute.assert_not_called()


@pytest.mark.parametrize("identity", ["", " ", "x" * 129])
def test_explicit_nonempty_index_identity_is_required(identity) -> None:
    with pytest.raises(ValueError, match="index identity"):
        retrieve_keyword_candidates(Mock(spec=Session), uuid4(), "alpha", index_identity=identity)


@pytest.mark.parametrize(
    "query, limits, resource",
    [
        ("alpha", KeywordLimits(max_query_chars=4), "text_chars"),
        ("a b c", KeywordLimits(max_query_tokens=2), "text_tokens"),
    ],
)
def test_query_resource_overflow_does_not_read_corpus(query, limits, resource) -> None:
    db = Mock(spec=Session)
    with pytest.raises(KeywordLimitExceeded) as exc:
        search(db, uuid4(), query, limits=limits)
    assert exc.value.resource == resource
    db.execute.assert_not_called()


@pytest.mark.parametrize(
    "texts, limits, resource",
    [
        (["alpha", "beta"], KeywordLimits(max_chunks=1), "chunks"),
        (["alpha beta"], KeywordLimits(max_chunk_chars=5), "chunk_chars"),
        (["alpha", "beta"], KeywordLimits(max_corpus_chars=6), "corpus_chars"),
        (["alpha beta gamma"], KeywordLimits(max_chunk_tokens=2), "text_tokens"),
        (["alpha beta", "alpha gamma"], KeywordLimits(max_corpus_tokens=3), "corpus_tokens"),
    ],
)
def test_corpus_resource_overflow_is_explicit_not_partial(db, course_id, texts, limits, resource) -> None:
    for text in texts:
        add_chunk(db, course_id, text)
    with pytest.raises(KeywordLimitExceeded) as exc:
        search(db, course_id, "alpha", limits=limits)
    assert exc.value.resource == resource


def test_sql_reads_only_a_bounded_text_prefix_not_full_vectors(db, course_id) -> None:
    add_chunk(db, course_id, "a" * 20000)
    selects = []

    def capture(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append((statement, parameters))

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        with pytest.raises(KeywordLimitExceeded, match="chunk_chars"):
            search(db, course_id, "a", limits=KeywordLimits(max_chunk_chars=8, max_chunks=2))
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert len(selects) == 1
    statement, parameters = selects[0]
    projection = statement.split("FROM", 1)[0]
    assert "substr(chunks.text" in projection
    assert "chunks.embedding" not in projection
    assert "LIMIT" in statement
    assert 9 in parameters  # Per-chunk prefix plus overflow sentinel.
    assert 3 in parameters  # Row-count limit plus overflow sentinel.


def test_exclusion_resource_limit_is_bounded() -> None:
    with pytest.raises(KeywordLimitExceeded, match="excluded_documents"):
        search(Mock(spec=Session), uuid4(), "alpha", excluded_document_ids=[uuid4()] * 1001)


def test_exact_resource_boundaries_remain_searchable(db, course_id) -> None:
    add_chunk(db, course_id, "alpha")
    limits = KeywordLimits(
        max_chunks=1, max_chunk_chars=5, max_corpus_chars=5,
        max_query_chars=5, max_chunk_tokens=1, max_corpus_tokens=1, max_query_tokens=1,
    )
    assert len(search(db, course_id, "alpha", limits=limits)) == 1
