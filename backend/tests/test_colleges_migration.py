"""0018 runs only against isolated SQLite or PostgreSQL offline DDL."""

import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


def migration():
    scripts = ScriptDirectory(str(Path(__file__).parents[1] / "alembic"))
    revision = scripts.get_revision("0018")
    assert revision.down_revision == "0017"
    return revision.module


def test_0018_sqlite_roundtrip_preserves_rows_constraints_and_references():
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            metadata = sa.MetaData()
            sa.Table(
                "users", metadata,
                sa.Column("id", sa.Uuid(), primary_key=True),
                sa.Column("username", sa.String(64), nullable=False, unique=True, index=True),
                sa.Column("employee_number", sa.String(64), unique=True),
            )
            sa.Table(
                "courses", metadata,
                sa.Column("id", sa.Uuid(), primary_key=True),
                sa.Column("title", sa.String(200), nullable=False),
            )
            sa.Table(
                "course_members", metadata,
                sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id")),
                sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id")),
            )
            metadata.create_all(conn)
            conn.exec_driver_sql("INSERT INTO users VALUES ('u', 'old', 'EMP')")
            conn.exec_driver_sql("INSERT INTO courses VALUES ('c', 'old course')")
            conn.exec_driver_sql("INSERT INTO course_members VALUES ('u', 'c')")
            with Operations.context(MigrationContext.configure(conn)):
                migration().upgrade()
            for table in ("users", "courses"):
                assert next(c for c in sa.inspect(conn).get_columns(table) if c["name"] == "college_id")["nullable"]
                assert conn.exec_driver_sql(f"SELECT college_id FROM {table}").scalar_one() is None
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            conn.commit()
            with conn.begin():
                conn.exec_driver_sql("INSERT INTO colleges VALUES ('college', 'CS', '计算机学院')")
                with conn.begin_nested(), pytest.raises(IntegrityError):
                    conn.exec_driver_sql("INSERT INTO colleges VALUES ('duplicate', 'CS', '重复')")
                for table in ("users", "courses"):
                    with conn.begin_nested(), pytest.raises(IntegrityError):
                        conn.exec_driver_sql(f"UPDATE {table} SET college_id='missing'")
                    conn.exec_driver_sql(f"UPDATE {table} SET college_id='college'")
                    with conn.begin_nested(), pytest.raises(IntegrityError):
                        conn.exec_driver_sql("DELETE FROM colleges WHERE id='college'")
                    conn.exec_driver_sql(f"UPDATE {table} SET college_id=NULL")
                assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
                # Downgrade must preserve old rows even while affiliations are mounted.
                conn.exec_driver_sql("UPDATE users SET college_id='college'")
                conn.exec_driver_sql("UPDATE courses SET college_id='college'")
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conn.commit()
            with conn.begin(), Operations.context(MigrationContext.configure(conn)):
                migration().downgrade()
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            assert "colleges" not in sa.inspect(conn).get_table_names()
            for table in ("users", "courses"):
                assert "college_id" not in {c["name"] for c in sa.inspect(conn).get_columns(table)}
            assert conn.exec_driver_sql("SELECT username, employee_number FROM users").one() == ("old", "EMP")
            assert conn.exec_driver_sql("SELECT title FROM courses").scalar_one() == "old course"
            assert conn.exec_driver_sql("SELECT user_id, course_id FROM course_members").one() == ("u", "c")
            assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
            assert "ix_users_username" in {i["name"] for i in sa.inspect(conn).get_indexes("users")}
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql("INSERT INTO users VALUES ('u2', 'other', 'EMP')")
    finally:
        engine.dispose()


def test_0018_postgresql_offline_upgrade_downgrade_ddl():
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output},
    )
    with Operations.context(context):
        migration().upgrade()
        migration().downgrade()
    sql = output.getvalue()
    assert "CREATE TABLE colleges" in sql and "CONSTRAINT uq_colleges_code UNIQUE (code)" in sql
    for table in ("users", "courses"):
        assert f"ALTER TABLE {table} ADD COLUMN college_id UUID" in sql
        assert f"CONSTRAINT fk_{table}_college FOREIGN KEY(college_id) REFERENCES colleges (id) ON DELETE RESTRICT" in sql
        assert f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_college" in sql
        assert f"ALTER TABLE {table} DROP COLUMN college_id" in sql
    assert "DROP TABLE colleges" in sql
    assert "UPDATE " not in sql
