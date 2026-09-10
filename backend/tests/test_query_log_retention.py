import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.config import Settings
from app.models.query_log import QueryLog
from app.models.user import UserRole
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_courses import add_course, login_as


def _add_log(
    db: Session,
    *,
    course_id,
    user_id,
    query: str,
    created_at: datetime,
) -> QueryLog:
    row = QueryLog(
        id=uuid4(),
        course_id=course_id,
        user_id=user_id,
        query=query,
        hit=True,
        error_code=None,
        chunk_ids="[]",
        duration_ms=1,
        created_at=created_at,
    )
    db.add(row)
    return row


def _log_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(QueryLog)) or 0


def test_query_log_retention_dry_run_and_delete_are_admin_only_and_bounded(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("QUERY_LOG_RETENTION_DAYS", "30")
    monkeypatch.setenv("QUERY_LOG_CLEANUP_BATCH_SIZE", "2")
    admin = add_user(db, "retention-admin", "pass", UserRole.admin)
    teacher = add_user(db, "retention-teacher", "pass", UserRole.teacher)
    course = add_course(db, "Retention")
    now = datetime.now(UTC)
    expired = [
        _add_log(
            db,
            course_id=course.id,
            user_id=teacher.id,
            query=f"private expired question {days}",
            created_at=now - timedelta(days=days),
        )
        for days in (33, 32, 31)
    ]
    retained = _add_log(
        db,
        course_id=course.id,
        user_id=teacher.id,
        query="private retained question",
        created_at=now - timedelta(days=29),
    )
    db.commit()

    login_as(client, teacher.username, "pass")
    assert client.post("/admin/query-logs/retention", json={"mode": "dry_run"}).status_code == 403
    client.post("/auth/logout")
    login_as(client, admin.username, "pass")

    with caplog.at_level(logging.INFO, logger="app.api.query_log_retention"):
        preview = client.post("/admin/query-logs/retention", json={"mode": "dry_run"})
        assert preview.status_code == 200
        assert preview.json()["matched_count"] == 2
        assert preview.json()["deleted_count"] == 0
        assert preview.json()["has_more"] is True
        assert _log_count(db) == 4

        first_delete = client.post("/admin/query-logs/retention", json={"mode": "delete"})
        assert first_delete.status_code == 200
        assert first_delete.json()["deleted_count"] == 2
        assert first_delete.json()["has_more"] is True
        assert db.get(QueryLog, expired[0].id) is None
        assert db.get(QueryLog, expired[1].id) is None
        assert db.get(QueryLog, expired[2].id) is not None
        assert db.get(QueryLog, retained.id) is not None

        second_delete = client.post("/admin/query-logs/retention", json={"mode": "delete"})
        assert second_delete.status_code == 200
        assert second_delete.json()["deleted_count"] == 1
        assert second_delete.json()["has_more"] is False
        assert db.get(QueryLog, expired[2].id) is None
        assert db.get(QueryLog, retained.id) is not None

    assert "query_log_retention_maintenance" in caplog.text
    assert "mode=dry_run count=2" in caplog.text
    assert "mode=delete count=2" in caplog.text
    assert "private" not in caplog.text
    assert admin.username not in caplog.text
    assert teacher.username not in caplog.text
    assert "session_id" not in caplog.text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("query_log_retention_days", 0),
        ("query_log_retention_days", 3_651),
        ("query_log_cleanup_batch_size", 0),
        ("query_log_cleanup_batch_size", 1_001),
    ],
)
def test_query_log_retention_configuration_has_bounds(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})
