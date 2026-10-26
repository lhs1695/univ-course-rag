from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.db import get_db
from app.main import app
from app.models.agent_task import AgentTask
from app.models.course import CourseMember, CourseMemberRole
from app.models.user import UserRole
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingSessionLocal, add_user
from tests.test_courses import add_course, add_member, login_as


@pytest.fixture
def client(db):
    # These endpoints need neither uploads nor tmp_path. Keep DB isolation without
    # the shared upload fixture's platform-dependent temporary-directory ACLs.
    previous = app.dependency_overrides.copy()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def payload(**changes):
    now = datetime.now(UTC)
    return {
        "start_at": (now - timedelta(days=2)).isoformat(),
        "end_at": (now - timedelta(days=1)).isoformat(),
        "confirm_external_processing": False, "idempotency_key": "api-task-key-001", **changes,
    }


@pytest.fixture
def teacher_scope(client, db):
    teacher = add_user(db, "task-teacher", "pass", UserRole.teacher)
    course = add_course(db, "Private task course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    return course


def test_teacher_creates_then_independent_client_and_db_session_reads(client, db, teacher_scope):
    """H-task-read: another HTTP session and fresh DB session load the committed task."""
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    created = client.post(prefix, json=payload())
    assert created.status_code == 201
    body = created.json()
    assert (body["status"], body["attempt"]) == ("queued", 1)
    assert body["course_id"] == str(teacher_scope.id)
    assert all(value == 0 for value in body["budget_used"].values())
    assert body["budget_limits"]["max_runtime_seconds"] == 120
    assert body["created_at"].endswith("Z")
    db.expunge_all()
    original_override = app.dependency_overrides[get_db]

    def independent_db():
        with TestingSessionLocal() as reader:
            yield reader

    app.dependency_overrides[get_db] = independent_db
    try:
        with TestClient(app) as reader:
            login_as(reader, "task-teacher", "pass")
            response = reader.get(f"{prefix}/{body['task_id']}")
            assert response.status_code == 200
            assert response.json() == body
    finally:
        app.dependency_overrides[get_db] = original_override
    assert set(body) == {
        "task_id", "course_id", "status", "attempt", "budget_limits", "budget_used",
        "error_code", "created_at", "expires_at",
    }


@pytest.mark.parametrize("role,membership", [
    (UserRole.student, CourseMemberRole.student),
    (UserRole.teacher, None), (UserRole.teacher, CourseMemberRole.student),
    (UserRole.admin, None),
])
def test_non_course_teacher_cannot_create_or_read_no_content_leak(
    client, db, teacher_scope, role, membership,
):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    created = client.post(prefix, json=payload()).json()
    outsider = add_user(db, "outsider", "pass", role)
    if membership is not None:
        add_member(db, teacher_scope, outsider, membership)
    other_course = add_course(db, "Other course")
    if role == UserRole.teacher:
        add_member(db, other_course, outsider, CourseMemberRole.teacher)
    login_as(client, "outsider", "pass")
    for response in [client.post(prefix, json=payload()),
                     client.get(f"{prefix}/{created['task_id']}")]:
        assert response.status_code == 403
        assert set(response.json()) == {"detail"}
        assert created["task_id"] not in response.text
        assert "budget" not in response.text
        assert "Private task course" not in response.text


def test_wrong_course_missing_and_expired_task_share_safe_404(client, db, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    created = client.post(prefix, json=payload()).json()
    teacher = add_user(db, "second-teacher", "pass", UserRole.teacher)
    second = add_course(db, "Second")
    add_member(db, second, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    wrong_course = client.get(f"/courses/{second.id}/agent-tasks/{created['task_id']}")
    missing = client.get(f"/courses/{second.id}/agent-tasks/{uuid4()}")
    assert wrong_course.status_code == missing.status_code == 404
    assert wrong_course.json() == missing.json() == {"detail": "Task not found"}
    login_as(client, "task-teacher", "pass")
    row = db.scalar(select(AgentTask))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get(f"{prefix}/{created['task_id']}").json() == missing.json()


def test_api_idempotency_and_stable_conflict_codes(client, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    body = payload()
    first = client.post(prefix, json=body)
    repeated = client.post(prefix, json=body)
    assert repeated.status_code == 201
    assert repeated.json()["task_id"] == first.json()["task_id"]
    conflict = client.post(prefix, json={**body, "focus": "no_evidence"})
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "idempotency_conflict"}
    active = client.post(prefix, json={**body, "idempotency_key": "another-key"})
    assert active.status_code == 409
    assert active.json() == {"detail": "active_investigation_conflict"}


def test_api_rejects_scope_and_budget_override_and_missing_confirmation(client, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    for extra in [{"course_id": str(uuid4())}, {"budget": {"max_steps": 999}}]:
        assert client.post(prefix, json=payload(**extra)).status_code == 422
    body = payload()
    del body["confirm_external_processing"]
    assert client.post(prefix, json=body).status_code == 422
    expired = payload(start_at=(datetime.now(UTC) - timedelta(days=91)).isoformat(),
                      end_at=(datetime.now(UTC) - timedelta(days=90)).isoformat())
    response = client.post(prefix, json=expired)
    assert response.status_code == 422
    assert response.json() == {"detail": "investigation_window_outside_retention"}


def test_anonymous_task_endpoints_require_login(client, db):
    course = add_course(db, "No login")
    prefix = f"/courses/{course.id}/agent-tasks"
    assert client.post(prefix, json=payload()).status_code == 401
    assert client.get(f"{prefix}/{uuid4()}").status_code == 401


def test_read_uses_safe_projection_and_rechecks_current_membership(client, db, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    created = client.post(prefix, json=payload()).json()
    row = db.scalar(select(AgentTask))
    row.checkpoint_json = {"private": "SECRET-SENTINEL question/prompt"}
    row.report_json = {"private": "REPORT-SENTINEL"}
    db.commit()
    response = client.get(f"{prefix}/{created['task_id']}")
    assert response.status_code == 200
    assert "SENTINEL" not in response.text
    assert "checkpoint" not in response.text
    assert "report_json" not in response.text
    assert "idempotency" not in response.text
    member = db.scalar(select(CourseMember).where(CourseMember.course_id == teacher_scope.id))
    db.delete(member)
    db.commit()
    denied = client.get(f"{prefix}/{created['task_id']}")
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Not a course member"}
