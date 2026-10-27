"""Role-specific profiles, employee numbers and isolated 0017 migration checks."""

import io
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from app.models import Course, CourseClass, CourseMember
from sqlalchemy.exc import IntegrityError

from tests import test_course_business as business

client = business.client
scope = business.scope
login = business.login


@pytest.mark.parametrize("role", ["student", "teacher", "admin"])
def test_profile_fields_and_classes_by_global_role(client, db, scope, role):
    user = scope.people[role]
    user.full_name = "测试姓名"
    if role != "student":
        user.employee_number = "EMP-001"
    course = Course(title="有名单班的课程")
    db.add(course)
    db.flush()
    klass = CourseClass(course_id=course.id, name="一班")
    db.add(klass)
    db.flush()
    # A legacy student membership must not expose classes for a global staff role.
    db.add(CourseMember(
        course_id=course.id, user_id=user.id, role="student", class_id=klass.id,
    ))
    db.commit()
    login(client, role)
    response = client.get("/auth/profile")
    assert response.status_code == 200
    assert response.json() == {
        "full_name": "测试姓名",
        "student_number": "00123" if role == "student" else None,
        "employee_number": None if role == "student" else "EMP-001",
        "role": role,
        "classes": [{"course_title": course.title, "class_name": "一班"}]
        if role == "student" else [],
    }
    assert client.get("/auth/me").json()["employee_number"] == user.employee_number


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_admin_creates_edits_and_clears_employee_number(client, scope, role):
    login(client, "admin")
    created = client.post("/admin/users", json={
        "username": "staff", "password": "pass", "role": role,
        "full_name": " 姓名 ", "employee_number": " 001_staff-A ",
    })
    assert created.status_code == 201
    user = created.json()
    assert user["full_name"] == "姓名"
    assert user["student_number"] is None
    assert user["employee_number"] == "001_staff-A"
    path = f"/admin/users/{user['id']}"
    # Omitted fields retain their values; explicit null clears the number.
    assert client.patch(path, json={"full_name": "改名"}).json()["employee_number"] == "001_staff-A"
    changed = client.patch(path, json={"employee_number": " NEW-002 "})
    assert changed.status_code == 200
    assert changed.json()["employee_number"] == "NEW-002"
    listed = next(u for u in client.get("/admin/users").json() if u["id"] == user["id"])
    assert listed["employee_number"] == "NEW-002"
    cleared = client.patch(path, json={"employee_number": None})
    assert cleared.status_code == 200 and cleared.json()["employee_number"] is None
    response = client.post("/auth/login", json={"username": "staff", "password": "pass"})
    assert response.status_code == 200 and response.json()["employee_number"] is None
    assert client.get("/auth/profile").json()["classes"] == []


def test_employee_number_conflicts_rollback_and_independent_student_numbers(client, scope):
    login(client, "admin")
    payload = {"username": "staff1", "password": "pass", "role": "teacher", "employee_number": "00123"}
    first = client.post("/admin/users", json=payload)
    # Employee and student numbers have independent uniqueness namespaces.
    assert first.status_code == 201
    assert client.post("/admin/users", json={**payload, "username": "staff2", "role": "admin"}).status_code == 409
    second = client.post("/admin/users", json={**payload, "username": "staff2", "employee_number": None})
    assert second.status_code == 201
    uid = second.json()["id"]
    assert client.patch(f"/admin/users/{uid}", json={
        "full_name": "must roll back", "employee_number": "00123",
    }).status_code == 409
    listed = next(u for u in client.get("/admin/users").json() if u["id"] == uid)
    assert listed["full_name"] is None and listed["employee_number"] is None
    assert client.patch(f"/admin/users/{first.json()['id']}", json={"employee_number": None}).status_code == 200
    assert client.patch(f"/admin/users/{uid}", json={"employee_number": "00123"}).status_code == 200
    assert client.patch(f"/admin/users/{uuid4()}", json={"employee_number": "missing"}).status_code == 404


