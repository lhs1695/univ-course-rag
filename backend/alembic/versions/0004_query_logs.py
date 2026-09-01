"""query_logs

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "query_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("hit", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("chunk_ids", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_logs_course_id", "query_logs", ["course_id"])
    op.create_index("ix_query_logs_user_id", "query_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_query_logs_user_id", table_name="query_logs")
    op.drop_index("ix_query_logs_course_id", table_name="query_logs")
    op.drop_table("query_logs")
