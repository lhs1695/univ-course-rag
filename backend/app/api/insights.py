from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import InsightsResponse
from app.config import Settings, get_settings
from app.db import get_db
from app.security.deps import CourseAccess, require_course_teacher
from app.services.insights import aggregate_course_insights

router = APIRouter(prefix="/courses", tags=["insights"])


@router.get("/{course_id}/insights", response_model=InsightsResponse)
def course_insights(
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InsightsResponse:
    retained_since = datetime.now(UTC) - timedelta(days=settings.query_log_retention_days)
    payload = aggregate_course_insights(
        db,
        access.course.id,
        retained_since=retained_since,
    )
    payload["retention_days"] = settings.query_log_retention_days
    return InsightsResponse.model_validate(payload)
