import logging
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.models.agent_task import AgentTask, AgentTaskEvent
from app.models.user import UserRole
from app.services.agent_task_retention import maintain_agent_tasks
from app.services.agent_task_store import create_task, get_task
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_agent_task_store import request_at
from tests.test_courses import add_course, login_as

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
STATUSES = (
    "queued", "running", "cancel_requested", "succeeded", "failed", "cancelled",
    "interrupted", "budget_exceeded",
)


@pytest.fixture
def cascade_db(db: Session):
    """Enable real SQLite FK cascades only for these tests, then restore the fixture."""
    previous = db.scalar(text("PRAGMA foreign_keys"))
    db.commit()
    db.execute(text("PRAGMA foreign_keys=ON"))
    assert db.scalar(text("PRAGMA foreign_keys")) == 1
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.execute(text(f"PRAGMA foreign_keys={int(previous)}"))
        db.commit()


@pytest.fixture
def teacher_id(cascade_db):
    return add_user(cascade_db, "ttl-teacher", "pass", UserRole.teacher).id


def _add_task(db, teacher_id, *, expires_at, status="succeeded"):
    created_at = NOW - timedelta(days=100)
    course = add_course(db, f"TTL {uuid4()}")
    row = create_task(
        db, request_at(created_at), course_id=course.id, created_by=teacher_id,
        now=created_at,
    )
    row.expires_at = expires_at
    row.status = status
    db.commit()
    return row.id


def _event_task_ids(db):
    return set(db.scalars(select(AgentTaskEvent.task_id)).all())


@pytest.mark.parametrize("status", STATUSES)
def test_expiry_alone_controls_dry_run_and_delete(cascade_db, teacher_id, status):
    db = cascade_db
    expired_id = _add_task(db, teacher_id, expires_at=NOW, status=status)
    live_id = _add_task(
        db, teacher_id, expires_at=NOW + timedelta(microseconds=1), status=status,
    )

    preview = maintain_agent_tasks(db, batch_size=10, delete_matched=False, now=NOW)
    assert preview.cutoff == NOW
    assert preview.cutoff.tzinfo is UTC
    assert (preview.matched_count, preview.deleted_count, preview.has_more) == (1, 0, False)
    assert db.get(AgentTask, expired_id) is not None
    assert get_task(db, expired_id, now=NOW) is None
    assert get_task(db, live_id, now=NOW) is not None
    assert _event_task_ids(db) == {expired_id, live_id}

    result = maintain_agent_tasks(db, batch_size=10, delete_matched=True, now=NOW)
    db.commit()
    assert (result.matched_count, result.deleted_count, result.has_more) == (1, 1, False)
    assert db.get(AgentTask, expired_id) is None
    assert get_task(db, expired_id, now=NOW) is None
    assert get_task(db, live_id, now=NOW) is not None
    assert _event_task_ids(db) == {live_id}


def test_batches_order_by_expiry_then_id_and_report_has_more(cascade_db, teacher_id):
    db = cascade_db
    oldest = _add_task(db, teacher_id, expires_at=NOW - timedelta(days=2), status="running")
    tied = sorted(
        _add_task(db, teacher_id, expires_at=NOW - timedelta(days=1)) for _ in range(2)
    )
    boundary = _add_task(db, teacher_id, expires_at=NOW)
    live = _add_task(db, teacher_id, expires_at=NOW + timedelta(days=1))

    preview = maintain_agent_tasks(db, batch_size=2, delete_matched=False, now=NOW)
    assert (preview.matched_count, preview.deleted_count, preview.has_more) == (2, 0, True)
    assert db.scalar(select(func.count()).select_from(AgentTask)) == 5

    first = maintain_agent_tasks(db, batch_size=2, delete_matched=True, now=NOW)
    db.commit()
    assert (first.matched_count, first.deleted_count, first.has_more) == (2, 2, True)
    assert db.get(AgentTask, oldest) is None
    assert db.get(AgentTask, tied[0]) is None
    assert _event_task_ids(db) == {tied[1], boundary, live}

    second = maintain_agent_tasks(db, batch_size=2, delete_matched=True, now=NOW)
    db.commit()
    assert (second.matched_count, second.deleted_count, second.has_more) == (2, 2, False)
    assert _event_task_ids(db) == {live}
    assert set(db.scalars(select(AgentTask.id))) == {live}

    empty = maintain_agent_tasks(db, batch_size=2, delete_matched=True, now=NOW)
    assert (empty.matched_count, empty.deleted_count, empty.has_more) == (0, 0, False)


