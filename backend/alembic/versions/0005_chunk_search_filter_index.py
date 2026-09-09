"""chunk search filter index

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_chunks_course_embedding_model",
        "chunks",
        ["course_id", "embedding_model"],
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_course_embedding_model", table_name="chunks")
