"""Add optional demo college affiliations to users and courses."""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "colleges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("code", name="uq_colleges_code"),
    )
    for table in ("users", "courses"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("college_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_college", "colleges", ["college_id"], ["id"],
                ondelete="RESTRICT",
            )


def downgrade():
    for table in ("courses", "users"):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"fk_{table}_college", type_="foreignkey")
            batch.drop_column("college_id")
    op.drop_table("colleges")
