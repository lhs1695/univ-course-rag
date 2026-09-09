"""Ask tests use FakeLLM. Do not change golden.json to fit generation."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import pytest
from app.main import app
from app.models.course import CourseMemberRole
from app.models.query_log import QueryLog
from app.models.user import UserRole
from app.services.generate import NO_EVIDENCE
from app.services.llm import FakeLLM, get_llm, parse_cited_ids
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_retrieve import (
    FIXTURES,
    GOLDEN,
    UNRELATED,
    add_course,
    add_member,
    login_as,
    upload,
)


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
    assert json.loads(log.chunk_ids) == []
    assert log.duration_ms >= 0
    assert "sk-" not in (log.query or "")


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


@pytest.mark.parametrize("answer", ["没有引用的回答。", "编造 [Source 00000000-0000-0000-0000-000000000000]"])
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


def test_ask_requires_membership(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    add_user(db, "bob", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "bob", "pass")
    response = client.post(f"/courses/{course.id}/ask", json={"query": "anything"})
    assert response.status_code == 403
