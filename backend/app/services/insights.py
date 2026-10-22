from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.models.course import CourseMemberRole
from app.models.query_log import QueryLog, QueryOutcome

NORMALIZE_MAX_CHARS = 200
SAMPLE_LIMIT_N = 30  # metrics-v1 low-sample gate
SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")


def normalize_query(text: str) -> str:
    collapsed = " ".join((text or "").split())
    return collapsed[:NORMALIZE_MAX_CHARS]


def _utc(value: datetime) -> datetime:
    # SQLite drops timezone information; stored test times are UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _local_day(column, dialect: str):
    # One expression is reused in SELECT and GROUP BY so list totals and the
    # daily series come from the same statement.
    if dialect == "postgresql":
        return func.date_trunc("day", func.timezone("Asia/Shanghai", column))
    if dialect == "sqlite":
        # Drop subsecond digits so SQLite cannot round across local midnight.
        return func.date(func.substr(column, 1, 19), "+8 hours")
    raise RuntimeError(f"Unsupported insights day bucket dialect: {dialect}")


def _bucket_start(value: datetime | str) -> datetime:
    if isinstance(value, str):
        year, month, day = (int(part) for part in value[:10].split("-"))
        return datetime(year, month, day, tzinfo=SHANGHAI)
    # SQL returns a naive wall-clock midnight in Asia/Shanghai.
    return datetime(value.year, value.month, value.day, tzinfo=SHANGHAI)


def _local_days(window_start: datetime, window_end: datetime):
    start = _utc(window_start).astimezone(SHANGHAI)
    end = _utc(window_end).astimezone(SHANGHAI)
    day = datetime(start.year, start.month, start.day, tzinfo=SHANGHAI)
    last_instant = end - timedelta(microseconds=1)
    last = datetime(last_instant.year, last_instant.month, last_instant.day, tzinfo=SHANGHAI)
    while day <= last:
        yield day
        day += timedelta(days=1)


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
    reviewable = and_(
        QueryLog.member_role_at_ask == CourseMemberRole.student.value,
        QueryLog.outcome.in_([QueryOutcome.cited_answer.value, QueryOutcome.no_evidence.value]),
        # Missing-context follow-ups and meaningless inputs are not reviewable course questions.
        or_(QueryLog.error_code.is_(None), QueryLog.error_code.not_in(["NEEDS_CONTEXT", "INVALID_QUESTION"])),
    )
    listed_query = case((reviewable, QueryLog.query), else_=None)
    student_query = case(
        (QueryLog.member_role_at_ask == CourseMemberRole.student.value, QueryLog.query),
        else_=None,
    )
    bucket = _local_day(QueryLog.created_at, db.get_bind().dialect.name)
    counts = db.execute(
        select(
            QueryLog.member_role_at_ask, QueryLog.outcome, listed_query, student_query, bucket,
            func.count(), func.max(QueryLog.created_at),
        )
        .where(*scope)
        .group_by(
            QueryLog.member_role_at_ask, QueryLog.outcome, listed_query, student_query, bucket,
        )
    ).all()
    summary = dict.fromkeys((
        "recorded_attempts", "student_attempts", "cited_answer", "no_evidence", "failure",
        "unknown_outcome", "non_student_attempts", "unknown_role_attempts",
    ), 0)
    frequent_counts: dict[str, int] = defaultdict(int)
    distinct_queries: set[str] = set()
    no_evidence_groups: dict[str, dict] = {}
    trend_counts: dict[datetime, dict[str, int]] = defaultdict(
        lambda: dict.fromkeys(("cited_answer", "no_evidence", "failure", "unknown_outcome"), 0)
    )
    for role, outcome, query, student_query_text, day_value, count, last_at in counts:
        if role == CourseMemberRole.student.value:
            distinct_key = normalize_query(student_query_text or "")
            if distinct_key:
                distinct_queries.add(distinct_key)
        summary["recorded_attempts"] += count
        if role == CourseMemberRole.student.value:
            summary["student_attempts"] += count
            outcome_key = outcome if outcome in QueryOutcome else "unknown_outcome"
            summary[outcome_key] += count
            trend_counts[_bucket_start(day_value)][outcome_key] += count
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
    knowledge = summary["cited_answer"] + summary["no_evidence"]
    summary["knowledge_attempts"] = knowledge
    student_n = summary["student_attempts"]
    summary["distinct_student_questions"] = len(distinct_queries)
    if student_n:
        summary["cited_answer_rate"] = summary["cited_answer"] / student_n
        summary["no_evidence_rate"] = summary["no_evidence"] / student_n
        summary["failure_rate"] = summary["failure"] / student_n
    else:
        summary["cited_answer_rate"] = None
        summary["no_evidence_rate"] = None
        summary["failure_rate"] = None
    summary["rate_denominator"] = "student_attempts"
    summary["sample_limited"] = student_n < SAMPLE_LIMIT_N

    frequent = [{"query": query, "count": count} for query, count in frequent_counts.items()]
    frequent.sort(key=lambda row: (-row["count"], row["query"]))

    no_evidence = [
        {"query": query, "count": group["count"], "last_asked_at": group["last_asked_at"]}
        for query, group in no_evidence_groups.items()
    ]
    no_evidence.sort(key=lambda row: (-row["last_asked_at"].timestamp(), -row["count"], row["query"]))

    themes = []
    for row in no_evidence[:20]:
        themes.append({
            "label": row["query"],
            "source": "exact_normalize",
            "status": "candidate",
            "kind": "no_evidence",
            "ask_count": row["count"],
            "distinct_questions": 1,
            "sort_reason": "no_evidence_repeat",
            "sort_reason_label": "依据不足重复出现（待核对，不等于资料缺失）",
        })
    for row in frequent[:20]:
        if row["count"] < 2:
            continue
        themes.append({
            "label": row["query"],
            "source": "exact_normalize",
            "status": "candidate",
            "kind": "cited_repeat",
            "ask_count": row["count"],
            "distinct_questions": 1,
            "sort_reason": "repeated_question",
            "sort_reason_label": "相同问句重复提问（可能为复习，不代表盲区）",
        })
    themes.sort(key=lambda row: (0 if row["kind"] == "no_evidence" else 1, -row["ask_count"], row["label"]))

    clues = []
    for row in no_evidence[:10]:
        clues.append({
            "title": row["query"],
            "trigger": "no_evidence_repeat",
            "trigger_label": "依据不足次数较高",
            "ask_count": row["count"],
            "status": "pending_review",
        })
    for row in frequent[:10]:
        if row["count"] < 3:
            continue
        clues.append({
            "title": row["query"],
            "trigger": "high_repeat",
            "trigger_label": "高频重复问句",
            "ask_count": row["count"],
            "status": "pending_review",
        })
    if summary["failure"] >= max(3, student_n // 10) and summary["failure"] > 0:
        clues.insert(0, {
            "title": "系统失败偏多",
            "trigger": "system_failure_volume",
            "trigger_label": "系统失败需运维/稳定性核查（不计知识缺口）",
            "ask_count": summary["failure"],
            "status": "pending_ops",
        })

    covered = set(_local_days(window_start, window_end))
    trend = [{"bucket_start": day, **trend_counts[day]} for day in sorted(covered | set(trend_counts))]
    return {
        "window_start": window_start,
        "window_end": window_end,
        "metric_contract": "metrics-v1",
        "summary": summary,
        "trend": trend,
        "frequent": frequent,
        "no_evidence": no_evidence,
        "themes": themes,
        "clues": clues,
    }