@pytest.mark.parametrize("number", ["", "   ", "has space", "x" * 65])
def test_invalid_employee_number_rejected_on_create_and_patch(client, scope, number):
    login(client, "admin")
    assert client.post("/admin/users", json={
        "username": "invalid", "password": "pass", "role": "teacher", "employee_number": number,
    }).status_code == 422
    assert client.patch(f"/admin/users/{scope.people['teacher'].id}", json={"employee_number": number}).status_code == 422


@pytest.mark.parametrize("role", [None, "teacher", "student"])
def test_employee_number_maintenance_requires_admin(client, scope, role):
    if role:
        login(client, role)
    expected = 403 if role else 401
    assert client.post("/admin/users", json={
        "username": "denied", "password": "pass", "role": "teacher", "employee_number": "EMP",
    }).status_code == expected
    assert client.patch(f"/admin/users/{scope.people['teacher'].id}", json={"employee_number": "EMP"}).status_code == expected


def migration():
    scripts = ScriptDirectory(str(Path(__file__).parents[1] / "alembic"))
    revision = scripts.get_revision("0017")
    assert revision.down_revision == "0016"
    return revision.module


def test_0017_isolated_sqlite_upgrade_downgrade_preserves_users_and_references():
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            # Only the pre-0017 users shape and a dependent table, never a live DB.
            metadata = sa.MetaData()
            sa.Table(
                "users", metadata,
                sa.Column("id", sa.String(32), primary_key=True),
                sa.Column("username", sa.String(64), nullable=False, unique=True, index=True),
                sa.Column("password_hash", sa.String(255), nullable=False),
                sa.Column("role", sa.String(16), nullable=False),
                sa.Column("full_name", sa.String(100)),
                sa.Column("student_number", sa.String(64), unique=True),
            )
            sa.Table("dependent", metadata, sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id")))
            metadata.create_all(conn)
            conn.exec_driver_sql("INSERT INTO users VALUES ('old', 'old', 'hash', 'student', '原姓名', 'S001')")
            conn.exec_driver_sql("INSERT INTO dependent VALUES ('old')")
            with Operations.context(MigrationContext.configure(conn)):
                migration().upgrade()
            column = next(c for c in sa.inspect(conn).get_columns("users") if c["name"] == "employee_number")
            assert column["nullable"] and column["type"].length == 64
            assert conn.exec_driver_sql("SELECT full_name, student_number, employee_number FROM users").one() == ("原姓名", "S001", None)
            for uid in ("staff1", "staff2"):
                conn.exec_driver_sql(f"INSERT INTO users (id, username, password_hash, role) VALUES ('{uid}', '{uid}', 'hash', 'teacher')")
            conn.exec_driver_sql("UPDATE users SET employee_number='EMP' WHERE id='staff1'")
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql("UPDATE users SET employee_number='EMP' WHERE id='staff2'")
            assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
            with Operations.context(MigrationContext.configure(conn)):
                migration().downgrade()
            assert "employee_number" not in {c["name"] for c in sa.inspect(conn).get_columns("users")}
            assert conn.exec_driver_sql("SELECT username, full_name, student_number FROM users WHERE id='old'").one() == ("old", "原姓名", "S001")
            assert conn.exec_driver_sql("SELECT user_id FROM dependent").scalar_one() == "old"
            assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
            assert "ix_users_username" in {i["name"] for i in sa.inspect(conn).get_indexes("users")}
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql("UPDATE users SET student_number='S001' WHERE id='staff1'")
            with conn.begin_nested(), pytest.raises(IntegrityError):
                conn.exec_driver_sql("UPDATE users SET username='old' WHERE id='staff1'")
    finally:
        engine.dispose()


def test_0017_postgresql_offline_upgrade_and_downgrade_ddl():
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output},
    )
    with Operations.context(context):
        migration().upgrade()
        migration().downgrade()
    sql = output.getvalue()
    assert "ALTER TABLE users ADD COLUMN employee_number VARCHAR(64)" in sql
    assert "CONSTRAINT uq_users_employee_number UNIQUE (employee_number)" in sql
    assert "ALTER TABLE users DROP CONSTRAINT uq_users_employee_number" in sql
    assert "ALTER TABLE users DROP COLUMN employee_number" in sql
    assert "NOT NULL" not in sql
    assert "UPDATE " not in sql and "CREATE TABLE" not in sql
