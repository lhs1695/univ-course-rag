"""0016 runs only on SQLite memory and PostgreSQL offline DDL contexts."""

import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


def revision():
    return ScriptDirectory(str(Path(__file__).parents[1] / "alembic")).get_revision("0016")


def test_0016_isolated_sqlite_upgrade_downgrade():
    migration = revision()
    assert migration.down_revision == "0015"
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses (id CHAR(32) PRIMARY KEY, title VARCHAR(200))")
        conn.exec_driver_sql(
            "CREATE TABLE documents (id CHAR(32) PRIMARY KEY, course_id CHAR(32) REFERENCES courses(id) ON DELETE CASCADE, retrieval_enabled BOOLEAN NOT NULL DEFAULT 0)"
        )
        conn.exec_driver_sql("INSERT INTO courses (id, title) VALUES ('c', 'old'), ('other', 'other')")
        conn.exec_driver_sql("INSERT INTO documents (id, course_id, retrieval_enabled) VALUES ('old-doc', 'c', 1)")
        with Operations.context(MigrationContext.configure(conn)):
            migration.module.upgrade()
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.commit()
        with conn.begin():
            assert conn.exec_driver_sql("SELECT folder_id, retrieval_enabled FROM documents").one() == (None, 1)
            conn.exec_driver_sql("INSERT INTO course_folders (id, course_id, name) VALUES ('r', 'c', 'root'), ('r2', 'c', 'other root'), ('foreign', 'other', 'root')")
            conn.exec_driver_sql("INSERT INTO course_folders (id, course_id, parent_id, name) VALUES ('s', 'c', 'r', 'child'), ('s2', 'c', 'r2', 'child'), ('foreign-child', 'other', 'foreign', 'child')")
            for sql in [
                "INSERT INTO course_folders (id, course_id, name) VALUES ('dup', 'c', 'root')",
                "INSERT INTO course_folders (id, course_id, parent_id, name) VALUES ('dup', 'c', 'r', 'child')",
                "INSERT INTO course_folders (id, course_id, name) VALUES ('bad', 'missing', 'root')",
                "INSERT INTO course_folders (id, course_id, parent_id, name) VALUES ('bad', 'c', 'missing', 'child')",
                "UPDATE documents SET folder_id='missing'",
            ]:
                with conn.begin_nested(), pytest.raises(IntegrityError):
                    conn.exec_driver_sql(sql)
            conn.exec_driver_sql("UPDATE documents SET folder_id='s'")
            conn.exec_driver_sql("DELETE FROM course_folders WHERE id='s'")
            assert conn.exec_driver_sql("SELECT folder_id, retrieval_enabled FROM documents").one() == (None, 1)
            conn.exec_driver_sql("UPDATE documents SET folder_id='r'")
            conn.exec_driver_sql("DELETE FROM courses WHERE id='other'")
            assert conn.exec_driver_sql("SELECT COUNT(*) FROM course_folders WHERE course_id='other'").scalar_one() == 0
            assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.commit()
        with conn.begin(), Operations.context(MigrationContext.configure(conn)):
            migration.module.downgrade()
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert "course_folders" not in sa.inspect(conn).get_table_names()
        assert "folder_id" not in {column["name"] for column in sa.inspect(conn).get_columns("documents")}
        assert conn.exec_driver_sql("SELECT id, retrieval_enabled FROM documents").one() == ("old-doc", 1)
        assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
    engine.dispose()


def test_0016_postgresql_offline_ddl_only():
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output},
    )
    with Operations.context(context):
        revision().module.upgrade()
        revision().module.downgrade()
    sql = output.getvalue()
    assert "CREATE TABLE course_folders" in sql
    assert "REFERENCES courses (id) ON DELETE CASCADE" in sql
    assert "REFERENCES course_folders (id) ON DELETE SET NULL" in sql
    assert "REFERENCES course_folders (id)" in sql
    assert "CREATE UNIQUE INDEX uq_course_folders_root_name ON course_folders (course_id, name) WHERE parent_id IS NULL" in sql
    assert "CREATE UNIQUE INDEX uq_course_folders_child_name ON course_folders (course_id, parent_id, name) WHERE parent_id IS NOT NULL" in sql
    assert "DROP TABLE course_folders" in sql and "DROP COLUMN folder_id" in sql
    assert "UPDATE documents" not in sql
