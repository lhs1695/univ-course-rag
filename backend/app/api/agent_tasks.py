from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.agent.contracts import AgentBudget, InvestigationRequest, TaskStatus
from app.config import Settings, get_settings
from app.db import get_db
from app.models.agent_task import AgentTask, AgentTaskEvent
from app.security.deps import CourseAccess, require_course_teacher
from app.services.agent_investigation import (
    InvestigationReportOut,
    checkpoint_is_safe,
    external_processing_required,
    read_report,
    run_investigation,
)
from app.services.agent_task_runtime import cancel_task, interrupt_stale, restart_task
from app.services.agent_task_store import (
    AgentTaskConflict,
    InvalidInvestigationWindow,
    _normalize,
    create_task,
    get_task,
)

router = APIRouter(prefix="/courses/{course_id}/agent-tasks", tags=["agent-tasks"])


class AgentBudgetUsedOut(BaseModel):
    steps: int
    tool_calls: int
    model_calls: int
    runtime_seconds: float
    evidence_refs: int
    report_chars: int


class AgentTaskOut(BaseModel):
    task_id: UUID
    course_id: UUID
    status: TaskStatus
    attempt: int
    budget_limits: AgentBudget
    budget_used: AgentBudgetUsedOut
    error_code: str | None
    created_at: datetime
    expires_at: datetime


def _out(row: AgentTask) -> AgentTaskOut:
    _normalize(row)
    return AgentTaskOut(
        task_id=row.id, course_id=row.course_id, status=row.status, attempt=row.attempt,
        budget_limits=row.budget_json, budget_used=row.budget_used_json,
        error_code=row.error_code, created_at=row.created_at, expires_at=row.expires_at,
    )


@router.post("", response_model=AgentTaskOut, status_code=status.HTTP_201_CREATED)
def create_investigation_task(
    body: InvestigationRequest,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentTaskOut:
    if external_processing_required(settings) and not body.confirm_external_processing:
        raise HTTPException(status_code=422, detail="external_processing_confirmation_required")
    try:
        row = create_task(db, body, course_id=access.course.id, created_by=access.user.id,
                          retention_days=settings.query_log_retention_days)
    except AgentTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except InvalidInvestigationWindow as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _out(row)


class RunRequest(BaseModel):
    mode: Literal["fake", "replay"] = "fake"


@router.post("/{task_id}/run", response_model=AgentTaskOut)
def run_fake_investigation_task(
    task_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    body: RunRequest | None = None,
) -> AgentTaskOut:
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if external_processing_required(settings) and not row.confirm_external_processing:
        raise HTTPException(status_code=422, detail="external_processing_confirmation_required")
    if row.status != TaskStatus.queued:
        raise HTTPException(status_code=409, detail="investigation_not_queued")
    if not run_investigation(db, row, course_title=access.course.title,
                             retention_days=settings.query_log_retention_days,
                             actor_id=access.user.id,
                             mode=body.mode if body else "fake") and row.status != "budget_exceeded":
        raise HTTPException(status_code=409, detail="investigation_not_queued")
    return _out(row)


@router.get("/{task_id}/report", response_model=InvestigationReportOut)
def read_investigation_report(
    task_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InvestigationReportOut:
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    interrupt_stale(db, row)
    return read_report(db, row, retention_days=settings.query_log_retention_days)


@router.get("/{task_id}", response_model=AgentTaskOut)
def read_investigation_task(
    task_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> AgentTaskOut:
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    interrupt_stale(db, row)
    return _out(row)


class RestartRequest(BaseModel):
    confirm_external_processing: bool


def _safe_evidence_refs(raw: object) -> list[dict]:
    """Project reference metadata only; never forward arbitrary JSON text."""
    id_keys = {"id", "evidence_id", "query_log_id", "chunk_id", "document_id", "course_id"}
    page_keys = {"page", "page_no", "page_number", "start_page", "end_page"}
    refs = raw if isinstance(raw, list) else [raw]
    safe = []
    for ref in refs:
        if isinstance(ref, str):
            ref = {"evidence_id": ref}
        if not isinstance(ref, dict):
            continue
        item = {}
        for key, value in ref.items():
            if key in id_keys and isinstance(value, str):
                try:
                    item[key] = str(UUID(value))
                except ValueError:
                    pass
            elif key in page_keys and type(value) is int and value > 0:
                item[key] = value
        if item:
            safe.append(item)
    return safe


@router.get("/{task_id}/events")
def read_investigation_events(
    task_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[dict]:
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    interrupt_stale(db, row)
    return [{"sequence": e.sequence, "attempt": e.attempt, "step_no": e.step_no,
             "event_type": e.event_type, "tool_name": e.tool_name,
             "status": e.status, "safe_summary": e.safe_summary, "error_code": e.error_code,
             "duration_ms": e.duration_ms,
             "created_at": e.created_at.replace(tzinfo=UTC) if e.created_at.tzinfo is None
             else e.created_at,
             "evidence_refs": _safe_evidence_refs(e.evidence_refs_json)}
            for e in db.scalars(select(AgentTaskEvent).where(
                AgentTaskEvent.task_id == row.id,
            ).order_by(AgentTaskEvent.sequence)).all()]


@router.post("/{task_id}/cancel", response_model=AgentTaskOut)
def cancel_investigation_task(
    task_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> AgentTaskOut:
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    cancel_task(db, row)
    interrupt_stale(db, row)
    return _out(row)


def _restart(task_id, body, access, db, settings, operation):
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not body.confirm_external_processing:
        raise HTTPException(status_code=422, detail="external_processing_confirmation_required")
    interrupt_stale(db, row)
    checkpoint = row.checkpoint_json or {}
    try:
        restart_task(db, row, operation=operation, checkpoint_safe=checkpoint_is_safe(
            db, row, retention_days=settings.query_log_retention_days,
        ), checkpoint_error=("source_unavailable" if checkpoint.get("version") == 1
                             and checkpoint.get("safe_boundary") is True
                             else "investigation_checkpoint_unsafe"))
    except AgentTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _out(row)


@router.post("/{task_id}/resume", response_model=AgentTaskOut)
def resume_investigation_task(
    task_id: UUID, body: RestartRequest,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentTaskOut:
    return _restart(task_id, body, access, db, settings, "resume")


@router.post("/{task_id}/retry", response_model=AgentTaskOut)
def retry_investigation_task(
    task_id: UUID, body: RestartRequest,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentTaskOut:
    return _restart(task_id, body, access, db, settings, "retry")
