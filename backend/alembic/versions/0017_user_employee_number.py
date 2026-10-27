"""Add an optional unique employee number to users."""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("employee_number", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_users_employee_number", ["employee_number"])


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_employee_number", type_="unique")
        batch.drop_column("employee_number")
