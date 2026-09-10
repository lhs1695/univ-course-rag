from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.models.query_log import QueryLog


@dataclass(frozen=True)
class QueryLogCleanupResult:
    cutoff: datetime
    matched_count: int
    deleted_count: int
    has_more: bool


def maintain_query_logs(
    db: DbSession,
    *,
    retention_days: int,
    batch_size: int,
    delete_matched: bool,
    now: datetime | None = None,
) -> QueryLogCleanupResult:
    """Inspect or delete one oldest-first, bounded batch of expired query logs."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    candidate_ids = db.execute(
        select(QueryLog.id)
        .where(QueryLog.created_at < cutoff)
        .order_by(QueryLog.created_at, QueryLog.id)
        .limit(batch_size + 1)
    ).scalars().all()
    has_more = len(candidate_ids) > batch_size
    matched_ids = candidate_ids[:batch_size]

    deleted_count = 0
    if delete_matched and matched_ids:
        rowcount = db.execute(delete(QueryLog).where(QueryLog.id.in_(matched_ids))).rowcount
        deleted_count = int(rowcount or 0)

    return QueryLogCleanupResult(
        cutoff=cutoff,
        matched_count=len(matched_ids),
        deleted_count=deleted_count,
        has_more=has_more,
    )
