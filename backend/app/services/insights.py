from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session as DbSession

from app.models.course import CourseMemberRole
from app.models.query_log import QueryLog, QueryOutcome

NORMALIZE_MAX_CHARS = 200


def normalize_query(text: str) -> str:
    collapsed = " ".join((text or "").split())
    return collapsed[:NORMALIZE_MAX_CHARS]


def _utc(value: datetime) -> datetime:
    # SQLite drops timezone information; stored test times are UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def aggregate_course_insights(
    db: DbSession,
    course_id: UUID,
    *,
    window_start: datetime,
    window_end: datetime,
) -> dict:
    scope = (
        QueryLog.course_id == course_id,
        QueryLog.created_at >= window_start,
        QueryLog.created_at < window_end,
    )
    listed_query = case((and_(
        QueryLog.member_role_at_ask == CourseMemberRole.student.value,
        QueryLog.outcome.in_([QueryOutcome.cited_answer.value, QueryOutcome.no_evidence.value]),
    ), QueryLog.query), else_=None)
    # One statement keeps totals and lists consistent if another attempt commits meanwhile.
    # Do not load identities or non-student/unknown question text.
    counts = db.execute(
        select(
            QueryLog.member_role_at_ask, QueryLog.outcome, listed_query,
            func.count(), func.max(QueryLog.created_at),
        )
        .where(*scope)
        .group_by(QueryLog.member_role_at_ask, QueryLog.outcome, listed_query)
    ).all()
    summary = dict.fromkeys((
        "recorded_attempts", "student_attempts", "cited_answer", "no_evidence", "failure",
        "unknown_outcome", "non_student_attempts", "unknown_role_attempts",
    ), 0)
    frequent_counts: dict[str, int] = defaultdict(int)
    no_evidence_groups: dict[str, dict] = {}
    for role, outcome, query, count, last_at in counts:
        summary["recorded_attempts"] += count
        if role == CourseMemberRole.student.value:
            summary["student_attempts"] += count
            key = outcome if outcome in QueryOutcome else "unknown_outcome"
            summary[key] += count
        elif role == CourseMemberRole.teacher.value:
            summary["non_student_attempts"] += count
        else:
            summary["unknown_role_attempts"] += count
        key = normalize_query(query)
        if not key:
            continue
        if outcome == QueryOutcome.cited_answer:
            frequent_counts[key] += count
        elif outcome == QueryOutcome.no_evidence:
            last_at = _utc(last_at)
            group = no_evidence_groups.setdefault(key, {"count": 0, "last_asked_at": last_at})
            group["count"] += count
            group["last_asked_at"] = max(group["last_asked_at"], last_at)
    denominator = summary["cited_answer"] + summary["no_evidence"]
    summary["knowledge_attempts"] = denominator
    summary["no_evidence_rate"] = summary["no_evidence"] / denominator if denominator else None

    frequent = [
        {
            "query": query,
            "count": count,
        }
        for query, count in frequent_counts.items()
    ]
    frequent.sort(key=lambda row: (-row["count"], row["query"]))

    no_evidence = [
        {
            "query": query,
            "count": group["count"],
            "last_asked_at": group["last_asked_at"],
        }
        for query, group in no_evidence_groups.items()
    ]
    no_evidence.sort(key=lambda row: (-row["last_asked_at"].timestamp(), -row["count"], row["query"]))
    return {
        "window_start": window_start,
        "window_end": window_end,
        "summary": summary,
        "frequent": frequent,
        "no_evidence": no_evidence,
    }
