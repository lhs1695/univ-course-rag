import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.models import AgentTask, AgentTaskEvent
from app.models.course import CourseMember, CourseMemberRole
from app.models.user import UserRole
from app.services import embedder, llm, question_groups
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests import test_agent_investigation_runner, test_agent_task_api
from tests.conftest import TestingSessionLocal, add_user
from tests.test_courses import add_course, add_member, login_as

client = test_agent_task_api.client
teacher_scope = test_agent_task_api.teacher_scope
payload = test_agent_task_api.payload
snapshot = test_agent_investigation_runner.snapshot


@pytest.fixture(autouse=True)
def fake_settings(client):
    settings = Settings(_env_file=None, llm_backend="fake", embedder_backend="fake")
    app.dependency_overrides[get_settings] = lambda: settings
    yield settings
    app.dependency_overrides.pop(get_settings, None)


def create_and_run(client, course):
    prefix = f"/courses/{course.id}/agent-tasks"
    created = client.post(prefix, json=payload())
    assert created.status_code == 201
    task_id = created.json()["task_id"]
    result = client.post(f"{prefix}/{task_id}/run")
    assert result.status_code == 200, result.text
    assert result.json()["created_at"].endswith("Z")
    assert result.json()["expires_at"].endswith("Z")
    return prefix, task_id


def test_h01_empty_report_committed_independent_http_and_new_db_session(
    client, db, teacher_scope,
):
    prefix, task_id = create_and_run(client, teacher_scope)
    row = db.get(AgentTask, UUID(task_id))
    assert row.status == "succeeded"
    assert row.report_json["findings"] == row.report_json["candidate_causes"] == []
    events = db.scalars(select(AgentTaskEvent).order_by(AgentTaskEvent.sequence)).all()
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    assert [e.event_type for e in events[:2]] == ["task_created", "task_started"]
    assert events[-1].event_type == "task_terminal"
    assert row.budget_used_json["model_calls"] == row.budget_used_json["tool_calls"] == 1
    db.expunge_all()
    original = app.dependency_overrides[get_db]

    def independent_db():
        with TestingSessionLocal() as reader:
            yield reader

    app.dependency_overrides[get_db] = independent_db
    try:
        with TestClient(app) as reader:
            login_as(reader, "task-teacher", "pass")
            response = reader.get(f"{prefix}/{task_id}/report")
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "succeeded"
            assert body["sample_count"] == body["summary"]["student_attempts"] == 0
            assert body["summary"]["recorded_attempts"] == 0
            assert body["summary"]["no_evidence_rate"] is None
            assert body["report"]["findings"] == body["report"]["candidate_causes"] == []
            assert body["report"]["unknowns"]
            assert body["sources"] == body["evidence_sources"] == []
            assert "report" not in reader.get(f"{prefix}/{task_id}").json()
    finally:
        app.dependency_overrides[get_db] = original
    assert client.post(f"{prefix}/{task_id}/run").json() == {"detail": "investigation_not_queued"}
    # A completed investigation releases the M1 single-active slot; same key is reused.
    body = payload(idempotency_key="next-investigation-key")
    assert client.post(prefix, json=body).status_code == 201


def test_h01_nonempty_report_independent_http_and_new_db_session(client, db, snapshot):
    course, row, _, _ = snapshot
    login_as(client, "fixture-teacher", "pass")
    prefix = f"/courses/{course.id}/agent-tasks/{row.id}"
    response = client.post(f"{prefix}/run")
    assert response.status_code == 200 and response.json()["status"] == "succeeded"
    assert row.report_json["findings"]
    stored_report = row.report_json
    db.expunge_all()
    original = app.dependency_overrides[get_db]

    def independent_db():
        with TestingSessionLocal() as reader:
            yield reader

    app.dependency_overrides[get_db] = independent_db
    try:
        with TestClient(app) as reader:
            login_as(reader, "fixture-teacher", "pass")
            body = reader.get(f"{prefix}/report").json()
            assert body["status"] == "succeeded" and body["report"] == stored_report
            assert body["sample_count"] == 5
            assert len(body["sources"]) == 5 and all(s["available"] for s in body["sources"])
            assert "Explain the fixed definition" not in json.dumps(body)
    finally:
        app.dependency_overrides[get_db] = original


