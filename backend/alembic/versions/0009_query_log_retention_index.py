"""query log retention index

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_query_logs_created_at_id",
        "query_logs",
        ["created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_query_logs_created_at_id", table_name="query_logs")
