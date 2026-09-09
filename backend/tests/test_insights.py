from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.course import CourseMemberRole
from app.models.query_log import QueryLog
from app.models.user import UserRole
from app.services.generate import NO_EVIDENCE
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_courses import add_course, add_member, login_as


def _add_log(
    db: Session,
    *,
    course_id,
    user_id,
    query: str,
    hit: bool,
    error_code: str | None,
    created_at: datetime,
) -> None:
    db.add(
        QueryLog(
            id=uuid4(),
            course_id=course_id,
            user_id=user_id,
            query=query,
            hit=hit,
            error_code=error_code,
            chunk_ids="[]",
            duration_ms=1,
            created_at=created_at,
        )
    )


def test_insights_aggregates_student_queries_without_identities(
    client: TestClient, db: Session
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student_a = add_user(db, "alice", "pass", UserRole.student)
    student_b = add_user(db, "bob", "pass", UserRole.student)
    outsider = add_user(db, "carol", "pass", UserRole.student)
    course1 = add_course(db, "Course 1")
    course2 = add_course(db, "Course 2")
    add_member(db, course1, teacher, CourseMemberRole.teacher)
    add_member(db, course1, student_a, CourseMemberRole.student)
    add_member(db, course1, student_b, CourseMemberRole.student)
    add_member(db, course2, teacher, CourseMemberRole.teacher)
    add_member(db, course2, outsider, CourseMemberRole.student)

    t0 = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)
    t1 = t0 + timedelta(hours=1)
    t2 = t0 + timedelta(hours=2)
    t3 = t0 + timedelta(hours=3)

    _add_log(
        db,
        course_id=course1.id,
        user_id=student_a.id,
        query="  什么是  向量检索  ",
        hit=True,
        error_code=None,
        created_at=t0,
    )
    _add_log(
        db,
        course_id=course1.id,
        user_id=student_b.id,
        query="什么是 向量检索",
        hit=True,
        error_code=None,
        created_at=t1,
    )
    _add_log(
        db,
        course_id=course1.id,
        user_id=teacher.id,
        query="什么是 向量检索",
        hit=True,
        error_code=None,
        created_at=t2,
    )
    _add_log(
        db,
        course_id=course1.id,
        user_id=student_a.id,
        query="课件里有期末范围吗",
        hit=False,
        error_code=NO_EVIDENCE,
        created_at=t1,
    )
    _add_log(
        db,
        course_id=course1.id,
        user_id=student_b.id,
        query="  课件里有期末范围吗  ",
        hit=False,
        error_code=NO_EVIDENCE,
        created_at=t3,
    )
    _add_log(
        db,
        course_id=course1.id,
        user_id=student_a.id,
        query="课件里有期末范围吗",
        hit=True,
        error_code=NO_EVIDENCE,
        created_at=t3,
    )
    _add_log(
        db,
        course_id=course1.id,
        user_id=teacher.id,
        query="课件里有期末范围吗",
        hit=False,
        error_code=NO_EVIDENCE,
        created_at=t3 + timedelta(hours=1),
    )
    _add_log(
        db,
        course_id=course2.id,
        user_id=outsider.id,
        query="什么是 向量检索",
        hit=True,
        error_code=None,
        created_at=t3,
    )
    db.commit()

    login_as(client, "t1", "pass")
    response = client.get(f"/courses/{course1.id}/insights")
    assert response.status_code == 200
    body = response.json()
    dumped = response.text
    assert "user_id" not in dumped
    assert "username" not in dumped
    assert "alice" not in dumped
    assert "bob" not in dumped
    assert "carol" not in dumped
    assert "t1" not in dumped
    assert "unique" not in dumped.lower()
    assert "frequent" in body
    assert "no_evidence" in body
    assert body["frequent"] == [{"query": "什么是 向量检索", "count": 2}]
    assert len(body["no_evidence"]) == 1
    miss = body["no_evidence"][0]
    assert miss["query"] == "课件里有期末范围吗"
    assert miss["count"] == 3
    assert miss["last_asked_at"].startswith("2026-03-01T11:00:00")


def test_student_cannot_open_insights(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)

    login_as(client, "alice", "pass")
    response = client.get(f"/courses/{course.id}/insights")
    assert response.status_code == 403
