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
    assert body["summary"]["recorded_attempts"] == 7
    assert body["summary"]["student_attempts"] == 5
    assert body["summary"]["cited_answer"] == 2
    assert body["summary"]["no_evidence"] == 3
    assert body["summary"]["failure"] == 0
    assert body["summary"]["knowledge_attempts"] == 5
    assert body["summary"]["distinct_student_questions"] >= 1
    assert body["summary"]["no_evidence_rate"] == 0.6
    assert body["summary"]["cited_answer_rate"] == 0.4
    assert body["summary"]["failure_rate"] == 0.0
    assert body["summary"]["rate_denominator"] == "student_attempts"
    assert body["summary"]["sample_limited"] is True
    assert body["metric_contract"] == "metrics-v1"
    assert isinstance(body["themes"], list) and isinstance(body["clues"], list)
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

    assert body["summary"]["student_attempts"] == 4
    assert body["summary"]["cited_answer"] == 1
    assert body["summary"]["no_evidence"] == 1
    assert body["summary"]["failure"] == 1
    assert body["summary"]["unknown_outcome"] == 1
    assert body["summary"]["knowledge_attempts"] == 2
    assert body["summary"]["no_evidence_rate"] == 0.25
    assert body["summary"]["cited_answer_rate"] == 0.25
    assert body["summary"]["failure_rate"] == 0.25
    assert body["summary"]["rate_denominator"] == "student_attempts"
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


def test_non_knowledge_outcomes_use_student_denominator_rates(client, db) -> None:
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
    # metrics-v1: denominator is student_attempts; zero numerators yield 0.0 not None
    assert body["summary"]["no_evidence_rate"] == 0.0
    assert body["summary"]["cited_answer_rate"] == 0.0
    assert body["summary"]["failure_rate"] == (1 / 3)
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


def _local_days(start: datetime, end: datetime):
    local = timezone(timedelta(hours=8))
    start, end = start.astimezone(local), end.astimezone(local)
    day = datetime(start.year, start.month, start.day, tzinfo=local)
    last = end - timedelta(microseconds=1)
    last_day = datetime(last.year, last.month, last.day, tzinfo=local)
    days = []
    while day <= last_day:
        days.append(day)
        day += timedelta(days=1)
    return days


def test_trend_buckets_student_outcomes_on_shanghai_days(client, db) -> None:
    teacher = add_user(db, "trend", "pass", UserRole.teacher)
    course = add_course(db, "Trend Course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    now = datetime.now(UTC)
    start = now - timedelta(hours=50)
    cited_at = start
    failure_at = start + timedelta(seconds=1)
    unknown_at = start + timedelta(seconds=2)
    for when, role, outcome, query in [
        (cited_at, "student", "cited_answer", "学生有引用"),
        (failure_at, "student", "failure", "学生失败"),
        (unknown_at, "student", None, "学生未知"),
        (start + timedelta(seconds=3), "teacher", "cited_answer", "教师不进趋势"),
        (start + timedelta(seconds=4), None, "cited_answer", "未知角色不进趋势"),
    ]:
        _add_log(db, course_id=course.id, user_id=teacher.id, query=query, hit=True,
                 error_code=None, created_at=when, role=role, outcome=outcome)
    db.commit()
    login_as(client, teacher.username, "pass")

    body = client.get(f"/courses/{course.id}/insights", params={
        "start_at": start.isoformat(), "end_at": now.isoformat(),
    }).json()

    window_start = datetime.fromisoformat(body["window_start"])
    window_end = datetime.fromisoformat(body["window_end"])
    buckets = [datetime.fromisoformat(row["bucket_start"]) for row in body["trend"]]
    assert buckets == _local_days(window_start, window_end)
    assert buckets[0] == _local_days(cited_at, cited_at + timedelta(seconds=1))[0]
    first = body["trend"][0]
    assert first["cited_answer"] == 1
    assert first["failure"] == 1
    assert first["unknown_outcome"] == 1
    assert first["no_evidence"] == 0
    assert any(not any(row[key] for key in ("cited_answer", "no_evidence", "failure", "unknown_outcome"))
               for row in body["trend"])
    assert sum(sum(row[key] for key in ("cited_answer", "no_evidence", "failure", "unknown_outcome"))
               for row in body["trend"]) == body["summary"]["student_attempts"] == 3
    assert body["summary"]["non_student_attempts"] == 1
    assert body["summary"]["unknown_role_attempts"] == 1
    assert body["frequent"] == [{"query": "学生有引用", "count": 1}]
    assert body["no_evidence"] == []


def test_trend_shanghai_midnight_and_utc_midnight(db) -> None:
    from app.services.insights import aggregate_course_insights

    teacher = add_user(db, "shanghai-buckets", "pass", UserRole.teacher)
    course = add_course(db, "Shanghai Buckets")
    for hour, minute, outcome in [(15, 59, "cited_answer"), (16, 0, "no_evidence"),
                                  (23, 59, "failure"), (24, 0, "unknown_outcome")]:
        when = datetime(2026, 10, 15, tzinfo=UTC) + timedelta(hours=hour, minutes=minute)
        _add_log(db, course_id=course.id, user_id=teacher.id, query="时区边界",
                 hit=True, error_code=None, created_at=when, outcome=outcome)
    _add_log(db, course_id=course.id, user_id=teacher.id, query="午夜前一微秒",
             hit=True, error_code=None, outcome="cited_answer",
             created_at=datetime(2026, 10, 15, 15, 59, 59, 999999, tzinfo=UTC))
    db.commit()
    body = aggregate_course_insights(
        db, course.id, window_start=datetime(2026, 10, 15, 15, tzinfo=UTC),
        window_end=datetime(2026, 10, 17, 16, tzinfo=UTC),
    )
    assert [row["bucket_start"].isoformat() for row in body["trend"]] == [
        "2026-10-15T00:00:00+08:00", "2026-10-16T00:00:00+08:00",
        "2026-10-17T00:00:00+08:00",
    ]
    assert body["trend"][0]["cited_answer"] == 2
    assert body["trend"][1] == {
        "bucket_start": datetime(2026, 10, 16, tzinfo=timezone(timedelta(hours=8))),
        "cited_answer": 0, "no_evidence": 1, "failure": 1, "unknown_outcome": 1,
    }
    assert all(body["trend"][2][key] == 0
               for key in ("cited_answer", "no_evidence", "failure", "unknown_outcome"))


def test_postgres_trend_bucket_uses_shanghai_timezone() -> None:
    from app.services.insights import _bucket_start, _local_day
    from sqlalchemy.dialects import postgresql

    expression = _local_day(QueryLog.created_at, "postgresql")
    sql = str(expression.compile(dialect=postgresql.dialect(),
                                 compile_kwargs={"literal_binds": True}))
    assert "timezone('Asia/Shanghai', query_logs.created_at)" in sql
    wall_midnight = datetime(2026, 10, 16, tzinfo=UTC).replace(tzinfo=None)
    assert _bucket_start(wall_midnight).isoformat() == "2026-10-16T00:00:00+08:00"
