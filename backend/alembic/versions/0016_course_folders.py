"""Shallow course folders and optional document organization metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "course_folders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("course_folders.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_course_folders_course_id", "course_folders", ["course_id"])
    op.create_index("ix_course_folders_parent_id", "course_folders", ["parent_id"])
    for kind, columns, predicate in (
        ("root", ["course_id", "name"], "parent_id IS NULL"),
        ("child", ["course_id", "parent_id", "name"], "parent_id IS NOT NULL"),
    ):
        op.create_index(
            f"uq_course_folders_{kind}_name", "course_folders", columns, unique=True,
            sqlite_where=sa.text(predicate), postgresql_where=sa.text(predicate),
        )
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("folder_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_documents_folder", "course_folders", ["folder_id"], ["id"], ondelete="SET NULL",
        )
        batch.create_index("ix_documents_folder_id", ["folder_id"])


def downgrade():
    with op.batch_alter_table("documents") as batch:
        batch.drop_index("ix_documents_folder_id")
        batch.drop_constraint("fk_documents_folder", type_="foreignkey")
        batch.drop_column("folder_id")
    op.drop_table("course_folders")
