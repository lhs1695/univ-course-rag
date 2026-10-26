from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.agent.contracts import AgentBudget, InvestigationRequest, TaskStatus
from app.config import Settings, get_settings
from app.db import get_db
from app.models.agent_task import AgentTask
from app.security.deps import CourseAccess, require_course_teacher
from app.services.agent_task_store import (
    AgentTaskConflict,
    InvalidInvestigationWindow,
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
    # M1 only queues persisted state: confirmation=False is valid, with no dispatch.
    try:
        row = create_task(db, body, course_id=access.course.id, created_by=access.user.id,
                          retention_days=settings.query_log_retention_days)
    except AgentTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except InvalidInvestigationWindow as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _out(row)


@router.get("/{task_id}", response_model=AgentTaskOut)
def read_investigation_task(
    task_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> AgentTaskOut:
    row = get_task(db, task_id, course_id=access.course.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _out(row)
