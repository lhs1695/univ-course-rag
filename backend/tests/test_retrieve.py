"""Retrieval tests use FakeEmbedder token/bigram hashing so shared terms rank higher.

Do not weaken golden.json if a query misses; fix retrieve/embedder instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.user import User, UserRole
from fastapi.testclient import TestClient
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
    content_type = "application/pdf" if suffix == ".pdf" else "text/markdown"
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
    }
    login_as(client, "alice", "pass")
    assert len(GOLDEN) >= 3
    sources = {item["source_file"] for item in GOLDEN}
    assert "sample.md" in sources and "sample.pdf" in sources
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
