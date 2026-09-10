"""add document quality metadata

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source_unit_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("extracted_char_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("quality_warning", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "quality_warning")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "extracted_char_count")
    op.drop_column("documents", "source_unit_count")
