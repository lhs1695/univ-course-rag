from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.models.course import CourseMember, CourseMemberRole
from app.models.query_log import QueryLog, QueryOutcome
from app.models.user import UserRole
from app.services.generate import NO_EVIDENCE
from fastapi.testclient import TestClient
from sqlalchemy import select
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
    role: str | None = "student",
    outcome: str | None = "auto",
) -> None:
    db.add(
        QueryLog(
            id=uuid4(),
            course_id=course_id,
            user_id=user_id,
            query=query,
            hit=hit,
            member_role_at_ask=role,
            outcome=(
                QueryOutcome.no_evidence if error_code == NO_EVIDENCE
                else QueryOutcome.failure if error_code
                else QueryOutcome.cited_answer
            ) if outcome == "auto" else outcome,
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

    t0 = datetime.now(UTC) - timedelta(hours=4)
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
        role="teacher",
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
        role="teacher",
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
    assert body["retention_days"] == 90
    assert body["summary"] == {
        "recorded_attempts": 7, "student_attempts": 5, "cited_answer": 2,
        "no_evidence": 3, "failure": 0, "unknown_outcome": 0,
        "non_student_attempts": 2, "unknown_role_attempts": 0,
        "knowledge_attempts": 5, "no_evidence_rate": 0.6,
    }
    assert "frequent" in body
    assert "no_evidence" in body
    assert body["frequent"] == [{"query": "什么是 向量检索", "count": 2}]
    assert len(body["no_evidence"]) == 1
    miss = body["no_evidence"][0]
    assert miss["query"] == "课件里有期末范围吗"
    assert miss["count"] == 3
    assert miss["last_asked_at"].startswith(t3.replace(tzinfo=None).isoformat())


def test_insights_excludes_queries_outside_retention_window(
    client: TestClient, db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("QUERY_LOG_RETENTION_DAYS", "30")
    teacher = add_user(db, "teacher-retention", "pass", UserRole.teacher)
    student = add_user(db, "student-retention", "pass", UserRole.student)
    course = add_course(db, "Retention Course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    now = datetime.now(UTC)
    _add_log(
        db,
        course_id=course.id,
        user_id=student.id,
        query="已经到期的问题",
        hit=True,
        error_code=None,
        created_at=now - timedelta(days=31),
    )
    _add_log(
        db,
        course_id=course.id,
        user_id=student.id,
        query="仍在留存期的问题",
        hit=True,
        error_code=None,
        created_at=now - timedelta(days=29),
    )
    db.commit()

    login_as(client, teacher.username, "pass")
    response = client.get(f"/courses/{course.id}/insights")

    assert response.status_code == 200
    assert response.json()["retention_days"] == 30
    assert response.json()["frequent"] == [{"query": "仍在留存期的问题", "count": 1}]


def test_student_cannot_open_insights(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)

    login_as(client, "alice", "pass")
    response = client.get(f"/courses/{course.id}/insights")
    assert response.status_code == 403


def test_historical_roles_are_not_rewritten_by_current_membership(client, db) -> None:
    teacher = add_user(db, "observer", "pass", UserRole.teacher)
    promoted = add_user(db, "promoted", "pass", UserRole.student)
    removed = add_user(db, "removed", "pass", UserRole.student)
    current = add_user(db, "current", "pass", UserRole.student)
    course = add_course(db, "Snapshot Course")
    for user, role in [(teacher, "teacher"), (promoted, "student"), (removed, "student"), (current, "student")]:
        add_member(db, course, user, CourseMemberRole(role))
    now = datetime.now(UTC) - timedelta(hours=1)
    for user, role, outcome, query in [
        (promoted, "student", "cited_answer", "学生时的回答"),
        (removed, "student", "no_evidence", "移出前的不足"),
        (current, "teacher", "cited_answer", "教师时不算学生"),
        (current, None, None, "旧日志不推断角色与结果"),
        (current, "student", None, "已知角色但结果未知"),
        (promoted, "student", "failure", "服务失败不算不足"),
    ]:
        _add_log(db, course_id=course.id, user_id=user.id, query=query, hit=True,
                 error_code=None, created_at=now, role=role, outcome=outcome)
    memberships = db.scalars(select(CourseMember).where(CourseMember.course_id == course.id)).all()
    for member in memberships:
        if member.user_id == promoted.id:
            member.role = "teacher"
        if member.user_id == removed.id:
            db.delete(member)
    db.commit()
    login_as(client, teacher.username, "pass")

    body = client.get(f"/courses/{course.id}/insights").json()

    assert body["summary"] == {
        "recorded_attempts": 6, "student_attempts": 4, "cited_answer": 1,
        "no_evidence": 1, "failure": 1, "unknown_outcome": 1,
        "non_student_attempts": 1, "unknown_role_attempts": 1,
        "knowledge_attempts": 2, "no_evidence_rate": 0.5,
    }
    assert body["frequent"] == [{"query": "学生时的回答", "count": 1}]
    assert [row["query"] for row in body["no_evidence"]] == ["移出前的不足"]


def test_time_window_is_utc_half_open_and_counts_repeated_attempts(client, db) -> None:
    teacher = add_user(db, "window", "pass", UserRole.teacher)
    course = add_course(db, "Window Course")
    other_course = add_course(db, "Other Course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    start = datetime.now(UTC) - timedelta(hours=4)
    end = start + timedelta(hours=1)
    for course_id, when in [
        (course.id, start - timedelta(microseconds=1)),
        (course.id, start), (course.id, end - timedelta(microseconds=1)),
        (course.id, end), (other_course.id, start),
    ]:
        _add_log(db, course_id=course_id, user_id=teacher.id, query="同次问句的重复提交",
                 hit=True, error_code=None, created_at=when, role="student")
    db.commit()
    login_as(client, teacher.username, "pass")

    response = client.get(f"/courses/{course.id}/insights", params={
        "start_at": start.astimezone(timezone(timedelta(hours=8))).isoformat(),
        "end_at": end.isoformat(),
    })

    assert response.status_code == 200
    body = response.json()
    assert datetime.fromisoformat(body["window_start"]) == start
    assert datetime.fromisoformat(body["window_end"]) == end
    assert body["summary"]["recorded_attempts"] == 2
    assert body["frequent"] == [{"query": "同次问句的重复提交", "count": 2}]


@pytest.mark.parametrize("params", [
    {"start_at": "2026-01-01T00:00:00"},  # timezone required
    {"start_at": "2099-01-01T00:00:00Z"},
    {"start_at": "2099-01-02T00:00:00Z", "end_at": "2099-01-01T00:00:00Z"},
    {"start_at": "2000-01-01T00:00:00Z", "end_at": "2000-01-02T00:00:00Z"},
])
def test_invalid_or_expired_time_windows_are_rejected(client, db, params) -> None:
    teacher = add_user(db, "bad-window", "pass", UserRole.teacher)
    course = add_course(db, "Invalid Window")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    assert client.get(f"/courses/{course.id}/insights", params=params).status_code == 422


def test_no_known_knowledge_outcomes_has_no_rate(client, db) -> None:
    teacher = add_user(db, "empty-rate", "pass", UserRole.teacher)
    course = add_course(db, "Empty Rate")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    empty = client.get(f"/courses/{course.id}/insights").json()
    assert empty["summary"]["recorded_attempts"] == 0
    assert empty["summary"]["no_evidence_rate"] is None
    for outcome in ["failure", None, "unrecognized"]:
        _add_log(db, course_id=course.id, user_id=teacher.id, query="不进入知识结果分母",
                 hit=True, error_code=None, created_at=datetime.now(UTC), outcome=outcome)
    db.commit()
    body = client.get(f"/courses/{course.id}/insights").json()
    assert body["summary"]["student_attempts"] == 3
    assert body["summary"]["unknown_outcome"] == 2
    assert body["summary"]["no_evidence_rate"] is None
    assert body["frequent"] == body["no_evidence"] == []


def test_requested_window_is_clipped_to_retention_and_now(client, db, monkeypatch) -> None:
    monkeypatch.setenv("QUERY_LOG_RETENTION_DAYS", "30")
    teacher = add_user(db, "clipped", "pass", UserRole.teacher)
    course = add_course(db, "Clipped Window")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    now = datetime.now(UTC)
    for days, query in [(-31, "到期"), (-29, "保留"), (1, "未来时间")]:
        _add_log(db, course_id=course.id, user_id=teacher.id, query=query, hit=True,
                 error_code=None, created_at=now + timedelta(days=days))
    db.commit()
    login_as(client, teacher.username, "pass")
    body = client.get(f"/courses/{course.id}/insights", params={
        "start_at": "2000-01-01T00:00:00Z", "end_at": "2099-01-01T00:00:00Z",
    }).json()
    start, end = map(datetime.fromisoformat, [body["window_start"], body["window_end"]])
    assert start == end - timedelta(days=30)
    assert now <= end <= datetime.now(UTC)
    assert body["summary"]["recorded_attempts"] == 1
    assert body["frequent"] == [{"query": "保留", "count": 1}]
