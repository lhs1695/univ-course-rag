import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import AgentTaskRetentionRequest, AgentTaskRetentionResponse
from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.security.deps import require_admin
from app.services.agent_task_retention import maintain_agent_tasks

router = APIRouter(prefix="/admin/agent-tasks", tags=["admin-agent-tasks"])
logger = logging.getLogger(__name__)


@router.post("/retention", response_model=AgentTaskRetentionResponse)
def apply_agent_task_retention(
    body: AgentTaskRetentionRequest,
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _admin: Annotated[User, Depends(require_admin)],
) -> AgentTaskRetentionResponse:
    delete_matched = body.mode == "delete"
    result = maintain_agent_tasks(
        db,
        batch_size=settings.query_log_cleanup_batch_size,
        delete_matched=delete_matched,
    )
    if delete_matched:
        db.commit()

    logger.info(
        "agent_task_retention_maintenance mode=%s count=%d has_more=%s",
        body.mode,
        result.deleted_count if delete_matched else result.matched_count,
        result.has_more,
    )
    return AgentTaskRetentionResponse(
        mode=body.mode,
        batch_limit=settings.query_log_cleanup_batch_size,
        matched_count=result.matched_count,
        deleted_count=result.deleted_count,
        has_more=result.has_more,
        cutoff=result.cutoff,
    )