def test_service_leaves_transaction_to_caller(cascade_db, teacher_id):
    db = cascade_db
    task_id = _add_task(db, teacher_id, expires_at=NOW)
    loaded = db.get(AgentTask, task_id)
    assert loaded is not None
    maintain_agent_tasks(db, batch_size=1, delete_matched=True, now=NOW)
    assert db.get(AgentTask, task_id) is None
    assert _event_task_ids(db) == set()
    db.rollback()
    assert loaded.id == task_id
    assert db.get(AgentTask, task_id) is not None
    assert _event_task_ids(db) == {task_id}


def test_cutoff_normalizes_aware_time_to_utc(cascade_db):
    result = maintain_agent_tasks(
        cascade_db, batch_size=1, delete_matched=False,
        now=NOW.astimezone(timezone(timedelta(hours=8))),
    )
    assert result.cutoff == NOW
    assert result.cutoff.tzinfo is UTC


@pytest.mark.parametrize("batch_size", [0, -1])
def test_service_rejects_nonpositive_batch(cascade_db, batch_size):
    with pytest.raises(ValueError, match="batch_size must be positive"):
        maintain_agent_tasks(cascade_db, batch_size=batch_size, delete_matched=True, now=NOW)


def test_service_rejects_naive_time(cascade_db):
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        maintain_agent_tasks(
            cascade_db, batch_size=1, delete_matched=True, now=NOW.replace(tzinfo=None),
        )


def test_api_admin_only_default_preview_bounded_delete_and_safe_log(
    client: TestClient, cascade_db, teacher_id, monkeypatch, caplog,
):
    db = cascade_db
    monkeypatch.setenv("QUERY_LOG_CLEANUP_BATCH_SIZE", "2")
    admin = add_user(db, "ttl-admin", "pass", UserRole.admin)
    student = add_user(db, "ttl-student", "pass", UserRole.student)
    expired = [
        _add_task(db, teacher_id, expires_at=NOW - timedelta(days=days))
        for days in (2, 1, 0)
    ]
    live = _add_task(db, teacher_id, expires_at=NOW + timedelta(days=1), status="running")
    path = "/admin/agent-tasks/retention"

    for username in ("ttl-teacher", student.username):
        login_as(client, username, "pass")
        for mode in ("dry_run", "delete"):
            assert client.post(path, json={"mode": mode}).status_code == 403
        client.post("/auth/logout")
    assert _event_task_ids(db) == {*expired, live}
    login_as(client, admin.username, "pass")

    with (
        patch("app.services.agent_task_retention.datetime", wraps=datetime) as clock,
        caplog.at_level(logging.INFO, logger="app.api.agent_task_retention"),
    ):
        clock.now.return_value = NOW
        preview = client.post(path, json={})
        assert preview.status_code == 200
        assert preview.json() == {
            "mode": "dry_run", "batch_limit": 2, "matched_count": 2,
            "deleted_count": 0, "has_more": True, "cutoff": NOW.isoformat().replace("+00:00", "Z"),
        }
        assert _event_task_ids(db) == {*expired, live}
        assert client.post(path, json={"mode": "invalid"}).status_code == 422

        first = client.post(path, json={"mode": "delete"})
        assert first.status_code == 200
        assert first.json()["deleted_count"] == 2
        assert first.json()["has_more"] is True
        assert _event_task_ids(db) == {expired[2], live}
        for task_id in expired[:2]:
            assert db.get(AgentTask, task_id) is None
            assert get_task(db, task_id, now=NOW) is None

        second = client.post(path, json={"mode": "delete"})
        assert second.status_code == 200
        assert second.json()["deleted_count"] == 1
        assert second.json()["has_more"] is False
        assert _event_task_ids(db) == {live}
        assert get_task(db, live, now=NOW) is not None

    assert "agent_task_retention_maintenance mode=dry_run count=2" in caplog.text
    assert "agent_task_retention_maintenance mode=delete count=2" in caplog.text
    assert "ttl-teacher" not in caplog.text
    assert admin.username not in caplog.text
    assert str(teacher_id) not in caplog.text
    assert str(live) not in caplog.text
