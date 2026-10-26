"""0015 is executed only on an explicit in-memory SQLite connection."""

import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


def scripts():
    return ScriptDirectory(str(Path(__file__).parents[1] / "alembic"))


def test_0015_isolated_sqlite_upgrade_downgrade_preserves_old_rows():
    migrations = scripts()
    revision = migrations.get_revision("0015")
    assert revision.down_revision == "0014"
    engine = sa.create_engine("sqlite://")
    # SQLite batch recreation requires foreign keys OFF during DDL. They are
    # switched ON again before testing constraints / foreign_key_check.
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migrations.get_revision("0001").module.upgrade()
            migrations.get_revision("0002").module.upgrade()
        conn.exec_driver_sql(
            "CREATE TABLE documents (id CHAR(32) PRIMARY KEY, course_id CHAR(32) REFERENCES courses(id), retrieval_enabled BOOLEAN NOT NULL DEFAULT 1)"
        )
        conn.exec_driver_sql(
            "INSERT INTO users (id, username, password_hash, role) VALUES ('u', 'old', 'hash', 'student')"
        )
        conn.exec_driver_sql(
            "INSERT INTO courses (id, title) VALUES ('c', 'old course'), ('other', 'other course')"
        )
        conn.exec_driver_sql(
            "INSERT INTO course_members (id, course_id, user_id, role) VALUES ('m', 'c', 'u', 'student')"
        )
        conn.exec_driver_sql(
            "INSERT INTO documents (id, course_id) VALUES ('old-doc', 'c')"
        )
        with Operations.context(MigrationContext.configure(conn)):
            revision.module.upgrade()
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.commit()
        with conn.begin():
            assert conn.exec_driver_sql(
                "SELECT full_name, student_number FROM users"
            ).one() == (None, None)
            assert (
                conn.exec_driver_sql(
                    "SELECT semester_id FROM courses WHERE id='c'"
                ).scalar_one()
                is None
            )
            assert (
                conn.exec_driver_sql(
                    "SELECT retrieval_enabled FROM documents WHERE id='old-doc'"
                ).scalar_one()
                == 1
            )
            conn.exec_driver_sql(
                "INSERT INTO documents (id, course_id) VALUES ('new-doc', 'c')"
            )
            assert (
                conn.exec_driver_sql(
                    "SELECT retrieval_enabled FROM documents WHERE id='new-doc'"
                ).scalar_one()
                == 0
            )
            conn.exec_driver_sql(
                "INSERT INTO course_classes (id, course_id, name) VALUES ('k', 'c', '一班')"
            )
            conn.exec_driver_sql("UPDATE course_members SET class_id='k' WHERE id='m'")
            assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql(
                    "UPDATE course_members SET course_id='other' WHERE id='m'"
                )
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql(
                    "UPDATE course_members SET role='teacher' WHERE id='m'"
                )
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql(
                    "INSERT INTO semesters (id, name, starts_on, ends_on) VALUES ('s', 'bad', '2026-10-02', '2026-10-01')"
                )
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.commit()
        with conn.begin(), Operations.context(MigrationContext.configure(conn)):
            revision.module.downgrade()
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
        assert conn.exec_driver_sql("SELECT username FROM users").scalar_one() == "old"
        assert (
            conn.exec_driver_sql("SELECT user_id FROM course_members").scalar_one()
            == "u"
        )
        assert (
            conn.exec_driver_sql(
                "SELECT retrieval_enabled FROM documents WHERE id='new-doc'"
            ).scalar_one()
            == 0
        )
        conn.exec_driver_sql(
            "INSERT INTO documents (id, course_id) VALUES ('after-down', 'c')"
        )
        assert (
            conn.exec_driver_sql(
                "SELECT retrieval_enabled FROM documents WHERE id='after-down'"
            ).scalar_one()
            == 1
        )
        assert "semesters" not in sa.inspect(conn).get_table_names()
        assert "class_id" not in {
            c["name"] for c in sa.inspect(conn).get_columns("course_members")
        }
    engine.dispose()


def test_0015_postgresql_offline_ddl_only():
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        scripts().get_revision("0015").module.upgrade()
        scripts().get_revision("0015").module.downgrade()
    sql = output.getvalue()
    assert "CREATE TABLE semesters" in sql and "CREATE TABLE course_classes" in sql
    assert (
        "FOREIGN KEY(class_id, course_id) REFERENCES course_classes (id, course_id)"
        in sql
    )
    assert "ALTER COLUMN retrieval_enabled SET DEFAULT false" in sql
    assert "UPDATE documents" not in sql
