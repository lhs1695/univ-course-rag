"""Task persistence; no provider calls or automatic dispatch."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.agent.contracts import AgentBudget, InvestigationRequest, TaskStatus
from app.models.agent_task import AgentTask, AgentTaskEvent

ACTIVE_STATUSES = ("queued", "running", "cancel_requested")
TASK_TYPE = "course_question_investigation"
_DATETIME_FIELDS = (
    "window_start", "window_end", "created_at", "updated_at", "started_at",
    "finished_at", "expires_at", "cancel_requested_at", "lease_expires_at",
)


class AgentTaskConflict(ValueError):
    """Stable public conflict code; never expose database exception details."""


class InvalidInvestigationWindow(ValueError):
    """Request window lies outside currently retained logs."""


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _normalize(row: AgentTask) -> AgentTask:
    for name in _DATETIME_FIELDS:
        value = getattr(row, name)
        if value is not None:
            # SQLite drops tzinfo. Mark the loaded value without scheduling an UPDATE.
            set_committed_value(row, name, _utc(value))
    return row


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _existing(db: Session, course_id: UUID, created_by: UUID, key_hash: str) -> AgentTask | None:
    return db.scalar(select(AgentTask).where(
        AgentTask.course_id == course_id,
        AgentTask.created_by == created_by,
        AgentTask.idempotency_key_hash == key_hash,
    ))


def _reuse(row: AgentTask, fingerprint: str) -> AgentTask:
    if row.request_fingerprint != fingerprint:
        raise AgentTaskConflict("idempotency_conflict")
    return _normalize(row)


def create_task(
    db: Session,
    request: InvestigationRequest,
    *,
    course_id: UUID,
    created_by: UUID,
    retention_days: int = 90,
    now: datetime | None = None,
) -> AgentTask:
    """Commit a queued task and its creation event atomically, or reuse its key.

    Caller supplies the configured retention; no Settings/.env loading here.
    Database uniqueness, including the partial active-course index, fences races.
    """
    current = _utc(now or datetime.now(UTC))
    start, end = _utc(request.start_at), _utc(request.end_at)
    key_hash = _digest(request.idempotency_key)
    fingerprint = _digest(json.dumps({
        "course_id": str(course_id), "user_id": str(created_by), "task_type": TASK_TYPE,
        "focus": request.focus.value, "start_at": start.isoformat(), "end_at": end.isoformat(),
        "confirm_external_processing": request.confirm_external_processing,
    }, sort_keys=True, separators=(",", ":")))
    existing = _existing(db, course_id, created_by, key_hash)
    if existing is not None:
        return _reuse(existing, fingerprint)
    if retention_days < 1 or start < current - timedelta(days=retention_days) or end > current:
        raise InvalidInvestigationWindow("investigation_window_outside_retention")
    if db.scalar(select(AgentTask.id).where(
        AgentTask.course_id == course_id, AgentTask.status.in_(ACTIVE_STATUSES),
    )) is not None:
        raise AgentTaskConflict("active_investigation_conflict")

    row = AgentTask(
        id=uuid4(), course_id=course_id, created_by=created_by, task_type=TASK_TYPE,
        focus=request.focus.value, window_start=start, window_end=end,
        confirm_external_processing=request.confirm_external_processing,
        idempotency_key_hash=key_hash, request_fingerprint=fingerprint,
        status=TaskStatus.queued.value, attempt=1,
        budget_json=AgentBudget().model_dump(mode="json"),
        budget_used_json={"steps": 0, "tool_calls": 0, "model_calls": 0,
                          "runtime_seconds": 0, "evidence_refs": 0, "report_chars": 0},
        last_event_sequence=1, created_at=current, updated_at=current,
        expires_at=current + timedelta(days=retention_days),
    )
    try:
        db.add(row)
        db.flush()
        db.add(AgentTaskEvent(
            task_id=row.id, sequence=1, attempt=1, event_type="task_created",
            status=TaskStatus.queued.value, safe_summary="Investigation task queued",
            evidence_refs_json=[], created_at=current,
        ))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = _existing(db, course_id, created_by, key_hash)
        if existing is not None:
            return _reuse(existing, fingerprint)
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        active_collision = constraint == "uq_agent_tasks_active_course" or (
            str(exc.orig) == "UNIQUE constraint failed: agent_tasks.course_id"
        )
        if active_collision:
            raise AgentTaskConflict("active_investigation_conflict") from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(row)
    return _normalize(row)


def get_task(
    db: Session, task_id: UUID, *, course_id: UUID | None = None, now: datetime | None = None,
) -> AgentTask | None:
    """Read persisted state, optionally course-scoped; expired tasks are unavailable."""
    query = select(AgentTask).where(AgentTask.id == task_id)
    if course_id is not None:
        query = query.where(AgentTask.course_id == course_id)
    row = db.scalar(query)
    if row is None:
        return None
    row = _normalize(row)
    return row if row.expires_at > _utc(now or datetime.now(UTC)) else None
