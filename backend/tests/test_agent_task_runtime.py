"""M3 H06/H07/H11/H-source: isolated SQLite, never a PostgreSQL claim."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.agent.contracts import InvestigationRequest
from app.models import QueryLog
from app.models.agent_task import AgentTask, AgentTaskEvent
from app.models.course import CourseMember
from app.services import agent_investigation as investigation
from app.services.agent_task_runtime import (
    ExecutionRevoked,
    cancel_task,
    finish_task,
    interrupt_stale,
    progress_task,
    restart_task,
    start_task,
)
from app.services.agent_task_store import AgentTaskConflict, create_task
from sqlalchemy import event, select, update
from sqlalchemy.exc import IntegrityError

from tests import (
    test_agent_investigation_api,
    test_agent_investigation_runner,
    test_agent_task_api,
)
from tests.conftest import TestingSessionLocal

fake_settings = test_agent_investigation_api.fake_settings
snapshot = test_agent_investigation_runner.snapshot
client = test_agent_task_api.client
teacher_scope = test_agent_task_api.teacher_scope
payload = test_agent_task_api.payload
evidence_replay = test_agent_investigation_runner.evidence_replay


def expire(db, row):
    row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert interrupt_stale(db, row)


def test_h06_queued_cancel_is_idempotent_and_cannot_run(db, snapshot):
    course, row, *_ = snapshot
    cancel_task(db, row)
    count = row.last_event_sequence
    cancel_task(db, row)
    assert row.status == "cancelled" and row.last_event_sequence == count
    assert not investigation.run_investigation(db, row, course_title=course.title)
    assert row.budget_used_json["model_calls"] == 0


def test_h06_cancel_wins_finish_and_stale_finish_writes_nothing(db, snapshot):
    _, row, *_ = snapshot
    from app.agent.contracts import InvestigationReport, TaskStatus
    from app.agent.replay_harness import ReplayResult

    assert start_task(db, row)
    token = row.run_token
    result = ReplayResult(TaskStatus.succeeded, InvestigationReport(summary="Safe fixture"), (), 1, 1, 1)
    cancel_task(db, row)
    assert finish_task(db, row, token, result, snapshot=row.checkpoint_json)
    assert row.status == "cancelled" and row.report_json is None
    before = row.last_event_sequence
    assert not finish_task(db, row, token, result, snapshot={})
    assert row.last_event_sequence == before and row.report_json is None


def test_expired_cancel_token_cannot_finish_or_recurse(db, snapshot):
    _, row, *_ = snapshot
    from app.agent.contracts import TaskStatus
    from app.agent.replay_harness import ReplayResult

    assert start_task(db, row)
    token = row.run_token
    cancel_task(db, row)
    row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    result = ReplayResult(TaskStatus.cancelled, None, (), 0, 0, 0)
    assert not finish_task(db, row, token, result, snapshot={})
    assert interrupt_stale(db, row) and row.status == "cancelled"


def test_h06_cancel_during_tool_stops_next_model_and_tool(db, snapshot, monkeypatch):
    course, row, *_ = snapshot
    original = investigation._fake_tools

    def tools(session, task):
        wrapped = original(session, task)

        def search(query):
            result = wrapped.search_course_evidence(query)
            with TestingSessionLocal() as canceller:
                cancel_task(canceller, canceller.get(AgentTask, row.id))
            return result

        return investigation.ReplayTools(search, wrapped.open_evidence, wrapped.get_document_quality)

    monkeypatch.setattr(investigation, "_fake_tools", tools)
    investigation.run_investigation(db, row, course_title=course.title,
                                   replay_responses=evidence_replay(snapshot))
    assert row.status == "cancelled" and row.report_json is None
    assert row.budget_used_json["model_calls"] == row.budget_used_json["tool_calls"] == 1


@pytest.mark.parametrize("cancel", [False, True])
def test_h07_expiry_revokes_old_writes_and_only_explicit_resume(db, snapshot, cancel):
    _, row, *_ = snapshot
    assert start_task(db, row)
    token = row.run_token
    if cancel:
        cancel_task(db, row)
    expire(db, row)
    assert row.status == ("cancelled" if cancel else "interrupted")
    assert row.run_token is None
    count = row.last_event_sequence
    with pytest.raises(ExecutionRevoked):
        progress_task(db, row, token, usage=row.budget_used_json, snapshot={})
    assert row.last_event_sequence == count
    if not cancel:
        restart_task(db, row, operation="resume", checkpoint_safe=True)
        assert row.status == "queued" and row.attempt == 2
        assert start_task(db, row) and row.run_token != token
        with pytest.raises(ExecutionRevoked):
            progress_task(db, row, token, usage={}, snapshot={})
        assert row.status == "running" and row.attempt == 2


def test_h07_real_process_exit_after_claim_and_reservation(db, snapshot):
    """A child process commits progress and exits without finishing its lease."""
    # A file-backed database is required to exercise an actual process boundary.
    import subprocess
    from pathlib import Path
    from tempfile import NamedTemporaryFile

    from app.db import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    _, row, *_ = snapshot
    with NamedTemporaryFile(dir=Path.cwd(), prefix=".tmp-m3-process-", suffix=".sqlite",
                            delete_on_close=False) as temporary:
        path = Path(temporary.name)
        engine = create_engine(f"sqlite:///{path.as_posix()}")
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                records = db.execute(select(table)).mappings().all()
                if records:
                    conn.execute(table.insert(), [dict(r) for r in records])
        code = '''
import os, sys
from app.config import Settings
Settings.model_config["env_file"] = None
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.agent_task import AgentTask
from app.services.agent_task_runtime import start_task, progress_task
from uuid import UUID
with Session(create_engine(sys.argv[1])) as db:
    row = db.get(AgentTask, UUID(sys.argv[2]))
    assert start_task(db, row)
    usage = dict(row.budget_used_json, steps=1, model_calls=1, runtime_seconds=2)
    progress_task(db, row, row.run_token, usage=usage, snapshot=row.checkpoint_json)
os._exit(17)
'''
        import sys

        completed = subprocess.run([sys.executable, "-c", code, str(engine.url), str(row.id)],
                                   cwd=Path.cwd() / "backend", capture_output=True, timeout=15, check=False)
        assert completed.returncode == 17, completed.stderr.decode(errors="replace")
        with Session(engine, expire_on_commit=False) as reader:
            saved = reader.get(AgentTask, row.id)
            assert saved.status == "running" and saved.budget_used_json["model_calls"] == 1
            expire(reader, saved)
            assert saved.status == "interrupted"
            restart_task(reader, saved, operation="resume", checkpoint_safe=True)
            assert saved.attempt == 2 and saved.budget_used_json["model_calls"] == 1
        engine.dispose()


@pytest.mark.parametrize("operation,state", [("resume", "interrupted"), ("retry", "failed"),
                                             ("retry", "cancelled"), ("retry", "budget_exceeded")])
def test_h11_restart_partial_unique_index_and_key_reuse(db, snapshot, operation, state):
    course, row, *_ = snapshot
    row.status = state
    db.commit()
    now = datetime.now(UTC)
    request = InvestigationRequest(start_at=now - timedelta(days=2), end_at=now - timedelta(days=1),
                                   confirm_external_processing=False, idempotency_key="m3-other-key")
    other = create_task(db, request, course_id=course.id, created_by=row.created_by)
    assert create_task(db, request, course_id=course.id, created_by=row.created_by).id == other.id
    with pytest.raises(AgentTaskConflict, match="active_investigation_conflict"):
        restart_task(db, row, operation=operation, checkpoint_safe=True)
    # Bypass every service check: the database itself rejects this transition.
    with pytest.raises(IntegrityError):
        db.execute(update(AgentTask).where(AgentTask.id == row.id).values(status="queued"))
        db.commit()
    db.rollback()
    assert row.status == state and row.attempt == 1
    cancel_task(db, other)
    restart_task(db, row, operation=operation, checkpoint_safe=True)
    assert row.status == "queued" and row.attempt == 2
    assert create_task(db, request, course_id=course.id, created_by=row.created_by).id == other.id


@pytest.mark.parametrize("mutation", ["query_deleted", "query_expired", "doc_disabled", "chunk_deleted"])
def test_h_source_resume_metadata_only_rejects_unavailable(db, snapshot, mutation):
    course, row, doc, chunk = snapshot
    investigation.run_investigation(db, row, course_title=course.title,
                                   replay_responses=evidence_replay(snapshot))
    row.status = "interrupted"
    if mutation == "query_deleted":
        db.delete(db.get(QueryLog, UUID(row.checkpoint_json["source_query_ids"][0])))
    elif mutation == "query_expired":
        db.get(QueryLog, UUID(row.checkpoint_json["source_query_ids"][0])).created_at = datetime.now(UTC) - timedelta(days=100)
    elif mutation == "doc_disabled":
        doc.retrieval_enabled = False
    else:
        db.delete(chunk)
    db.commit()
    sql = []

    def capture(conn, cursor, statement, parameters, context, many):
        sql.append(statement.lower())

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        safe = investigation.checkpoint_is_safe(db, row, retention_days=90)
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert not safe
    assert not any("query_logs.query" in s or "chunks.text" in s for s in sql)
    before = dict(row.budget_used_json)
    restart_task(db, row, operation="resume", checkpoint_safe=safe)
    assert row.status == "failed" and row.budget_used_json == before


def test_resume_unsafe_and_budget_exhausted_do_not_start_new_attempt(db, snapshot):
    _, row, *_ = snapshot
    row.status, row.checkpoint_json = "interrupted", {"unsafe": True}
    db.commit()
    restart_task(db, row, operation="resume", checkpoint_safe=False)
    assert row.status == "failed" and row.attempt == 1
    row.budget_used_json = {**row.budget_used_json, "model_calls": 8}
    db.commit()
    with pytest.raises(AgentTaskConflict, match="agent_budget_exhausted"):
        restart_task(db, row, operation="retry", checkpoint_safe=True)
    assert row.status == "budget_exceeded" and row.attempt == 1


def test_api_explicit_cancel_resume_retry_confirmation_and_permissions(client, db, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    id = client.post(prefix, json=payload()).json()["task_id"]
    row = db.get(AgentTask, UUID(id))
    assert client.post(f"{prefix}/{id}/resume", json={"confirm_external_processing": True}).status_code == 409
    assert client.post(f"{prefix}/{id}/cancel").json()["status"] == "cancelled"
    assert client.post(f"{prefix}/{id}/retry", json={"confirm_external_processing": False}).status_code == 422
    assert client.post(f"{prefix}/{id}/retry", json={"confirm_external_processing": True}).json()["attempt"] == 2
    assert start_task(db, row)
    expire(db, row)
    assert client.get(f"{prefix}/{id}").json()["status"] == "interrupted"
    assert client.post(f"{prefix}/{id}/resume", json={"confirm_external_processing": True}).json()["attempt"] == 3
    events = client.get(f"{prefix}/{id}/events").json()
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert all("query" not in e and "run_token" not in e for e in events)
    member = db.scalar(select(CourseMember).where(CourseMember.course_id == teacher_scope.id))
    db.delete(member)
    db.commit()
    for endpoint in ("cancel", "resume", "retry"):
        assert client.post(f"{prefix}/{id}/{endpoint}", json={"confirm_external_processing": True}).status_code in {403, 404}
    assert client.get(f"{prefix}/{id}/events").status_code in {403, 404}


def test_api_read_marks_expired_without_implicit_resume(client, db, teacher_scope):
    prefix = f"/courses/{teacher_scope.id}/agent-tasks"
    id = client.post(prefix, json=payload()).json()["task_id"]
    row = db.get(AgentTask, UUID(id))
    assert start_task(db, row)
    row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    body = client.get(f"{prefix}/{id}").json()
    assert body["status"] == "interrupted" and body["attempt"] == 1
    assert client.post(f"{prefix}/{id}/run").status_code == 409
    assert client.get(f"{prefix}/{id}").json()["status"] == "interrupted"
    assert client.post(f"{prefix}/{id}/resume", json={"confirm_external_processing": False}).status_code == 422
    assert row.status == "interrupted" and row.attempt == 1


def test_api_resume_unavailable_stops_before_source_body_or_model(client, db, snapshot):
    from tests.test_courses import login_as

    course, row, doc, _ = snapshot
    investigation.run_investigation(db, row, course_title=course.title,
                                   replay_responses=evidence_replay(snapshot))
    row.status = "interrupted"
    doc.retrieval_enabled = False
    db.commit()
    before = dict(row.budget_used_json)
    login_as(client, "fixture-teacher", "pass")
    result = client.post(f"/courses/{course.id}/agent-tasks/{row.id}/resume",
                         json={"confirm_external_processing": True})
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    assert result.json()["error_code"] == "source_unavailable"
    assert result.json()["budget_used"] == before


def test_source_disabled_between_resume_and_run_stops_before_model(db, snapshot):
    course, row, doc, _ = snapshot
    investigation.run_investigation(db, row, course_title=course.title,
                                   replay_responses=evidence_replay(snapshot))
    row.status = "interrupted"
    db.commit()
    restart_task(db, row, operation="resume", checkpoint_safe=True)
    before = row.budget_used_json["model_calls"]
    doc.retrieval_enabled = False
    db.commit()
    investigation.run_investigation(db, row, course_title=course.title)
    assert row.status == "failed" and row.budget_used_json["model_calls"] == before


def test_crash_reservations_and_append_only_events_preserve_remaining_budget(db, snapshot, monkeypatch):
    course, row, *_ = snapshot
    original = investigation.ReplayActionSource.next_action

    def crash(self, **kwargs):
        raise SystemExit("PRIVATE crash sentinel")

    monkeypatch.setattr(investigation.ReplayActionSource, "next_action", crash)
    with pytest.raises(SystemExit):
        investigation.run_investigation(db, row, course_title=course.title)
    assert row.budget_used_json["model_calls"] == 1
    old_events = [(e.sequence, e.status, e.safe_summary) for e in db.scalars(select(AgentTaskEvent)).all()]
    expire(db, row)
    assert db.scalar(select(AgentTaskEvent).where(AgentTaskEvent.event_type == "step_failed"))
    restart_task(db, row, operation="resume", checkpoint_safe=True)
    monkeypatch.setattr(investigation.ReplayActionSource, "next_action", original)
    investigation.run_investigation(db, row, course_title=course.title)
    assert row.status == "succeeded" and row.budget_used_json["model_calls"] == 2
    current = db.scalars(select(AgentTaskEvent).order_by(AgentTaskEvent.sequence)).all()
    assert [(e.sequence, e.status, e.safe_summary) for e in current[:len(old_events)]] == old_events
    assert "PRIVATE" not in json.dumps([e.safe_summary for e in current])


def test_replay_mode_current_evidence_content_url_page(db, snapshot):
    course, row, doc, chunk = snapshot
    # The existing fixture's most recent in-window student is QUERY_IDS[4].
    query = db.get(QueryLog, UUID(int=104))
    query.query = "fixture-evidence"
    db.commit()
    investigation.run_investigation(db, row, course_title=course.title, mode="replay")
    result = investigation.read_report(db, row, retention_days=90)
    assert row.status == "succeeded"
    source = result.evidence_sources[0]
    assert source.document_id == doc.id and source.page == chunk.page == 3
    assert source.content_url == f"/courses/{course.id}/documents/{doc.id}/content"
