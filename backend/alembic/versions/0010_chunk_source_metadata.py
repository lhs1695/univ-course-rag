"""add nullable chunk provenance and document chunking version

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No backfill: historical text was produced by another parser/splitter.
    op.add_column("documents", sa.Column("chunking_version", sa.String(96), nullable=True))
    op.add_column("chunks", sa.Column("source_metadata", sa.JSON(none_as_null=True), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "source_metadata")
    op.drop_column("documents", "chunking_version")
