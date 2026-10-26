"""PLAN-17 semesters, course classes, profile and opt-in retrieval.

Existing document states are preserved. No roster or demo data is modified.
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "semesters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.CheckConstraint("ends_on >= starts_on", name="ck_semester_dates"),
    )
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("full_name", sa.String(100), nullable=True))
        batch.add_column(sa.Column("student_number", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_users_student_number", ["student_number"])
    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("semester_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_courses_semester", "semesters", ["semester_id"], ["id"]
        )
    op.create_table(
        "course_classes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Uuid(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("course_id", "name", name="uq_course_classes_course_name"),
        sa.UniqueConstraint("id", "course_id", name="uq_course_classes_id_course"),
    )
    op.create_index("ix_course_classes_course_id", "course_classes", ["course_id"])
    with op.batch_alter_table("course_members") as batch:
        batch.add_column(sa.Column("class_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_course_members_class_id", ["class_id"])
        batch.create_foreign_key(
            "fk_course_members_class_course",
            "course_classes",
            ["class_id", "course_id"],
            ["id", "course_id"],
            ondelete="NO ACTION",
        )
        batch.create_check_constraint(
            "ck_class_student_only", "class_id IS NULL OR role = 'student'"
        )
    with op.batch_alter_table("documents") as batch:
        batch.alter_column(
            "retrieval_enabled",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.false(),
        )


def downgrade():
    with op.batch_alter_table("documents") as batch:
        batch.alter_column(
            "retrieval_enabled",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.true(),
        )
    with op.batch_alter_table("course_members") as batch:
        batch.drop_constraint("ck_class_student_only", type_="check")
        batch.drop_constraint("fk_course_members_class_course", type_="foreignkey")
        batch.drop_index("ix_course_members_class_id")
        batch.drop_column("class_id")
    op.drop_index("ix_course_classes_course_id", table_name="course_classes")
    op.drop_table("course_classes")
    with op.batch_alter_table("courses") as batch:
        batch.drop_constraint("fk_courses_semester", type_="foreignkey")
        batch.drop_column("semester_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_student_number", type_="unique")
        batch.drop_column("student_number")
        batch.drop_column("full_name")
    op.drop_table("semesters")
