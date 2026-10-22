
"""insight_reviews for teacher action loop

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insight_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_key", sa.String(length=512), nullable=False),
        sa.Column("intent_code", sa.String(length=32), nullable=True),
        sa.Column("knowledge_point", sa.String(length=256), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="deferred"),
        sa.Column("cause_code", sa.String(length=32), nullable=True),
        sa.Column("action_code", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_insight_reviews_course_id", "insight_reviews", ["course_id"])
    op.create_index("ix_insight_reviews_teacher_id", "insight_reviews", ["teacher_id"])


def downgrade() -> None:
    op.drop_index("ix_insight_reviews_teacher_id", table_name="insight_reviews")
    op.drop_index("ix_insight_reviews_course_id", table_name="insight_reviews")
    op.drop_table("insight_reviews")
