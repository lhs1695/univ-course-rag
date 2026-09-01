from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import InsightsResponse
from app.db import get_db
from app.security.deps import CourseAccess, require_course_teacher
from app.services.insights import aggregate_course_insights

router = APIRouter(prefix="/courses", tags=["insights"])


@router.get("/{course_id}/insights", response_model=InsightsResponse)
def course_insights(
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> InsightsResponse:
    payload = aggregate_course_insights(db, access.course.id)
    return InsightsResponse.model_validate(payload)
