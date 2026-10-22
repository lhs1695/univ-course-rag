
from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import InsightReviewCreate, InsightReviewOut, InsightReviewUpdate
from app.db import get_db
from app.models.insight_review import InsightReview
from app.security.deps import CourseAccess, require_course_teacher

router = APIRouter(prefix="/courses/{course_id}/insight-reviews", tags=["insight-reviews"])


def _out(row: InsightReview) -> InsightReviewOut:
    return InsightReviewOut(
        id=str(row.id),
        course_id=str(row.course_id),
        teacher_id=str(row.teacher_id),
        subject_type=row.subject_type,
        subject_key=row.subject_key,
        intent_code=row.intent_code,
        knowledge_point=row.knowledge_point,
        review_status=row.review_status,
        cause_code=row.cause_code,
        action_code=row.action_code,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[InsightReviewOut])
def list_reviews(
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[InsightReviewOut]:
    rows = db.scalars(
        select(InsightReview)
        .where(InsightReview.course_id == access.course.id)
        .order_by(InsightReview.updated_at.desc())
    ).all()
    return [_out(row) for row in rows]


@router.post("", response_model=InsightReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    body: InsightReviewCreate,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> InsightReviewOut:
    row = InsightReview(
        id=uuid4(),
        course_id=access.course.id,
        teacher_id=access.user.id,
        subject_type=body.subject_type,
        subject_key=body.subject_key.strip(),
        intent_code=body.intent_code,
        knowledge_point=(body.knowledge_point or None),
        review_status=body.review_status,
        cause_code=body.cause_code,
        action_code=body.action_code,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/{review_id}", response_model=InsightReviewOut)
def update_review(
    review_id: UUID,
    body: InsightReviewUpdate,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> InsightReviewOut:
    row = db.get(InsightReview, review_id)
    if row is None or row.course_id != access.course.id:
        raise HTTPException(status_code=404, detail="Review not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _out(row)
