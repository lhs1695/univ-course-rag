"""Retrieval tests use FakeEmbedder token/bigram hashing so shared terms rank higher.

Do not weaken golden.json if a query misses; fix retrieve/embedder instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from app.config import Settings
from app.main import app
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.document import Chunk, Document
from app.models.user import User, UserRole
from app.services.embedder import FakeEmbedder
from app.services.fusion import FusionError
from app.services.keyword import KeywordLimitExceeded
from app.services.rerank import FakeReranker, RerankError, get_reranker
from app.services.retrieve import (
    HYBRID_CANDIDATE_K,
    SEARCH_MIN_SCORE,
    SILICONFLOW_SEARCH_MIN_SCORE,
    RetrievalStrategyError,
    _default_min_score,
    _postgres_retrieval_statement,
    has_incompatible_chunks,
    merge_definition_hits,
    retrieve_chunks,
    retrieve_hybrid_candidates,
)
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from tests.conftest import add_user

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = json.loads((FIXTURES / "golden.json").read_text(encoding="utf-8"))
UNRELATED = "xyzzyplugh qwertyuiop-unrelated-zz9 cooking recipe"


def login_as(client: TestClient, username: str, password: str) -> None:
    client.post("/auth/logout")
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def add_course(db: Session, title: str) -> Course:
    course = Course(title=title)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def add_member(db: Session, course: Course, user: User, role: CourseMemberRole) -> None:
    db.add(CourseMember(course_id=course.id, user_id=user.id, role=role.value))
    db.commit()


def upload(client: TestClient, course_id: UUID, path: Path, db: Session | None = None) -> UUID:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        content_type = "application/pdf"
    elif suffix == ".pptx":
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif suffix == ".ppt":
        content_type = "application/vnd.ms-powerpoint"
    elif suffix == ".docx":
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif suffix == ".doc":
        content_type = "application/msword"
    else:
        content_type = "text/markdown"
    response = client.post(
        f"/courses/{course_id}/documents",
        files={"file": (path.name, path.read_bytes(), content_type)},
    )
    assert response.status_code == 201, response.text
    doc_id = UUID(response.json()["id"])
    detail = client.get(f"/courses/{course_id}/documents/{doc_id}")
    assert detail.json()["job_status"] == "succeeded", detail.json()
    if db is not None:
        document = db.get(Document, doc_id)
        assert document is not None
        document.retrieval_enabled = True
        db.commit()
    return doc_id


def test_golden_hits_md_and_pdf(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    login_as(client, "t1", "pass")
    by_file = {
        "sample.md": upload(client, course.id, FIXTURES / "sample.md", db),
        "sample.pdf": upload(client, course.id, FIXTURES / "sample.pdf", db),
        "sample.pptx": upload(client, course.id, FIXTURES / "sample.pptx", db),
        "sample.docx": upload(client, course.id, FIXTURES / "sample.docx", db),
    }
    login_as(client, "alice", "pass")
    assert len(GOLDEN) >= 3
    sources = {item["source_file"] for item in GOLDEN}
    assert "sample.md" in sources and "sample.pdf" in sources
    assert "sample.pptx" in sources
    assert "sample.docx" in sources
    for item in GOLDEN:
        response = client.post(
            f"/courses/{course.id}/search",
            json={"query": item["query"]},
        )
        assert response.status_code == 200, item
        hits = response.json()["hits"]
        assert hits, item
        expected_doc = str(by_file[item["source_file"]])
        assert any(
            hit["document_id"] == expected_doc and item["expect_substring"] in hit["snippet"]
            for hit in hits
        ), (item, hits)


def test_low_score_returns_empty_not_guess(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    upload(client, course.id, FIXTURES / "sample.md", db)
    response = client.post(f"/courses/{course.id}/search", json={"query": UNRELATED})
    assert response.status_code == 200
    assert response.json()["hits"] == []


def test_retrieve_only_uses_matching_index_identity(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    document_id = upload(client, course.id, FIXTURES / "sample.md", db)
    embedder = FakeEmbedder()
    query = GOLDEN[0]["query"]
    incompatible = Chunk(
        course_id=course.id,
        document_id=document_id,
        text="不兼容索引不应被检索到",
        embedding=embedder.embed([query])[0],
        embedding_model="siliconflow|fake-bge-m3|1024|v1",
    )
    db.add(incompatible)
    db.commit()

    hits = retrieve_chunks(db, course.id, query, embedder)

    assert hits
    assert all(hit.chunk_id != incompatible.id for hit in hits)


def test_default_min_score_is_calibrated_per_embedding_space() -> None:
    fake = FakeEmbedder()
    live_identity = FakeEmbedder()
    live_identity.index_identity = "siliconflow|BAAI/bge-m3|1024|v1"

    assert _default_min_score(fake) == SEARCH_MIN_SCORE == 0.15
    assert _default_min_score(live_identity) == SILICONFLOW_SEARCH_MIN_SCORE == 0.45


def test_postgres_statement_pushes_filters_distance_order_and_limit_to_sql() -> None:
    embedder = FakeEmbedder()
    course_id = UUID("00000000-0000-0000-0000-000000000001")
    excluded_id = UUID("00000000-0000-0000-0000-000000000002")

    statement = _postgres_retrieval_statement(
        course_id,
        embedder,
        embedder.embed(["database systems"])[0],
        top_k=8,
        min_score=0.15,
        excluded_document_ids={excluded_id},
    )
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "chunks.embedding <=>" in sql
    assert "chunks.course_id =" in sql
    assert "chunks.embedding_model =" in sql
    assert "chunks.document_id NOT IN" in sql
    assert "ORDER BY distance" in sql
    assert "LIMIT" in sql
    assert "chunks.embedding," not in sql


def test_incompatible_check_uses_exists_and_honors_exclusions(db: Session) -> None:
    course = add_course(db, "Course 1")
    excluded_document_id = UUID("00000000-0000-0000-0000-000000000003")
    embedder = FakeEmbedder()
    teacher = add_user(db, "legacy-uploader", "pass", UserRole.teacher)
    db.add(Document(
        id=excluded_document_id, course_id=course.id, uploaded_by=teacher.id,
        filename="legacy.txt", storage_path="unused-synthetic-path",
        retrieval_enabled=True,
    ))
    db.add(
        Chunk(
            course_id=course.id,
            document_id=excluded_document_id,
            text="legacy",
            embedding=embedder.embed(["legacy"])[0],
            embedding_model="legacy-model",
        )
    )
    db.commit()

    assert has_incompatible_chunks(db, course.id, embedder)
    assert not has_incompatible_chunks(
        db,
        course.id,
        embedder,
        excluded_document_ids={excluded_document_id},
    )


@pytest.mark.postgres
def test_postgres_executes_pgvector_top_k_and_has_filter_index() -> None:
    if os.environ.get("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("set RUN_POSTGRES_TESTS=1 for the local Postgres proof")
    from app.db import SessionLocal

    embedder = FakeEmbedder()
    query = "database transaction isolation"
    with SessionLocal() as db:
        user = User(
            username=f"pgvector-{uuid4()}",
            password_hash="test-only",
            role=UserRole.teacher.value,
        )
        course = Course(title="pgvector proof")
        db.add_all([user, course])
        db.flush()
        document = Document(
            course_id=course.id,
            uploaded_by=user.id,
            filename="proof.md",
            storage_path="test-only",
            retrieval_enabled=True,
        )
        db.add(document)
        db.flush()
        for page, body in enumerate(
            [query, "database isolation", "unrelated cooking recipe"], start=1
        ):
            db.add(
                Chunk(
                    course_id=course.id,
                    document_id=document.id,
                    page=page,
                    text=body,
                    embedding=embedder.embed([body])[0],
                    embedding_model=embedder.index_identity,
                )
            )
        db.flush()

        statement = _postgres_retrieval_statement(
            course.id,
            embedder,
            embedder.embed([query])[0],
            top_k=2,
            min_score=-1.0,
            excluded_document_ids=(),
        )
        compiled = statement.compile(db.get_bind(), compile_kwargs={"literal_binds": True})
        plan = "\n".join(db.execute(text(f"EXPLAIN {compiled}")).scalars())
        hits = retrieve_chunks(db, course.id, query, embedder, top_k=2, min_score=-1.0)
        index_exists = db.scalar(
            text("SELECT to_regclass('public.ix_chunks_course_embedding_model') IS NOT NULL")
        )
        db.rollback()

    assert index_exists is True
    assert len(hits) == 2
    assert hits[0].snippet == query
    assert hits[0].score == pytest.approx(1.0)
    assert "Limit" in plan
    # PG/SQLAlchemy may qualify the column as chunks.embedding in EXPLAIN output.
    assert "Sort Key:" in plan
    assert "embedding <=>" in plan


def test_search_does_not_leak_other_course(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course1 = add_course(db, "Course 1")
    course2 = add_course(db, "Course 2")
    add_member(db, course1, teacher, CourseMemberRole.teacher)
    add_member(db, course2, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    doc1 = upload(client, course1.id, FIXTURES / "sample.md", db)
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

    query = GOLDEN[0]["query"]
    response = client.post(f"/courses/{course1.id}/search", json={"query": query})
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert hits
    assert all(hit["document_id"] == str(doc1) for hit in hits)
    assert all(hit["document_id"] != doc2 for hit in hits)


def test_search_requires_membership(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    add_user(db, "bob", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "bob", "pass")
    response = client.post(f"/courses/{course.id}/search", json={"query": "anything"})
    assert response.status_code == 403


@pytest.mark.integration
def test_siliconflow_embedding_optional() -> None:
    key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if not key:
        pytest.skip("no SILICONFLOW_API_KEY")
    from app.services.embedder import SiliconFlowEmbedder

    embedder = SiliconFlowEmbedder(
        api_key=key,
        base_url=os.environ.get("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
        model_name=os.environ.get("EMBEDDING_MODEL", "BAAI/bge-m3"),
    )
    vectors = embedder.embed(["课程知识库测试"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 1024


def _scaled_chunk(db: Session, course: Course, embedder: FakeEmbedder, query: str, text: str, scale: float) -> Chunk:
    document = Document(
        course_id=course.id,
        uploaded_by=uuid4(),
        filename="synthetic.md",
        storage_path="unused",
        retrieval_enabled=True,
    )
    db.add(document)
    db.flush()
    vector = embedder.embed([query])[0]
    chunk = Chunk(
        course_id=course.id,
        document_id=document.id,
        page=4,
        text=text,
        embedding=[scale * value for value in vector],
        embedding_model=embedder.index_identity,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_definition_lexical_merge_is_scoped_bounded_and_deduplicated(db: Session) -> None:
    course = add_course(db, "Definition")
    other = add_course(db, "Other")
    embedder = FakeEmbedder()
    query = "简述大数定律的含义"
    dense = _scaled_chunk(db, course, embedder, query, "干扰页", 1.0)
    support = _scaled_chunk(db, course, embedder, query, "大数定律描述样本均值的收敛。", 0.01)
    foreign = _scaled_chunk(db, other, embedder, query, "大数定律外课资料", 1.0)
    old = _scaled_chunk(db, course, embedder, query, "大数定律旧模型资料", 1.0)
    old.embedding_model = "old-index"
    db.commit()
    hits = retrieve_chunks(db, course.id, query, embedder)
    assert support.id not in {hit.chunk_id for hit in hits}
    merged = merge_definition_hits(db, course.id, "大数定律", embedder, hits)
    assert [hit.chunk_id for hit in merged] == [support.id, dense.id]
    assert not {foreign.id, old.id} & {hit.chunk_id for hit in merged}
    assert merge_definition_hits(db, course.id, "大数定律", embedder, merged) == merged
    for page in range(10):
        chunk = _scaled_chunk(db, course, embedder, query, "大数定律其他页", 0.01)
        chunk.page = page + 10
    db.commit()
    bounded = merge_definition_hits(db, course.id, "大数定律", embedder, hits)
    assert len(bounded) == 5  # four lexical additions plus the original dense hit
    assert len({hit.chunk_id for hit in bounded}) == 5
    assert merge_definition_hits(db, course.id, "", embedder, hits) == hits
    assert merge_definition_hits(db, course.id, "%_", embedder, hits) == hits


def test_retrieval_defaults_remain_dense() -> None:
    assert Settings.model_fields["retrieval_strategy"].default == "dense"
    assert Settings.model_fields["rrf_k"].default == 60
    with pytest.raises(ValidationError):
        Settings(_env_file=None, retrieval_strategy="sparse")


def test_dense_strategy_matches_the_historical_call_and_skips_keywords(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    course = add_course(db, "Dense course")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 1.0)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("dense retrieval must not call the keyword service")

    monkeypatch.setattr("app.services.keyword.retrieve_keyword_candidates", forbidden)
    explicit = retrieve_chunks(db, course.id, query, embedder, strategy="dense", rrf_k=1)
    historical = retrieve_chunks(db, course.id, query, embedder)
    assert [(hit.chunk_id, hit.score) for hit in explicit] == [
        (hit.chunk_id, hit.score) for hit in historical
    ]
    assert historical[0].score == pytest.approx(1.0)


def test_invalid_rrf_constant_fails_before_either_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Mock()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("invalid fusion settings must not search")

    monkeypatch.setattr("app.services.keyword.retrieve_keyword_candidates", forbidden)
    with pytest.raises(FusionError) as exc:
        retrieve_chunks(db, uuid4(), "事务隔离级别", FakeEmbedder(), strategy="hybrid", rrf_k=0)
    assert exc.value.kind == "rank_constant"
    assert db.method_calls == []


def test_unknown_strategy_fails_before_either_branch() -> None:
    db = Mock()
    with pytest.raises(RetrievalStrategyError):
        retrieve_chunks(db, uuid4(), "事务隔离级别", FakeEmbedder(), strategy="sparse")
    assert db.method_calls == []


def test_hybrid_reorders_dense_evidence_without_rewriting_cosine(
    db: Session,
) -> None:
    course = add_course(db, "Hybrid course")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    strong = _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 1.0)
    lexical = _scaled_chunk(db, course, embedder, query, "事务隔离级别用于定义并发正确性", 0.4)
    keyword_only = _scaled_chunk(db, course, embedder, query, "事务隔离级别的另一种措辞", 0.01)

    hits = retrieve_chunks(db, course.id, query, embedder, strategy="hybrid")

    assert [hit.chunk_id for hit in hits] == [lexical.id, strong.id]
    assert keyword_only.id not in {hit.chunk_id for hit in hits}
    assert hits[0].score == pytest.approx(0.4)
    assert hits[1].score == pytest.approx(1.0)
    assert hits[0].score != pytest.approx(1 / 61 + 1 / 62)


def test_hybrid_keyword_only_course_is_not_sufficient_evidence(db: Session) -> None:
    course = add_course(db, "Keyword only")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 0.01)
    assert retrieve_chunks(db, course.id, query, embedder, strategy="hybrid") == []


def test_hybrid_uses_the_dense_threshold_only_on_the_dense_branch(db: Session) -> None:
    course = add_course(db, "Calibrated hybrid")
    embedder = FakeEmbedder()
    embedder.index_identity = "siliconflow|BAAI/bge-m3|1024|v1"
    query = "事务隔离级别"
    below = _scaled_chunk(db, course, embedder, query, query, 0.2)
    admitted = _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 0.5)

    hits = retrieve_chunks(db, course.id, query, embedder, strategy="hybrid")

    assert [hit.chunk_id for hit in hits] == [admitted.id]
    assert below.id not in {hit.chunk_id for hit in hits}
    assert hits[0].score == pytest.approx(0.5)


def test_hybrid_selects_after_fusion_instead_of_truncating_to_final_dense_top_k(
    db: Session,
) -> None:
    course = add_course(db, "Capped hybrid")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    strong = _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 1.0)
    support = _scaled_chunk(db, course, embedder, query, "事务隔离级别包括读未提交、读已提交", 0.4)

    dense = retrieve_chunks(db, course.id, query, embedder, top_k=1)
    assert [hit.chunk_id for hit in dense] == [strong.id]

    hits = retrieve_chunks(db, course.id, query, embedder, strategy="hybrid", top_k=1)

    assert [hit.chunk_id for hit in hits] == [support.id]
    assert hits[0].score == pytest.approx(0.4)


@pytest.mark.parametrize("body", [
    "事务隔离级别包括读未提交、读已提交、可重复读和串行化。",
    "事务隔离级别是本章标题，具体内容略。",
])
def test_keyword_only_candidates_survive_dense_recall_miss_but_do_not_authorize_answers(
    db: Session, body: str,
) -> None:
    course = add_course(db, "Candidate union")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    for _ in range(HYBRID_CANDIDATE_K):
        _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 0.8)
    lexical = _scaled_chunk(db, course, embedder, query, body, 0.01)

    assert lexical.id not in {
        hit.chunk_id for hit in retrieve_chunks(db, course.id, query, embedder)
    }
    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder)
    recovered = next(hit for hit in candidates if hit.chunk_id == lexical.id)
    assert len(candidates) == HYBRID_CANDIDATE_K + 1
    assert recovered.dense_rank is None
    assert recovered.cosine_score is None
    assert recovered.keyword_rank == 1
    assert recovered.bm25_score is not None
    # Even the first RRF candidate cannot bypass the independent admission gate.
    assert recovered.rrf_score == candidates[0].rrf_score
    evidence = retrieve_chunks(db, course.id, query, embedder, strategy="hybrid")
    assert lexical.id not in {hit.chunk_id for hit in evidence}


def test_low_cosine_is_retained_in_candidates_before_final_threshold(db: Session) -> None:
    course = add_course(db, "Threshold separated")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    low = _scaled_chunk(db, course, embedder, query, query, -0.2)
    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder, candidate_k=1)
    assert candidates[0].chunk_id == low.id
    assert candidates[0].cosine_score == pytest.approx(-0.2)
    assert candidates[0].bm25_score is not None
    assert retrieve_chunks(db, course.id, query, embedder, strategy="hybrid") == []


def test_postgres_candidate_statement_keeps_scope_and_budget_without_admission_threshold() -> None:
    statement = _postgres_retrieval_statement(
        uuid4(), FakeEmbedder(), [0.0] * 1024,
        top_k=HYBRID_CANDIDATE_K, min_score=None, excluded_document_ids={uuid4()},
    )
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "chunks.course_id =" in sql
    assert "chunks.embedding_model =" in sql
    assert "chunks.document_id NOT IN" in sql
    assert "ORDER BY distance" in sql
    assert " <= " not in sql
    assert HYBRID_CANDIDATE_K in compiled.params.values()


@pytest.mark.parametrize("budget", [True, -1, 101])
def test_invalid_candidate_budget_does_not_search(budget) -> None:
    db = Mock()
    with pytest.raises(FusionError, match="Retrieval fusion rejected"):
        retrieve_hybrid_candidates(db, uuid4(), "query", FakeEmbedder(), candidate_k=budget)
    assert db.method_calls == []


def test_zero_final_limit_skips_recall() -> None:
    db = Mock()
    assert retrieve_chunks(db, uuid4(), "query", FakeEmbedder(), strategy="hybrid", top_k=0) == []
    assert db.method_calls == []


def test_hybrid_honors_course_index_exclusion_deletion_and_index_change(db: Session) -> None:
    course = add_course(db, "Scoped hybrid")
    other = add_course(db, "Other hybrid")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    kept = _scaled_chunk(db, course, embedder, query, query, 1.0)
    excluded = _scaled_chunk(db, course, embedder, query, query, 1.0)
    _scaled_chunk(db, other, embedder, query, query, 1.0)
    stale = _scaled_chunk(db, course, embedder, query, query, 1.0)
    stale.embedding_model = "other-index"
    db.commit()

    scoped = retrieve_chunks(
        db,
        course.id,
        query,
        embedder,
        strategy="hybrid",
        excluded_document_ids={excluded.document_id},
    )
    assert {hit.chunk_id for hit in scoped} == {kept.id}
    candidates = retrieve_hybrid_candidates(
        db, course.id, query, embedder, excluded_document_ids={excluded.document_id},
    )
    assert {hit.chunk_id for hit in candidates} == {kept.id}

    db.delete(kept)
    db.commit()
    after_delete = retrieve_chunks(
        db,
        course.id,
        query,
        embedder,
        strategy="hybrid",
        excluded_document_ids={excluded.document_id},
    )
    assert after_delete == []
    assert retrieve_hybrid_candidates(
        db, course.id, query, embedder, excluded_document_ids={excluded.document_id},
    ) == []


def test_hybrid_keyword_failure_is_not_a_dense_fallback(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    course = add_course(db, "Limit hybrid")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 1.0)

    def exceed(*_args, **_kwargs):
        raise KeywordLimitExceeded("chunks")

    monkeypatch.setattr("app.services.keyword.retrieve_keyword_candidates", exceed)
    with pytest.raises(KeywordLimitExceeded) as exc:
        retrieve_chunks(db, course.id, query, embedder, strategy="hybrid")
    assert exc.value.resource == "chunks"


def test_hybrid_fusion_failure_does_not_return_a_partial_branch(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    course = add_course(db, "Fusion hybrid")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 1.0)
    def reject(*_args, **_kwargs):
        raise FusionError("identity")

    monkeypatch.setattr("app.services.retrieve.fuse_rrf", reject)
    with pytest.raises(FusionError) as exc:
        retrieve_chunks(db, course.id, query, embedder, strategy="hybrid")
    assert exc.value.kind == "identity"


def test_search_hybrid_score_remains_cosine(client: TestClient, db: Session, monkeypatch) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Search hybrid")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    lexical = _scaled_chunk(db, course, embedder, query, query, 0.4)
    strong = _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 1.0)
    monkeypatch.setattr(
        "app.api.search.get_settings",
        lambda: Settings(_env_file=None, retrieval_strategy="hybrid"),
    )

    response = client.post(f"/courses/{course.id}/search", json={"query": query})

    assert response.status_code == 200
    hits = response.json()["hits"]
    assert [hit["chunk_id"] for hit in hits] == [str(lexical.id), str(strong.id)]
    assert hits[0]["score"] == pytest.approx(0.4)
    assert hits[1]["score"] == pytest.approx(1.0)


def test_search_keyword_limit_is_not_an_empty_success(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Search limit")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 1.0)
    monkeypatch.setattr(
        "app.api.search.get_settings",
        lambda: Settings(_env_file=None, retrieval_strategy="hybrid"),
    )
    monkeypatch.setattr(
        "app.services.keyword.retrieve_keyword_candidates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeywordLimitExceeded("chunks")),
    )

    response = client.post(f"/courses/{course.id}/search", json={"query": query})

    assert response.status_code == 503
    assert response.json()["error_code"] == "KEYWORD_LIMIT"
    assert "hits" not in response.json()
    assert query not in response.text
    assert "chunks" not in response.json()["message"]


def test_reranking_uses_current_body_beyond_snippet_and_keeps_cosine(db: Session) -> None:
    course = add_course(db, "Body reranking")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    first = _scaled_chunk(db, course, embedder, query, query, 1.0)
    body = "正文背景。" * 60 + "事务隔离级别：可重复读支持重复查询。" + "正文尾部。" * 250
    support = _scaled_chunk(db, course, embedder, query, body, 0.4)
    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder)
    fake = FakeReranker([0.9 if hit.chunk_id == support.id else 0.1 for hit in candidates])

    hits = retrieve_chunks(
        db, course.id, query, embedder, strategy="hybrid", top_k=1, reranker=fake,
    )

    assert [hit.chunk_id for hit in hits] == [support.id]
    assert first.id != support.id
    assert hits[0].score == pytest.approx(0.4)
    sent = fake.calls[0][1]
    assert any("可重复读支持重复查询" in passage for passage in sent)
    assert max(map(len, sent)) == 1200
    assert "可重复读支持重复查询" not in hits[0].snippet


@pytest.mark.parametrize("body", [
    "事务隔离级别包括读未提交、读已提交、可重复读和串行化。",
    "事务隔离级别是本章标题，具体内容略。",
])
def test_keyword_only_support_and_no_answer_both_reach_reranker_without_automatic_admission(
    db: Session, body: str,
) -> None:
    course = add_course(db, "Unadmitted reranking")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    for _ in range(HYBRID_CANDIDATE_K):
        _scaled_chunk(db, course, embedder, query, "qqqq-cooking-recipe", 0.8)
    lexical = _scaled_chunk(db, course, embedder, query, body, 0.01)
    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder)
    assert next(hit for hit in candidates if hit.chunk_id == lexical.id).cosine_score is None
    fake = FakeReranker([0.999 if hit.chunk_id == lexical.id else 0.1 for hit in candidates])
    hits = retrieve_chunks(db, course.id, query, embedder, strategy="hybrid", reranker=fake)
    assert len(fake.calls[0][1]) == HYBRID_CANDIDATE_K + 1
    assert body in fake.calls[0][1]
    assert lexical.id not in {hit.chunk_id for hit in hits}
    assert len(hits) == 8


@pytest.mark.parametrize("change", ["delete", "index", "empty"])
def test_reranker_rechecks_deletion_index_and_empty_body_before_sending(
    db: Session, monkeypatch, change: str,
) -> None:
    course = add_course(db, "Current rerank scope")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    hit = _scaled_chunk(db, course, embedder, query, query, 1.0)

    def recall_then_change(*args, **kwargs):
        candidates = retrieve_hybrid_candidates(*args, **kwargs)
        if change == "delete":
            db.delete(hit)
        elif change == "index":
            hit.embedding_model = "other-index"
        else:
            hit.text = " "
        db.commit()
        return candidates

    monkeypatch.setattr("app.services.retrieve.retrieve_hybrid_candidates", recall_then_change)
    fake = FakeReranker()
    assert retrieve_chunks(db, course.id, query, embedder, strategy="hybrid", reranker=fake) == []
    assert fake.calls == []


def test_rerank_transmits_only_current_course_compatible_nonexcluded_text(db: Session) -> None:
    course = add_course(db, "Scope")
    other = add_course(db, "Other")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    kept = _scaled_chunk(db, course, embedder, query, query + "保留", 1.0)
    excluded = _scaled_chunk(db, course, embedder, query, query + "排除", 1.0)
    _scaled_chunk(db, other, embedder, query, query + "外课", 1.0)
    stale = _scaled_chunk(db, course, embedder, query, query + "旧索引", 1.0)
    stale.embedding_model = "other-index"
    db.commit()
    fake = FakeReranker()
    hits = retrieve_chunks(
        db, course.id, query, embedder, strategy="hybrid", reranker=fake,
        excluded_document_ids={excluded.document_id},
    )
    assert [hit.chunk_id for hit in hits] == [kept.id]
    assert fake.calls == [(query, [query + "保留"])]


def test_dense_rejects_reranking_instead_of_silently_ignoring_it() -> None:
    db = Mock()
    with pytest.raises(RetrievalStrategyError):
        retrieve_chunks(db, uuid4(), "query", FakeEmbedder(), reranker=FakeReranker())
    assert db.method_calls == []


def test_oversized_union_is_not_silently_truncated_for_reranking(db: Session) -> None:
    course = add_course(db, "Bounded reranking")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    for _ in range(65):
        _scaled_chunk(db, course, embedder, query, query, 0.8)
    fake = FakeReranker()
    with pytest.raises(RerankError):
        retrieve_chunks(db, course.id, query, embedder, strategy="hybrid", top_k=100, reranker=fake)
    assert fake.calls == []


def test_search_uses_reranking_order_with_the_existing_cosine_api(client, db, monkeypatch) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Rerank search")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = FakeEmbedder()
    query = "事务隔离级别"
    _scaled_chunk(db, course, embedder, query, query, 0.9)
    target = _scaled_chunk(db, course, embedder, query, query + "定义", 0.4)
    candidates = retrieve_hybrid_candidates(db, course.id, query, embedder)
    fake = FakeReranker([0.9 if hit.chunk_id == target.id else 0.1 for hit in candidates])
    app.dependency_overrides[get_reranker] = lambda: fake
    monkeypatch.setattr("app.api.search.get_settings", lambda: Settings(_env_file=None, retrieval_strategy="hybrid"))
    response = client.post(f"/courses/{course.id}/search", json={"query": query})
    assert response.status_code == 200
    first = response.json()["hits"][0]
    assert first["chunk_id"] == str(target.id)
    assert first["score"] == pytest.approx(0.4)
    fake.score = Mock(side_effect=RerankError("private-error"))
    failed = client.post(f"/courses/{course.id}/search", json={"query": query})
    assert failed.status_code == 503
    assert failed.json()["error_code"] == "RERANK_FAILED"
    assert "hits" not in failed.json()
    assert "private-error" not in failed.text
