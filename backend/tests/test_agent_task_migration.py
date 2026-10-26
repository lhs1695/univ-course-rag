"""Exercise revision 0014 on isolated SQLite and PostgreSQL DDL compilers."""

import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


def _scripts() -> ScriptDirectory:
    return ScriptDirectory(str(Path(__file__).parents[1] / "alembic"))


def _create_parent_tables(connection: sa.Connection) -> None:
    connection.execute(sa.text("CREATE TABLE courses (id CHAR(32) PRIMARY KEY)"))
    connection.execute(sa.text("CREATE TABLE users (id CHAR(32) PRIMARY KEY)"))
    connection.execute(sa.text("INSERT INTO courses (id) VALUES ('course-1')"))
    connection.execute(sa.text("INSERT INTO users (id) VALUES ('user-1')"))


def _insert_task(connection: sa.Connection, task_id: str, key_hash: str, status: str) -> None:
    connection.execute(
        sa.text(
            """INSERT INTO agent_tasks (
                id, course_id, created_by, task_type, focus, window_start, window_end,
                confirm_external_processing, idempotency_key_hash, request_fingerprint,
                status, budget_json, budget_used_json, expires_at
            ) VALUES (
                :id, 'course-1', 'user-1', 'course_question_investigation', 'all',
                '2026-10-01 00:00:00', '2026-10-02 00:00:00', 0, :key_hash, 'fingerprint',
                :status, '{}', '{}', '2026-11-01 00:00:00'
            )"""
        ),
        {"id": task_id, "key_hash": key_hash, "status": status},
    )


def test_agent_task_migration_upgrade_downgrade_isolated_sqlite() -> None:
    scripts = _scripts()
    assert scripts.get_revision("0014").down_revision == "0013"
    migration = scripts.get_revision("0014").module
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        _create_parent_tables(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        inspector = sa.inspect(connection)
        assert {"agent_tasks", "agent_task_events"}.issubset(set(inspector.get_table_names()))
        assert {"courses", "users"}.issubset(set(inspector.get_table_names()))
        task_fks = inspector.get_foreign_keys("agent_tasks")
        assert any(fk["constrained_columns"] == ["course_id"] and fk["options"].get("ondelete") == "CASCADE" for fk in task_fks)
        assert any(fk["constrained_columns"] == ["created_by"] and fk["referred_table"] == "users" for fk in task_fks)
        event_fks = inspector.get_foreign_keys("agent_task_events")
        assert event_fks[0]["options"].get("ondelete") == "CASCADE"
        assert inspector.get_pk_constraint("agent_task_events")["constrained_columns"] == [
            "task_id",
            "sequence",
        ]
        task_indexes = {index["name"]: index for index in inspector.get_indexes("agent_tasks")}
        assert {
            "ix_agent_tasks_course_created_at",
            "ix_agent_tasks_course_status_created_at",
            "ix_agent_tasks_status_lease_expires_at",
            "ix_agent_tasks_expires_at",
            "uq_agent_tasks_active_course",
        }.issubset(task_indexes)
        assert task_indexes["uq_agent_tasks_active_course"]["unique"] == 1
        assert "status IN ('queued', 'running', 'cancel_requested')" in task_indexes[
            "uq_agent_tasks_active_course"
        ]["dialect_options"]["sqlite_where"].text

        _insert_task(connection, "task-1", "key-hash-1", "queued")
        with connection.begin_nested(), pytest.raises(IntegrityError):
            _insert_task(connection, "task-2", "key-hash-2", "running")
        _insert_task(connection, "task-3", "key-hash-2", "failed")
        with connection.begin_nested(), pytest.raises(IntegrityError):
            _insert_task(connection, "task-4", "key-hash-1", "failed")

    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert {"courses", "users"}.issubset(set(sa.inspect(connection).get_table_names()))
        assert not {"agent_tasks", "agent_task_events"}.intersection(set(sa.inspect(connection).get_table_names()))
        assert connection.execute(sa.text("SELECT COUNT(*) FROM courses")).scalar_one() == 1
    engine.dispose()


def test_agent_task_migration_compiles_postgresql_ddl_with_partial_active_unique_index() -> None:
    scripts = _scripts()
    migration = scripts.get_revision("0014").module
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "CREATE TABLE agent_tasks" in sql
    assert "CREATE TABLE agent_task_events" in sql
    assert "UNIQUE (course_id, created_by, idempotency_key_hash)" in sql
    assert "CREATE UNIQUE INDEX uq_agent_tasks_active_course ON agent_tasks (course_id) WHERE status IN ('queued', 'running', 'cancel_requested')" in sql
    assert "PRIMARY KEY (task_id, sequence)" in sql
    assert "DROP TABLE agent_task_events" in sql
    assert "DROP TABLE agent_tasks" in sql
    assert "DROP TABLE courses" not in sql
    assert "DROP TABLE users" not in sql
