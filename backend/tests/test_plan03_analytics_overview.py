
"""PLAN-03: metrics-v1 overview denominators, themes/clues, privacy/cross-course."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.course import CourseMemberRole
from app.models.query_log import QueryLog, QueryOutcome
from app.models.user import UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_courses import add_course, add_member, login_as


def _log(db, *, course_id, user_id, query, outcome, created_at, role="student"):
    db.add(QueryLog(
        id=uuid4(),
        course_id=course_id,
        user_id=user_id,
        query=query,
        hit=True,
        outcome=outcome,
        member_role_at_ask=role,
        chunk_ids="[]",
        duration_ms=1,
        created_at=created_at,
    ))


def test_plan03_overview_denominators_themes_clues_and_sample_flag(client: TestClient, db: Session):
    teacher = add_user(db, "p03-t", "pass", UserRole.teacher)
    student = add_user(db, "p03-s", "pass", UserRole.student)
    course = add_course(db, "P03 Course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    now = datetime.now(UTC)
    for _ in range(3):
        _log(db, course_id=course.id, user_id=student.id, query="什么是向量",
             outcome=QueryOutcome.no_evidence.value, created_at=now - timedelta(hours=1))
    _log(db, course_id=course.id, user_id=student.id, query="什么是矩阵",
         outcome=QueryOutcome.cited_answer.value, created_at=now - timedelta(hours=2))
    _log(db, course_id=course.id, user_id=student.id, query="什么是矩阵",
         outcome=QueryOutcome.cited_answer.value, created_at=now - timedelta(hours=3))
    for _ in range(3):
        _log(db, course_id=course.id, user_id=student.id, query="超时问题",
             outcome=QueryOutcome.failure.value, created_at=now - timedelta(minutes=30))
    db.commit()
    login_as(client, teacher.username, "pass")
    body = client.get(f"/courses/{course.id}/insights").json()
    summary = body["summary"]
    assert summary["student_attempts"] == 8
    assert summary["distinct_student_questions"] == 3
    assert summary["cited_answer"] == 2
    assert summary["no_evidence"] == 3
    assert summary["failure"] == 3
    assert summary["cited_answer_rate"] == 2 / 8
    assert summary["no_evidence_rate"] == 3 / 8
    assert summary["failure_rate"] == 3 / 8
    assert summary["rate_denominator"] == "student_attempts"
    assert summary["sample_limited"] is True
    assert body["metric_contract"] == "metrics-v1"
    assert any(c["trigger"] == "no_evidence_repeat" for c in body["clues"])
    assert any(c["trigger"] == "system_failure_volume" for c in body["clues"])
    assert "user_id" not in body
    themes = body["themes"]
    assert themes and themes[0]["status"] == "candidate"
    assert themes[0]["sort_reason_label"]


def test_plan03_student_and_cross_course_denied(client: TestClient, db: Session):
    teacher = add_user(db, "p03-t2", "pass", UserRole.teacher)
    student = add_user(db, "p03-s2", "pass", UserRole.student)
    other = add_user(db, "p03-t3", "pass", UserRole.teacher)
    c1 = add_course(db, "P03 A")
    c2 = add_course(db, "P03 B")
    add_member(db, c1, teacher, CourseMemberRole.teacher)
    add_member(db, c1, student, CourseMemberRole.student)
    add_member(db, c2, other, CourseMemberRole.teacher)
    login_as(client, student.username, "pass")
    assert client.get(f"/courses/{c1.id}/insights").status_code == 403
    login_as(client, other.username, "pass")
    assert client.get(f"/courses/{c1.id}/insights").status_code == 403
