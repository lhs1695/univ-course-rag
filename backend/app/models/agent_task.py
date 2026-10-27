"""Schema retained; investigation product withdrawn. No task API or runner is exposed."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

_ACTIVE_TASK_PREDICATE = text("status IN ('queued', 'running', 'cancel_requested')")


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "created_by",
            "idempotency_key_hash",
            name="uq_agent_tasks_course_creator_idempotency",
        ),
        Index("ix_agent_tasks_course_created_at", "course_id", "created_at"),
        Index("ix_agent_tasks_course_status_created_at", "course_id", "status", "created_at"),
        Index("ix_agent_tasks_status_lease_expires_at", "status", "lease_expires_at"),
        Index("ix_agent_tasks_expires_at", "expires_at"),
        Index(
            "uq_agent_tasks_active_course",
            "course_id",
            unique=True,
            sqlite_where=_ACTIVE_TASK_PREDICATE,
            postgresql_where=_ACTIVE_TASK_PREDICATE,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    task_type: Mapped[str] = mapped_column(String(64))
    focus: Mapped[str] = mapped_column(String(32))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirm_external_processing: Mapped[bool] = mapped_column(Boolean)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    attempt: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    budget_json: Mapped[dict] = mapped_column(JSON)
    budget_used_json: Mapped[dict] = mapped_column(JSON)
    checkpoint_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_token: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_event_sequence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentTaskEvent(Base):
    __tablename__ = "agent_task_events"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt: Mapped[int] = mapped_column(Integer)
    step_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(48))
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    safe_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs_json: Mapped[list | dict] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