@pytest.mark.parametrize("backends", [
    {"llm_backend": "deepseek"},
    {"embedder_backend": "siliconflow"},
    {"embedder_backend": "siliconflow", "question_grouping_backend": "embedding"},
    {"llm_backend": "deepseek", "embedder_backend": "siliconflow"},
])
def test_external_gate_rejects_before_insert_with_real_factory_boundary_spies(
    client, db, teacher_scope, fake_settings, monkeypatch, backends,
):
    for name, value in backends.items():
        monkeypatch.setattr(fake_settings, name, value)
    spies = []
    # Patch the actual provider factories/getters, including the grouping module's
    # imported build_embedder alias. Any attempt fails without network access.
    for module, names in [
        (llm, ("build_llm", "get_llm")),
        (embedder, ("build_embedder", "get_embedder")),
        (question_groups, ("build_embedder", "build_question_embedder", "get_question_embedder")),
    ]:
        for name in names:
            spy = Mock(side_effect=AssertionError("External adapter must not be constructed"))
            monkeypatch.setattr(module, name, spy)
            spies.append(spy)
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    response = client.post(prefix, json=payload())
    assert response.status_code == 422
    assert response.json() == {"detail": "external_processing_confirmation_required"}
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 0
    assert db.scalar(select(func.count()).select_from(AgentTaskEvent)) == 0
    assert [spy.call_count for spy in spies] == [0] * len(spies)
    # Confirmation opens only the request gate; M2 execution remains Fake/Replay.
    response = client.post(prefix, json=payload(confirm_external_processing=True))
    assert response.status_code == 201
    task_id = response.json()["task_id"]
    assert client.post(f"{prefix}/{task_id}/run").json()["status"] == "succeeded"
    assert [spy.call_count for spy in spies] == [0] * len(spies)


def test_run_rechecks_confirmation_if_settings_changed(
    client, db, teacher_scope, fake_settings, monkeypatch,
):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    task_id = client.post(prefix, json=payload()).json()["task_id"]
    monkeypatch.setattr(fake_settings, "llm_backend", "deepseek")
    assert client.post(f"{prefix}/{task_id}/run").status_code == 422
    assert db.get(AgentTask, UUID(task_id)).status == "queued"


@pytest.mark.parametrize("role,membership", [
    (UserRole.student, CourseMemberRole.student), (UserRole.teacher, None),
    (UserRole.teacher, CourseMemberRole.student), (UserRole.admin, None),
])
def test_report_and_run_require_current_course_teacher(
    client, db, teacher_scope, role, membership,
):
    prefix, task_id = create_and_run(client, teacher_scope)
    outsider = add_user(db, "report-outsider", "pass", role)
    if membership:
        add_member(db, teacher_scope, outsider, membership)
    login_as(client, outsider.username, "pass")
    for response in [client.get(f"{prefix}/{task_id}/report"),
                     client.post(f"{prefix}/{task_id}/run")]:
        assert response.status_code == 403
        assert set(response.json()) == {"detail"}
        assert task_id not in response.text


def test_report_wrong_course_missing_expired_and_revoked_are_safe(client, db, teacher_scope):
    prefix, task_id = create_and_run(client, teacher_scope)
    teacher = add_user(db, "other-report-teacher", "pass", UserRole.teacher)
    other = add_course(db, "Other")
    add_member(db, other, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    other_prefix = f"/courses/{other.id}/agent-tasks"
    wrong = client.get(f"{other_prefix}/{task_id}/report")
    missing = client.get(f"{other_prefix}/{uuid4()}/report")
    assert wrong.status_code == missing.status_code == 404
    assert wrong.json() == missing.json() == {"detail": "Task not found"}
    login_as(client, "task-teacher", "pass")
    row = db.get(AgentTask, UUID(task_id))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get(f"{prefix}/{task_id}/report").json() == missing.json()
    db.delete(db.scalar(select(CourseMember).where(CourseMember.course_id == teacher_scope.id)))
    db.commit()
    assert client.get(f"{prefix}/{task_id}/report").status_code == 403


def test_report_queued_failed_and_anonymous_states(client, db, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    task_id = client.post(prefix, json=payload()).json()["task_id"]
    body = client.get(f"{prefix}/{task_id}/report").json()
    assert body["status"] == "queued" and body["report"] is None
    row = db.get(AgentTask, UUID(task_id))
    row.budget_json = {**row.budget_json, "max_tool_calls": 0}
    db.commit()
    assert client.post(f"{prefix}/{task_id}/run").json()["status"] == "budget_exceeded"
    body = client.get(f"{prefix}/{task_id}/report").json()
    assert body["report"] is None and body["error_code"] == "agent_tool_budget_exceeded"
    with TestClient(app) as anonymous:
        assert anonymous.get(f"{prefix}/{task_id}/report").status_code == 401
        assert anonymous.post(f"{prefix}/{task_id}/run").status_code == 401


def test_execution_failure_report_has_safe_terminal_code(client, teacher_scope, monkeypatch):
    from app.services import agent_investigation

    def broken(*_args, **_kwargs):
        raise RuntimeError("PRIVATE-SENTINEL original exception and question")

    monkeypatch.setattr(agent_investigation, "build_initial_observation", broken)
    prefix, task_id = create_and_run(client, teacher_scope)
    response = client.get(f"{prefix}/{task_id}/report")
    assert response.status_code == 200
    assert response.json()["status"] == "failed" and response.json()["report"] is None
    assert response.json()["error_code"] == "investigation_execution_failed"
    assert "PRIVATE-SENTINEL" not in response.text
