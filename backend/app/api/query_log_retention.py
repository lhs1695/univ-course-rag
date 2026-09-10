import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import QueryLogRetentionRequest, QueryLogRetentionResponse
from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.security.deps import require_admin
from app.services.query_log_retention import maintain_query_logs

router = APIRouter(prefix="/admin/query-logs", tags=["admin-query-logs"])
logger = logging.getLogger(__name__)


@router.post("/retention", response_model=QueryLogRetentionResponse)
def apply_query_log_retention(
    body: QueryLogRetentionRequest,
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _admin: Annotated[User, Depends(require_admin)],
) -> QueryLogRetentionResponse:
    delete_matched = body.mode == "delete"
    result = maintain_query_logs(
        db,
        retention_days=settings.query_log_retention_days,
        batch_size=settings.query_log_cleanup_batch_size,
        delete_matched=delete_matched,
    )
    if delete_matched:
        db.commit()

    logger.info(
        "query_log_retention_maintenance mode=%s count=%d has_more=%s",
        body.mode,
        result.deleted_count if delete_matched else result.matched_count,
        result.has_more,
    )
    return QueryLogRetentionResponse(
        mode=body.mode,
        retention_days=settings.query_log_retention_days,
        batch_limit=settings.query_log_cleanup_batch_size,
        matched_count=result.matched_count,
        deleted_count=result.deleted_count,
        has_more=result.has_more,
        cutoff=result.cutoff,
    )
