"""Verify P4 migration without connecting to the target database."""

import io
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory


def test_query_outcome_migration_does_not_invent_historical_facts() -> None:
    scripts = ScriptDirectory(str(Path(__file__).parents[1] / "alembic"))
    assert scripts.get_current_head() == "0011"
    migration = scripts.get_revision("0011").module
    assert migration.down_revision == "0010"
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE query_logs (id INTEGER PRIMARY KEY, hit BOOLEAN, error_code TEXT)"))
        connection.execute(sa.text("INSERT INTO query_logs VALUES (1, 1, NULL)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert connection.execute(sa.text(
            "SELECT hit, error_code, outcome, member_role_at_ask FROM query_logs"
        )).one() == (1, None, None, None)
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert connection.execute(sa.text("SELECT hit, error_code FROM query_logs")).one() == (1, None)
    engine.dispose()


def test_query_outcome_postgres_ddl_is_additive_and_nullable() -> None:
    scripts = ScriptDirectory(str(Path(__file__).parents[1] / "alembic"))
    migration = scripts.get_revision("0011").module
    output = io.StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
    sql = output.getvalue()
    assert "ADD COLUMN outcome VARCHAR(24)" in sql
    assert "ADD COLUMN member_role_at_ask VARCHAR(16)" in sql
    assert "NOT NULL" not in sql
    assert "UPDATE " not in sql
