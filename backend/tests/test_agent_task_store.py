from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.agent.contracts import AgentBudget, InvestigationRequest
from app.models.agent_task import AgentTask, AgentTaskEvent
from app.models.user import UserRole
from app.services.agent_task_store import (
    AgentTaskConflict,
    InvalidInvestigationWindow,
    create_task,
    get_task,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.conftest import TestingSessionLocal, add_user
from tests.test_courses import add_course


@pytest.fixture
def scope(db):
    teacher = add_user(db, "task-teacher", "pass", UserRole.teacher)
    course = add_course(db, "Task course")
    return course.id, teacher.id


def request_at(now, **changes):
    return InvestigationRequest.model_validate({
        "start_at": now - timedelta(days=2), "end_at": now - timedelta(days=1),
        "idempotency_key": "test-key-001", "confirm_external_processing": False, **changes,
    })


def test_create_persisted_task_defaults_and_safe_atomic_event(db: Session, scope):
    """H-task-read: commit, then read with an independent SQLAlchemy session."""
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    row = create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    with TestingSessionLocal() as reader:
        saved = get_task(reader, row.id, course_id=course_id)
        assert saved is not None
        assert (saved.status, saved.attempt) == ("queued", 1)
        assert saved.budget_json == AgentBudget().model_dump()
        assert all(value == 0 for value in saved.budget_used_json.values())
        assert saved.expires_at == now + timedelta(days=90)
        assert saved.window_start.tzinfo is UTC
        assert saved.created_at.tzinfo is UTC
        assert len(saved.idempotency_key_hash) == len(saved.request_fingerprint) == 64
        assert "test-key-001" not in saved.idempotency_key_hash
        event = reader.scalar(select(AgentTaskEvent).where(AgentTaskEvent.task_id == row.id))
        assert (event.sequence, event.attempt, event.event_type) == (1, 1, "task_created")
        assert saved.last_event_sequence == event.sequence
        assert event.safe_summary == "Investigation task queued"
        assert event.evidence_refs_json == []


def test_same_key_normalized_utc_fingerprint_reuses_even_when_active(db, scope):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    request = request_at(now)
    first = create_task(db, request, course_id=course_id, created_by=teacher_id, now=now)
    offset = timezone(timedelta(hours=8))
    equivalent = request.model_copy(update={
        "start_at": request.start_at.astimezone(offset),
        "end_at": request.end_at.astimezone(offset),
    })
    second = create_task(db, equivalent, course_id=course_id, created_by=teacher_id, now=now)
    assert second.id == first.id
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 1
    assert db.scalar(select(func.count()).select_from(AgentTaskEvent)) == 1


@pytest.mark.parametrize("change", [
    {"focus": "no_evidence"}, {"confirm_external_processing": True},
    {"idempotency_key": "another-key-002"},
])
def test_key_fingerprint_or_active_course_conflict(db, scope, change):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    expected = "active_investigation_conflict" if "idempotency_key" in change else "idempotency_conflict"
    with pytest.raises(AgentTaskConflict, match=f"^{expected}$"):
        create_task(db, request_at(now, **change), course_id=course_id, created_by=teacher_id, now=now)


@pytest.mark.parametrize("status", ["queued", "running", "cancel_requested"])
def test_active_course_conflict_across_teachers_is_database_enforced(db, scope, status):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    first = create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    first.status = status
    db.commit()
    other = add_user(db, "other-teacher", "pass", UserRole.teacher)
    with pytest.raises(AgentTaskConflict, match="^active_investigation_conflict$"):
        create_task(db, request_at(now), course_id=course_id, created_by=other.id, now=now)
    # Bypass service precheck: the partial unique index still fences another writer.
    values = {column.name: getattr(first, column.name) for column in AgentTask.__table__.columns}
    values.update(id=uuid4(), created_by=other.id, idempotency_key_hash="b" * 64)
    db.add(AgentTask(**values))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 1


def test_terminal_task_allows_new_key_and_key_is_scoped(db, scope):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    first = create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    first.status = "failed"
    db.commit()
    second = create_task(db, request_at(now, idempotency_key="new-task-key"),
                         course_id=course_id, created_by=teacher_id, now=now)
    another_course = add_course(db, "Another")
    third = create_task(db, request_at(now), course_id=another_course.id, created_by=teacher_id, now=now)
    assert len({first.id, second.id, third.id}) == 3
    assert first.idempotency_key_hash == third.idempotency_key_hash
    assert first.request_fingerprint != third.request_fingerprint
    assert get_task(db, first.id, course_id=another_course.id) is None
    assert get_task(db, uuid4()) is None


@pytest.mark.parametrize("start_days,end_days", [(91, 89), (2, -1)])
def test_reject_window_outside_retention_without_persistence(db, scope, start_days, end_days):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    request = request_at(now, start_at=now - timedelta(days=start_days),
                         end_at=now - timedelta(days=end_days))
    with pytest.raises(InvalidInvestigationWindow, match="investigation_window_outside_retention"):
        create_task(db, request, course_id=course_id, created_by=teacher_id, now=now)
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 0


def test_configured_retention_and_expired_read(db, scope):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    row = create_task(db, request_at(now), course_id=course_id, created_by=teacher_id,
                      now=now, retention_days=7)
    assert row.expires_at == now + timedelta(days=7)
    assert get_task(db, row.id, now=row.expires_at) is None


def test_event_commit_failure_rolls_back_task_and_event(db, scope):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    # Fail after the task INSERT has flushed, while committing its pending event.
    with (
        patch.object(db, "commit", side_effect=RuntimeError("injected transaction failure")),
        pytest.raises(RuntimeError, match="injected transaction failure"),
    ):
        create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 0
    assert db.scalar(select(func.count()).select_from(AgentTaskEvent)) == 0


def test_unrelated_integrity_error_is_not_reported_as_conflict(db, scope):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    failure = IntegrityError("INSERT", {}, Exception("unrelated constraint"))
    with patch.object(db, "flush", side_effect=failure), pytest.raises(IntegrityError):
        create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 0


@pytest.mark.parametrize("changed", [False, True])
def test_integrity_race_requeries_exact_key_after_rollback(db, scope, changed):
    """Deterministic stale precheck; real SQLite uniqueness failure, not PG concurrency."""
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    request = request_at(now)
    first = create_task(db, request, course_id=course_id, created_by=teacher_id, now=now)
    incoming = request_at(now, focus="no_evidence") if changed else request
    with (
        patch("app.services.agent_task_store._existing", side_effect=[None, first]),
        patch.object(db, "scalar", return_value=None),
    ):
        if changed:
            with pytest.raises(AgentTaskConflict, match="^idempotency_conflict$"):
                create_task(db, incoming, course_id=course_id, created_by=teacher_id, now=now)
        else:
            assert create_task(db, incoming, course_id=course_id,
                               created_by=teacher_id, now=now).id == first.id
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 1
    assert db.scalar(select(func.count()).select_from(AgentTaskEvent)) == 1


def test_active_unique_race_returns_active_conflict(db, scope):
    now = datetime.now(UTC)
    course_id, teacher_id = scope
    create_task(db, request_at(now), course_id=course_id, created_by=teacher_id, now=now)
    with (
        patch("app.services.agent_task_store._existing", return_value=None),
        patch.object(db, "scalar", return_value=None),
        pytest.raises(AgentTaskConflict, match="^active_investigation_conflict$"),
    ):
        create_task(db, request_at(now, idempotency_key="new-conflicting-key"),
                    course_id=course_id, created_by=teacher_id, now=now)
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 1
