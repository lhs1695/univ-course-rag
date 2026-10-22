
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ReviewStatus(StrEnum):
    confirmed = "confirmed"
    rejected = "rejected"
    deferred = "deferred"
    split = "split"


class InsightReview(Base):
    __tablename__ = "insight_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    subject_type: Mapped[str] = mapped_column(String(32))
    subject_key: Mapped[str] = mapped_column(String(512))
    intent_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    knowledge_point: Mapped[str | None] = mapped_column(String(256), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default=ReviewStatus.deferred.value)
    cause_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
