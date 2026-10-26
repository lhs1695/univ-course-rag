"""Explicit Fake/Replay lifecycle. Every worker write is fenced in the database."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.models.agent_task import AgentTask, AgentTaskEvent
from app.services.agent_task_store import AgentTaskConflict, _normalize

LEASE_SECONDS = 15
COUNTERS = {"steps": "max_steps", "model_calls": "max_model_calls",
            "tool_calls": "max_tool_calls", "runtime_seconds": "max_runtime_seconds"}


class ExecutionRevoked(RuntimeError):
    """The worker no longer owns the task; it must perform no further writes."""


def _change(db, row, predicates, values, *, event_type=None, summary=None):
    now = datetime.now(UTC)
    result = db.execute(update(AgentTask).where(
        AgentTask.id == row.id, *predicates,
    ).values(**values, updated_at=now,
             last_event_sequence=AgentTask.last_event_sequence + (1 if event_type else 0)),
        execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        db.rollback()
        db.refresh(row)
        return False
    db.refresh(row)
    if event_type:
        db.add(AgentTaskEvent(
            task_id=row.id, sequence=row.last_event_sequence, attempt=row.attempt,
            event_type=event_type, status=row.status, safe_summary=summary,
            error_code=row.error_code, evidence_refs_json=[], created_at=now,
        ))
    return True


def has_budget(row):
    return all(row.budget_used_json.get(k, 0) < row.budget_json[limit]
               for k, limit in COUNTERS.items())


def cancel_task(db, row):
    # Predicate and update serialize against finish, including a concurrent cancel.
    for state in ("queued", "interrupted", "running"):
        target = "cancel_requested" if state == "running" else "cancelled"
        if _change(db, row, [AgentTask.status == state], {
            "status": target, "cancel_requested_at": datetime.now(UTC),
            **({"run_token": None, "lease_expires_at": None,
                "finished_at": datetime.now(UTC)} if target == "cancelled" else {}),
        }, event_type=target, summary="Cancellation requested by teacher"):
            db.commit()
            return


def interrupt_stale(db, row, *, now=None):
    current = now or datetime.now(UTC)
    db.refresh(row)
    _normalize(row)
    usage = dict(row.budget_used_json)
    if row.lease_expires_at and row.status in {"running", "cancel_requested"}:
        # Charge the unreported execution interval up to lease expiry; waiting
        # after expiry and time spent interrupted do not consume runtime.
        usage["runtime_seconds"] += max(0, (
            min(current, row.lease_expires_at) - row.updated_at
        ).total_seconds())
    for state in ("cancel_requested", "running"):
        target = "cancelled" if state == "cancel_requested" else "interrupted"
        if _change(db, row, [AgentTask.status == state,
                             AgentTask.last_event_sequence == row.last_event_sequence,
                             AgentTask.lease_expires_at <= current], {
            "status": target, "run_token": None, "lease_expires_at": None,
            "error_code": "agent_lease_expired", "finished_at": current,
            "budget_used_json": usage,
        }, event_type="lease_expired", summary="Lease expired; execution revoked"):
            # Close any persisted running steps without reopening old steps.
            events = db.scalars(select(AgentTaskEvent).where(
                AgentTaskEvent.task_id == row.id, AgentTaskEvent.attempt == row.attempt,
            ).order_by(AgentTaskEvent.sequence)).all()
            pending = {}
            for e in events:
                if e.event_type == "step_started":
                    pending[e.step_no] = e
                elif e.event_type in {"step_succeeded", "step_failed", "step_skipped"}:
                    pending.pop(e.step_no, None)
            for step in pending:
                row.last_event_sequence += 1
                db.add(AgentTaskEvent(
                    task_id=row.id, sequence=row.last_event_sequence, attempt=row.attempt,
                    step_no=step, event_type="step_failed", status="failed",
                    error_code="agent_lease_expired", safe_summary="Step interrupted",
                    evidence_refs_json=[], created_at=current,
                ))
            db.commit()
            return True
    return False


def start_task(db, row):
    now = datetime.now(UTC)
    code = next((f"agent_{name.removesuffix('_calls')}_budget_exceeded"
                 for name, limit in COUNTERS.items()
                 if row.budget_used_json.get(name, 0) >= row.budget_json[limit]), None)
    if not has_budget(row) and _change(db, row, [AgentTask.status == "queued"], {
            "status": "budget_exceeded", "error_code": code,
            "finished_at": now,
    }, event_type="task_terminal", summary="Cumulative budget exhausted"):
        db.commit()
        return False
    claimed = _change(db, row, [AgentTask.status == "queued"], {
        "status": "running", "run_token": uuid4(),
        "lease_expires_at": now + timedelta(seconds=LEASE_SECONDS),
        "started_at": now, "finished_at": None,
        "checkpoint_json": {"version": 1, "safe_boundary": True,
                            "source_query_ids": [], "evidence_metadata": {},
                            **(row.checkpoint_json or {})},
    }, event_type="task_started", summary="Fake replay started")
    if claimed:
        db.commit()
    return claimed


def worker_predicates(token):
    return [AgentTask.run_token == token, AgentTask.status.in_(["running", "cancel_requested"]),
            AgentTask.lease_expires_at > datetime.now(UTC)]


def progress_task(db, row, token, *, usage, snapshot, event=None):
    values = {"budget_used_json": usage, "checkpoint_json": snapshot,
              "lease_expires_at": datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)}
    if not _change(db, row, worker_predicates(token), values):
        raise ExecutionRevoked
    if event:
        row.last_event_sequence += 1
        db.add(AgentTaskEvent(
            task_id=row.id, sequence=row.last_event_sequence, attempt=row.attempt,
            step_no=event.step_no, event_type=event.event_type.value,
            tool_name=event.tool_name, status=event.status.value if event.status else "running",
            safe_summary=event.safe_summary, error_code=event.error_code,
            evidence_refs_json=[str(i) for i in event.evidence_refs],
            duration_ms=event.duration_ms, created_at=event.created_at,
        ))
    db.commit()


def cancellation_requested(db, row, token):
    db.refresh(row)
    if row.run_token != token or row.lease_expires_at is None or (
        _normalize(row).lease_expires_at <= datetime.now(UTC)
    ):
        raise ExecutionRevoked
    return row.status == "cancel_requested"


def finish_task(db, row, token, result, *, snapshot):
    # Cancel CAS first, then success CAS. A cancel arriving between the two wins
    # because the success predicate only accepts running.
    for state in ("cancel_requested", "running"):
        status = "cancelled" if state == "cancel_requested" else result.status.value
        report = result.report if status == "succeeded" else None
        if _change(db, row, [*worker_predicates(token), AgentTask.status == state], {
            "status": status, "error_code": None if status == "cancelled" else result.error_code,
            "report_json": report.model_dump(mode="json") if report else None,
            "checkpoint_json": snapshot, "run_token": None, "lease_expires_at": None,
            "finished_at": datetime.now(UTC),
        }, event_type="task_terminal", summary="Investigation ended"):
            db.commit()
            _normalize(row)
            return True
    # A cancel may have arrived after the first predicate was checked.
    db.refresh(row)
    if (row.status == "cancel_requested" and row.run_token == token
            and row.lease_expires_at is not None
            and _normalize(row).lease_expires_at > datetime.now(UTC)):
        return finish_task(db, row, token, result, snapshot=snapshot)
    return False


def restart_task(db, row, *, operation, checkpoint_safe, checkpoint_error="investigation_checkpoint_unsafe"):
    states = ["interrupted"] if operation == "resume" else ["failed", "cancelled", "budget_exceeded"]
    db.refresh(row)
    if row.status not in states:
        raise AgentTaskConflict(f"investigation_not_{operation}able")
    target, code = "queued", None
    if not has_budget(row):
        target, code = "budget_exceeded", "agent_budget_exhausted"
    elif operation == "resume" and not checkpoint_safe:
        target, code = "failed", checkpoint_error
    try:
        changed = _change(db, row, [AgentTask.status.in_(states), AgentTask.attempt == row.attempt], {
            "status": target, "error_code": code,
            "attempt": AgentTask.attempt + (1 if target == "queued" else 0),
            "run_token": None, "lease_expires_at": None, "cancel_requested_at": None,
            "finished_at": None if target == "queued" else datetime.now(UTC), "report_json": None,
            "confirm_external_processing": True,
            "checkpoint_json": {**(row.checkpoint_json or {}), "restart_operation": operation},
        }, event_type=f"task_{operation}", summary="Explicit teacher restart checked")
        if not changed:
            raise AgentTaskConflict(f"investigation_not_{operation}able")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AgentTaskConflict("active_investigation_conflict") from None
    _normalize(row)
    if operation == "retry" and code == "agent_budget_exhausted":
        raise AgentTaskConflict(code)
