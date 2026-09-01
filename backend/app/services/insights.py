from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session as DbSession

from app.models.course import CourseMember, CourseMemberRole
from app.models.query_log import QueryLog
from app.services.generate import NO_EVIDENCE

NORMALIZE_MAX_CHARS = 200


def normalize_query(text: str) -> str:
    collapsed = " ".join((text or "").split())
    return collapsed[:NORMALIZE_MAX_CHARS]


def _last_asked_at(logs: list[QueryLog]) -> datetime:
    return max(log.created_at for log in logs)


def aggregate_course_insights(db: DbSession, course_id: UUID) -> dict:
    logs = db.execute(
        select(QueryLog)
        .join(
            CourseMember,
            and_(
                CourseMember.course_id == QueryLog.course_id,
                CourseMember.user_id == QueryLog.user_id,
            ),
        )
        .where(
            QueryLog.course_id == course_id,
            CourseMember.role == CourseMemberRole.student.value,
        )
    ).scalars().all()

    frequent_groups: dict[str, list[QueryLog]] = defaultdict(list)
    no_evidence_groups: dict[str, list[QueryLog]] = defaultdict(list)
    for log in logs:
        key = normalize_query(log.query)
        if not key:
            continue
        if log.hit:
            frequent_groups[key].append(log)
        if log.error_code == NO_EVIDENCE:
            no_evidence_groups[key].append(log)

    frequent = [
        {
            "query": query,
            "count": len(group),
        }
        for query, group in frequent_groups.items()
    ]
    frequent.sort(key=lambda row: (-row["count"], row["query"]))

    no_evidence = [
        {
            "query": query,
            "count": len(group),
            "last_asked_at": _last_asked_at(group),
        }
        for query, group in no_evidence_groups.items()
    ]
    no_evidence.sort(key=lambda row: (-row["last_asked_at"].timestamp(), -row["count"], row["query"]))
    return {"frequent": frequent, "no_evidence": no_evidence}
