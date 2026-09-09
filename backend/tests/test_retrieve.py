"""Retrieval tests use FakeEmbedder token/bigram hashing so shared terms rank higher.

Do not weaken golden.json if a query misses; fix retrieve/embedder instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.document import Chunk, Document
from app.models.user import User, UserRole
from app.services.embedder import FakeEmbedder
from app.services.retrieve import (
    _postgres_retrieval_statement,
    has_incompatible_chunks,
    retrieve_chunks,
)
from fastapi.testclient import TestClient
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


def upload(client: TestClient, course_id: UUID, path: Path) -> UUID:
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
    return doc_id


def test_golden_hits_md_and_pdf(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    login_as(client, "t1", "pass")
    by_file = {
        "sample.md": upload(client, course.id, FIXTURES / "sample.md"),
        "sample.pdf": upload(client, course.id, FIXTURES / "sample.pdf"),
        "sample.pptx": upload(client, course.id, FIXTURES / "sample.pptx"),
        "sample.docx": upload(client, course.id, FIXTURES / "sample.docx"),
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
    upload(client, course.id, FIXTURES / "sample.md")
    response = client.post(f"/courses/{course.id}/search", json={"query": UNRELATED})
    assert response.status_code == 200
    assert response.json()["hits"] == []


def test_retrieve_only_uses_matching_index_identity(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    document_id = upload(client, course.id, FIXTURES / "sample.md")
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
    assert "Sort Key: ((embedding <=>" in plan


def test_search_does_not_leak_other_course(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course1 = add_course(db, "Course 1")
    course2 = add_course(db, "Course 2")
    add_member(db, course1, teacher, CourseMemberRole.teacher)
    add_member(db, course2, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    doc1 = upload(client, course1.id, FIXTURES / "sample.md")
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
