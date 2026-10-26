from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.models.agent_task import AgentTask


@dataclass(frozen=True)
class AgentTaskCleanupResult:
    cutoff: datetime
    matched_count: int
    deleted_count: int
    has_more: bool


def maintain_agent_tasks(
    db: DbSession,
    *,
    batch_size: int,
    delete_matched: bool,
    now: datetime | None = None,
) -> AgentTaskCleanupResult:
    """Inspect or physically delete one bounded batch; cutoff is the current UTC time.

    Only expires_at <= cutoff matters, including for running tasks. The database
    cascades task deletion to events; the caller owns the transaction.
    Physical TTL cleanup is distinct from the existing source validity gate:
    invalid sources must already be blocked on read/resolution, before cleanup.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    current = now or datetime.now(UTC)
    if current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    cutoff = current.astimezone(UTC)
    candidate_ids = db.execute(
        select(AgentTask.id)
        .where(AgentTask.expires_at <= cutoff)
        .order_by(AgentTask.expires_at, AgentTask.id)
        .limit(batch_size + 1)
    ).scalars().all()
    matched_ids = candidate_ids[:batch_size]
    deleted_count = 0
    if delete_matched and matched_ids:
        deleted_count = int(db.execute(
            delete(AgentTask).where(
                AgentTask.id.in_(matched_ids), AgentTask.expires_at <= cutoff,
            ).execution_options(synchronize_session="fetch")
        ).rowcount or 0)

    return AgentTaskCleanupResult(
        cutoff=cutoff,
        matched_count=len(matched_ids),
        deleted_count=deleted_count,
        has_more=len(candidate_ids) > batch_size,
    )
