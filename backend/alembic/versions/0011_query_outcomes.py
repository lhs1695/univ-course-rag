"""Record final ask outcome and course role at the time of asking.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Historical role and a cited answer cannot be inferred from hit/error_code.
    op.add_column("query_logs", sa.Column("outcome", sa.String(24), nullable=True))
    op.add_column("query_logs", sa.Column("member_role_at_ask", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("query_logs", "member_role_at_ask")
    op.drop_column("query_logs", "outcome")
