"""Persist agent tasks and append-only task events.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_TASK_PREDICATE = sa.text("status IN ('queued', 'running', 'cancel_requested')")


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("focus", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirm_external_processing", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="1", nullable=False),
        sa.Column("budget_json", sa.JSON(), nullable=False),
        sa.Column("budget_used_json", sa.JSON(), nullable=False),
        sa.Column("checkpoint_json", sa.JSON(), nullable=True),
        sa.Column("report_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_token", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_sequence", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id",
            "created_by",
            "idempotency_key_hash",
            name="uq_agent_tasks_course_creator_idempotency",
        ),
    )
    op.create_index(
        "ix_agent_tasks_course_created_at", "agent_tasks", ["course_id", "created_at"]
    )
    op.create_index(
        "ix_agent_tasks_course_status_created_at",
        "agent_tasks",
        ["course_id", "status", "created_at"],
    )
    op.create_index(
        "ix_agent_tasks_status_lease_expires_at",
        "agent_tasks",
        ["status", "lease_expires_at"],
    )
    op.create_index("ix_agent_tasks_expires_at", "agent_tasks", ["expires_at"])
    op.create_index(
        "uq_agent_tasks_active_course",
        "agent_tasks",
        ["course_id"],
        unique=True,
        sqlite_where=_ACTIVE_TASK_PREDICATE,
        postgresql_where=_ACTIVE_TASK_PREDICATE,
    )

    op.create_table(
        "agent_task_events",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safe_summary", sa.Text(), nullable=True),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "sequence"),
    )


def downgrade() -> None:
    op.drop_table("agent_task_events")
    op.drop_index("uq_agent_tasks_active_course", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_expires_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_status_lease_expires_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_course_status_created_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_course_created_at", table_name="agent_tasks")
    op.drop_table("agent_tasks")
