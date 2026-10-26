"""Deterministic, in-memory Agent harness for contract tests.

This module deliberately has no database, network, model-provider, or application
route integration. Production execution and persistence belong to PLAN-15/16.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol
from uuid import UUID

from app.agent.contracts import (
    ActionDecision,
    AgentBudget,
    DocumentQualityObservation,
    EvidenceDetailObservation,
    FinishAction,
    GetDocumentQualityAction,
    InvalidActionOutput,
    InvalidReportReferences,
    InvestigationReport,
    OpenEvidenceAction,
    ReportBudgetExceeded,
    SearchCourseEvidenceAction,
    SearchCourseEvidenceResult,
    StepStatus,
    TaskStatus,
    TraceEvent,
    TraceEventType,
    is_terminal_task_status,
    parse_action_decision,
    validate_report_budget,
    validate_report_references,
    validate_step_transition,
    validate_task_transition,
)


class ReplayExhausted(RuntimeError):
    """Raised when a replay contains no response for the next model call."""


class RecoverableToolError(RuntimeError):
    """Injected allowlisted transient tool failure eligible for one retry."""


class _RetryBudgetExceeded(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _RetryCancelled(RuntimeError):
    """Internal signal that cancellation won before a tool retry."""


class ActionSource(Protocol):
    def next_action(self, *, validation_error: str | None = None) -> str: ...


@dataclass
class ReplayActionSource:
    """Return recorded model outputs in order; never calls a real model."""

    responses: Sequence[str]
    feedback_codes: list[str | None] = field(default_factory=list)
    _index: int = 0

    def next_action(self, *, validation_error: str | None = None) -> str:
        self.feedback_codes.append(validation_error)
        if self._index >= len(self.responses):
            raise ReplayExhausted("replay_exhausted")
        response = self.responses[self._index]
        self._index += 1
        return response


@dataclass(frozen=True)
class ReplayTools:
    """Injected tool functions. Each function must enforce its own server scope."""

    search_course_evidence: Callable[[str], SearchCourseEvidenceResult]
    open_evidence: Callable[[UUID], EvidenceDetailObservation]
    get_document_quality: Callable[[UUID], DocumentQualityObservation]


@dataclass(frozen=True)
class ReplayResult:
    status: TaskStatus
    report: InvestigationReport | None
    trace: tuple[TraceEvent, ...]
    steps: int
    model_calls: int
    tool_calls: int
    runtime_seconds: float = 0.0
    error_code: str | None = None


def run_replay(
    *,
    action_source: ActionSource,
    tools: ReplayTools,
    allowed_query_ids: AbstractSet[UUID],
    budget: AgentBudget | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    now: Callable[[], datetime] | None = None,
    monotonic_clock: Callable[[], float] = monotonic,
    progress: Callable[[TraceEvent | None, dict], None] | None = None,
) -> ReplayResult:
    """Run a bounded, deterministic tool/action replay against contract checks.

    Only IDs returned by the initial observation or an earlier search result may
    be used by later actions. Trace summaries are fixed safe labels; raw actions,
    queries, snippets, excerpts, and exception messages are never copied to Trace.
    """
    active_budget = budget or AgentBudget()
    current_time = now or (lambda: datetime.now(UTC))
    is_cancel_requested = cancel_requested or (lambda: False)
    started_at = monotonic_clock()
    status = TaskStatus.queued
    step_status = StepStatus.pending
    trace: list[TraceEvent] = []
    report: InvestigationReport | None = None
    error_code: str | None = None
    steps = 0
    model_calls = 0
    tool_calls = 0
    schema_corrections = 0
    retried_tool_errors: set[tuple[str, str]] = set()
    evidence_by_chunk: dict[UUID, tuple[UUID, int | None]] = {}
    known_documents: set[UUID] = set()

    def persist(event=None):
        if progress is not None:
            progress(event, {"steps": steps, "model_calls": model_calls,
                             "tool_calls": tool_calls,
                             "runtime_seconds": max(0.0, monotonic_clock() - started_at)})

    def event(
        event_type: TraceEventType,
        *,
        event_status: TaskStatus | StepStatus | None = None,
        step_no: int | None = None,
        tool_name: str | None = None,
        summary: str = "",
        evidence_refs: Sequence[UUID] = (),
        event_error: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        trace.append(TraceEvent(
            sequence=len(trace) + 1,
            event_type=event_type,
            step_no=step_no,
            tool_name=tool_name,
            status=event_status,
            safe_summary=summary,
            evidence_refs=list(evidence_refs),
            error_code=event_error,
            duration_ms=duration_ms,
            created_at=current_time(),
        ))
        persist(trace[-1])

    def transition_step(target: StepStatus, *, error: str | None = None) -> None:
        nonlocal step_status
        validate_step_transition(step_status, target)
        step_status = target
        event_type = {
            StepStatus.running: TraceEventType.step_started,
            StepStatus.succeeded: TraceEventType.step_succeeded,
            StepStatus.failed: TraceEventType.step_failed,
            StepStatus.skipped: TraceEventType.step_skipped,
        }[target]
        event(
            event_type,
            event_status=target,
            step_no=steps,
            summary=f"step {steps} {target.value}",
            event_error=error,
        )

    def transition(target: TaskStatus, *, error: str | None = None) -> None:
        nonlocal status, error_code
        validate_task_transition(status, target)
        status = target
        error_code = error
        if is_terminal_task_status(target):
            event(
                TraceEventType.task_terminal,
                event_status=target,
                summary=f"task ended: {target.value}",
                event_error=error,
            )

    def terminate(target: TaskStatus, code: str | None = None) -> ReplayResult:
        if step_status is StepStatus.running:
            if target is TaskStatus.cancelled:
                transition_step(StepStatus.skipped, error=code)
            elif target in {TaskStatus.failed, TaskStatus.budget_exceeded}:
                transition_step(StepStatus.failed, error=code)
        transition(target, error=code)
        return result()

    def result() -> ReplayResult:
        return ReplayResult(
            status=status,
            report=report,
            trace=tuple(trace),
            steps=steps,
            model_calls=model_calls,
            tool_calls=tool_calls,
            runtime_seconds=max(0.0, monotonic_clock() - started_at),
            error_code=error_code,
        )

    def budget_exhausted() -> bool:
        return monotonic_clock() - started_at >= active_budget.max_runtime_seconds

    def request_cancel_if_needed() -> ReplayResult | None:
        if not is_cancel_requested():
            return None
        transition(TaskStatus.cancel_requested)
        event(
            TraceEventType.cancel_requested,
            event_status=TaskStatus.cancel_requested,
            summary="cancellation observed at safe boundary",
        )
        return terminate(TaskStatus.cancelled)

    def invoke_tool_with_one_retry(
        tool_name: str, function: Callable[..., object], *args: object
    ) -> object:
        """Retry only an explicitly classified transient error, within budgets."""
        nonlocal tool_calls
        try:
            return function(*args)
        except (RecoverableToolError, TimeoutError) as exc:
            retry_duration = max(0, int((monotonic_clock() - tool_started) * 1000))
            retry_key = (tool_name, type(exc).__name__)
            retry_already_used = retry_key in retried_tool_errors
            event(
                TraceEventType.tool_failed,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name=tool_name,
                summary=f"tool transient failure: {tool_name}",
                event_error=(
                    "tool_execution_retry_exhausted"
                    if retry_already_used
                    else "tool_execution_retryable"
                ),
                duration_ms=retry_duration,
            )
            if retry_already_used:
                raise
            cancelled = request_cancel_if_needed()
            if cancelled is not None:
                raise _RetryCancelled from None
            if budget_exhausted():
                raise _RetryBudgetExceeded("agent_runtime_budget_exceeded") from None
            if tool_calls >= active_budget.max_tool_calls:
                raise _RetryBudgetExceeded("agent_tool_budget_exceeded") from None
            retried_tool_errors.add(retry_key)
            tool_calls += 1
            event(
                TraceEventType.tool_started,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name=tool_name,
                summary=f"tool retry started: {tool_name}",
            )
            return function(*args)

    event(TraceEventType.task_created, event_status=TaskStatus.queued, summary="task created")
    transition(TaskStatus.running)
    event(TraceEventType.task_started, event_status=TaskStatus.running, summary="task started")

    while True:
        cancelled = request_cancel_if_needed()
        if cancelled is not None:
            return cancelled
        if steps >= active_budget.max_steps or budget_exhausted():
            return terminate(TaskStatus.budget_exceeded, "agent_step_or_runtime_budget_exceeded")
        if model_calls >= active_budget.max_model_calls:
            return terminate(TaskStatus.budget_exceeded, "agent_model_or_runtime_budget_exceeded")

        steps += 1
        step_status = StepStatus.pending
        transition_step(StepStatus.running)
        action: ActionDecision | None = None
        validation_feedback: str | None = None

        # One schema-correction retry is allowed across the task; it consumes a
        # model call, but not a second logical decision step.
        for attempt in range(2):
            cancelled = request_cancel_if_needed()
            if cancelled is not None:
                return cancelled
            if model_calls >= active_budget.max_model_calls or budget_exhausted():
                return terminate(TaskStatus.budget_exceeded, "agent_model_or_runtime_budget_exceeded")
            model_calls += 1
            persist()  # Reserve before invoking the action source, including failed calls.
            try:
                raw_action = action_source.next_action(validation_error=validation_feedback)
            except ReplayExhausted:
                return terminate(TaskStatus.failed, "replay_exhausted")
            except TimeoutError:  # Deterministic injected timeout; real adapters need finite timeouts.
                cancelled = request_cancel_if_needed()
                if cancelled is not None:
                    return cancelled
                if budget_exhausted():
                    return terminate(TaskStatus.budget_exceeded, "agent_runtime_budget_exceeded")
                return terminate(TaskStatus.failed, "action_source_timeout")
            except Exception:  # noqa: BLE001 - provider errors must not leak into task output.
                return terminate(TaskStatus.failed, "action_source_failed")

            try:
                action = parse_action_decision(raw_action)
            except InvalidActionOutput:
                event(
                    TraceEventType.model_action_received,
                    event_status=TaskStatus.running,
                    step_no=steps,
                    summary="invalid action rejected",
                    event_error="action_schema_invalid",
                )
                if attempt == 0 and schema_corrections == 0:
                    schema_corrections += 1
                    validation_feedback = "action_schema_invalid"
                    continue
                return terminate(TaskStatus.failed, "action_schema_invalid")

            event(
                TraceEventType.model_action_received,
                event_status=TaskStatus.running,
                step_no=steps,
                summary=f"validated action: {action.type}",
            )
            break

        if action is None:
            return terminate(TaskStatus.failed, "action_schema_invalid")

        cancelled = request_cancel_if_needed()
        if cancelled is not None:
            return cancelled
        # A valid finish returned exactly at the runtime boundary may commit;
        # other actions must leave positive runtime for another operation.
        if isinstance(action, FinishAction):
            if monotonic_clock() - started_at > active_budget.max_runtime_seconds:
                return terminate(TaskStatus.budget_exceeded, "agent_runtime_budget_exceeded")
        elif budget_exhausted():
            return terminate(TaskStatus.budget_exceeded, "agent_runtime_budget_exceeded")

        if isinstance(action, FinishAction):
            if tool_calls >= active_budget.max_tool_calls:
                return terminate(TaskStatus.budget_exceeded, "agent_tool_budget_exceeded")
            tool_calls += 1
            event(
                TraceEventType.tool_started,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name="finish",
                summary="tool started: finish",
            )
            try:
                validate_report_references(
                    action.report,
                    allowed_query_ids=allowed_query_ids,
                    evidence_by_chunk=evidence_by_chunk,
                )
                validate_report_budget(action.report, budget=active_budget)
            except InvalidReportReferences as exc:
                event(
                    TraceEventType.tool_failed,
                    event_status=TaskStatus.running,
                    step_no=steps,
                    tool_name="finish",
                    summary="tool failed: finish",
                    event_error=str(exc),
                )
                return terminate(TaskStatus.failed, str(exc))
            except ReportBudgetExceeded as exc:
                event(
                    TraceEventType.tool_failed,
                    event_status=TaskStatus.running,
                    step_no=steps,
                    tool_name="finish",
                    summary="tool failed: finish",
                    event_error=str(exc),
                )
                return terminate(TaskStatus.budget_exceeded, str(exc))
            except ValueError as exc:
                event(
                    TraceEventType.tool_failed,
                    event_status=TaskStatus.running,
                    step_no=steps,
                    tool_name="finish",
                    summary="tool failed: finish",
                    event_error=str(exc),
                )
                return terminate(TaskStatus.failed, str(exc))
            report = action.report
            event(
                TraceEventType.tool_succeeded,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name="finish",
                summary="tool succeeded: finish",
                evidence_refs=[item.chunk_id for item in report.evidence_refs],
            )
            transition_step(StepStatus.succeeded)
            return terminate(TaskStatus.succeeded)

        if tool_calls >= active_budget.max_tool_calls:
            return terminate(TaskStatus.budget_exceeded, "agent_tool_budget_exceeded")

        if isinstance(action, OpenEvidenceAction) and action.chunk_id not in evidence_by_chunk:
            return terminate(TaskStatus.failed, "chunk_reference_not_allowed")
        if isinstance(action, GetDocumentQualityAction) and action.document_id not in known_documents:
            return terminate(TaskStatus.failed, "document_reference_not_allowed")

        tool_name = action.type
        tool_calls += 1
        tool_started = monotonic_clock()
        event(
            TraceEventType.tool_started,
            event_status=TaskStatus.running,
            step_no=steps,
            tool_name=tool_name,
            summary=f"tool started: {tool_name}",
        )

        try:
            if isinstance(action, SearchCourseEvidenceAction):
                tool_result = SearchCourseEvidenceResult.model_validate(
                    invoke_tool_with_one_retry(
                        tool_name, tools.search_course_evidence, action.query
                    )
                )
                new_evidence = dict(evidence_by_chunk)
                new_documents = set(known_documents)
                for hit in tool_result.hits:
                    previous = new_evidence.get(hit.chunk_id)
                    reference = (hit.document_id, hit.page)
                    if previous is not None and previous != reference:
                        raise ValueError("search_result_conflict")
                    new_evidence[hit.chunk_id] = reference
                    new_documents.add(hit.document_id)
                if len(new_evidence) > active_budget.max_evidence_refs:
                    event(
                        TraceEventType.tool_succeeded,
                        event_status=TaskStatus.running,
                        step_no=steps,
                        tool_name=tool_name,
                        summary="search completed; evidence withheld by budget",
                        duration_ms=max(0, int((monotonic_clock() - tool_started) * 1000)),
                    )
                    return terminate(TaskStatus.budget_exceeded, "agent_evidence_budget_exceeded")
                evidence_by_chunk = new_evidence
                known_documents = new_documents
                result_evidence = [hit.chunk_id for hit in tool_result.hits]
            elif isinstance(action, OpenEvidenceAction):
                tool_result = EvidenceDetailObservation.model_validate(
                    invoke_tool_with_one_retry(tool_name, tools.open_evidence, action.chunk_id)
                )
                expected = evidence_by_chunk[action.chunk_id]
                if (
                    tool_result.chunk_id != action.chunk_id
                    or (tool_result.document_id, tool_result.page) != expected
                ):
                    raise ValueError("evidence_reference_mismatch")
                result_evidence = [action.chunk_id]
            elif isinstance(action, GetDocumentQualityAction):
                tool_result = DocumentQualityObservation.model_validate(
                    invoke_tool_with_one_retry(
                        tool_name, tools.get_document_quality, action.document_id
                    )
                )
                if tool_result.document_id != action.document_id:
                    raise ValueError("document_reference_mismatch")
                result_evidence = []
            else:  # The discriminated schema should make this unreachable.
                return terminate(TaskStatus.failed, "action_not_allowed")
        except _RetryCancelled:
            return result()
        except _RetryBudgetExceeded as exc:
            return terminate(TaskStatus.budget_exceeded, exc.code)
        except ValueError as exc:
            code = str(exc)
            if code not in {
                "search_result_conflict",
                "evidence_reference_mismatch",
                "document_reference_mismatch",
            }:
                code = "tool_result_schema_invalid"
            event(
                TraceEventType.tool_failed,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name=tool_name,
                summary=f"tool failed: {tool_name}",
                event_error=code,
                duration_ms=max(0, int((monotonic_clock() - tool_started) * 1000)),
            )
            return terminate(TaskStatus.failed, code)
        except TimeoutError:
            cancelled = request_cancel_if_needed()
            if cancelled is not None:
                return cancelled
            timed_out = budget_exhausted()
            code = "agent_runtime_budget_exceeded" if timed_out else "tool_execution_timeout"
            terminal = TaskStatus.budget_exceeded if timed_out else TaskStatus.failed
            event(
                TraceEventType.tool_failed,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name=tool_name,
                summary=f"tool timed out: {tool_name}",
                event_error=code,
                duration_ms=max(0, int((monotonic_clock() - tool_started) * 1000)),
            )
            return terminate(terminal, code)
        except Exception:  # noqa: BLE001 - tool errors must be sanitized at this boundary.
            event(
                TraceEventType.tool_failed,
                event_status=TaskStatus.running,
                step_no=steps,
                tool_name=tool_name,
                summary=f"tool failed: {tool_name}",
                event_error="tool_execution_failed",
                duration_ms=max(0, int((monotonic_clock() - tool_started) * 1000)),
            )
            return terminate(TaskStatus.failed, "tool_execution_failed")

        event(
            TraceEventType.tool_succeeded,
            event_status=TaskStatus.running,
            step_no=steps,
            tool_name=tool_name,
            summary=f"tool succeeded: {tool_name}",
            evidence_refs=result_evidence,
            duration_ms=max(0, int((monotonic_clock() - tool_started) * 1000)),
        )
        transition_step(StepStatus.succeeded)
        cancelled = request_cancel_if_needed()
        if cancelled is not None:
            return cancelled
        if budget_exhausted():
            return terminate(TaskStatus.budget_exceeded, "agent_runtime_budget_exceeded")
