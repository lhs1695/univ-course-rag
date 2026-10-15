"""Run only R5's additive migration on an isolated legacy-shaped SQLite DB."""

import importlib.util
import io
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory


def test_source_migration_preserves_legacy_rows_and_has_no_invented_backfill() -> None:
    path = Path(__file__).parents[1] / "alembic/versions/0010_chunk_source_metadata.py"
    spec = importlib.util.spec_from_file_location("r5_source_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT)"))
        connection.execute(sa.text("CREATE TABLE chunks (id INTEGER PRIMARY KEY, text TEXT)"))
        connection.execute(sa.text("INSERT INTO documents VALUES (1, 'legacy.txt')"))
        connection.execute(sa.text("INSERT INTO chunks VALUES (1, 'keep old evidence')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert connection.execute(sa.text("SELECT filename, chunking_version FROM documents")).one() == (
            "legacy.txt", None,
        )
        assert connection.execute(sa.text("SELECT text, source_metadata FROM chunks")).one() == (
            "keep old evidence", None,
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert connection.execute(sa.text("SELECT text FROM chunks")).scalar_one() == "keep old evidence"
        assert {column["name"] for column in sa.inspect(connection).get_columns("chunks")} == {"id", "text"}
    engine.dispose()


def test_postgres_migration_compiles_only_additive_nullable_columns_at_the_new_head() -> None:
    directory = Path(__file__).parents[1] / "alembic"
    scripts = ScriptDirectory(str(directory))
    assert scripts.get_revision("0010").down_revision == "0009"
    migration = scripts.get_revision("0010").module
    output = io.StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
    sql = output.getvalue()
    assert "ALTER TABLE documents ADD COLUMN chunking_version VARCHAR(96)" in sql
    assert "ALTER TABLE chunks ADD COLUMN source_metadata JSON" in sql
    assert "NOT NULL" not in sql
    assert "UPDATE " not in sql
