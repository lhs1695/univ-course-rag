from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import (
    InsightsResponse,
    QuestionGroupingRequest,
    QuestionGroupingResponse,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.security.deps import CourseAccess, require_course_teacher
from app.services.embedder import Embedder
from app.services.insights import aggregate_course_insights
from app.services.question_groups import (
    QuestionGroupingDisabled,
    get_question_embedder,
    group_course_questions,
)

router = APIRouter(prefix="/courses", tags=["insights"])


def _window(settings: Settings, start_at: datetime | None, end_at: datetime | None):
    now = datetime.now(UTC)
    retained_since = now - timedelta(days=settings.query_log_retention_days)
    requested_start = start_at.astimezone(UTC) if start_at else retained_since
    requested_end = end_at.astimezone(UTC) if end_at else now
    window_start = max(requested_start, retained_since)
    window_end = min(requested_end, now)
    if window_start >= window_end:
        raise HTTPException(status_code=422, detail="Time window must overlap retained history")
    return window_start, window_end


@router.get("/{course_id}/insights", response_model=InsightsResponse)
def course_insights(
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    start_at: AwareDatetime | None = None,
    end_at: AwareDatetime | None = None,
) -> InsightsResponse:
    window_start, window_end = _window(settings, start_at, end_at)
    payload = aggregate_course_insights(
        db,
        access.course.id,
        window_start=window_start,
        window_end=window_end,
    )
    payload["retention_days"] = settings.query_log_retention_days
    return InsightsResponse.model_validate(payload)


@router.post("/{course_id}/insights/groups", response_model=QuestionGroupingResponse)
def course_question_groups(
    body: QuestionGroupingRequest,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[Embedder | None, Depends(get_question_embedder)],
) -> QuestionGroupingResponse:
    if not body.confirm_external_processing:
        raise HTTPException(status_code=422, detail="Explicit external processing confirmation required")
    window_start, window_end = _window(settings, body.start_at, body.end_at)
    if embedder is None:
        raise QuestionGroupingDisabled()
    return QuestionGroupingResponse.model_validate(group_course_questions(
        db, access.course.id, window_start=window_start, window_end=window_end,
        embedder=embedder, min_similarity=body.min_similarity,
    ))
