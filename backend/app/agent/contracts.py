from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from datetime import timedelta
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    TypeAdapter,
    ValidationError,
    model_validator,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvestigationFocus(StrEnum):
    all = "all"
    repeated_questions = "repeated_questions"
    no_evidence = "no_evidence"
    system_failures = "system_failures"


class TaskStatus(StrEnum):
    queued = "queued"
    running = "running"
    cancel_requested = "cancel_requested"
    interrupted = "interrupted"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    budget_exceeded = "budget_exceeded"


class StepStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class TraceEventType(StrEnum):
    task_created = "task_created"
    task_started = "task_started"
    step_started = "step_started"
    step_succeeded = "step_succeeded"
    step_failed = "step_failed"
    step_skipped = "step_skipped"
    model_action_received = "model_action_received"
    tool_started = "tool_started"
    tool_succeeded = "tool_succeeded"
    tool_failed = "tool_failed"
    checkpoint_saved = "checkpoint_saved"
    cancel_requested = "cancel_requested"
    task_interrupted = "task_interrupted"
    task_resumed = "task_resumed"
    task_terminal = "task_terminal"


class FindingCategory(StrEnum):
    repeated_question = "repeated_question"
    no_evidence = "no_evidence"
    system_failure = "system_failure"
    coverage_candidate = "coverage_candidate"
    retrieval_candidate = "retrieval_candidate"
    question_wording = "question_wording"
    normal_review = "normal_review"
    unknown = "unknown"


class CauseCode(StrEnum):
    coverage_gap = "coverage_gap"
    retrieval_citation = "retrieval_citation"
    question_wording = "question_wording"
    normal_review = "normal_review"
    undecidable = "undecidable"


class SuggestedActionCode(StrEnum):
    update_material = "update_material"
    clarify_in_class = "clarify_in_class"
    add_regression = "add_regression"
    no_action = "no_action"
    investigate_system = "investigate_system"


class InvestigationRequest(ContractModel):
    start_at: AwareDatetime
    end_at: AwareDatetime
    focus: InvestigationFocus = InvestigationFocus.all
    confirm_external_processing: StrictBool
    idempotency_key: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_window(self) -> InvestigationRequest:
        if self.start_at >= self.end_at:
            raise ValueError("start_at must be earlier than end_at")
        if self.end_at - self.start_at > timedelta(days=30):
            raise ValueError("investigation window must not exceed 30 days")
        return self


class EvidenceReference(ContractModel):
    chunk_id: UUID
    document_id: UUID
    page: int | None = Field(default=None, ge=1)
    claim_supported: str = Field(min_length=1, max_length=400)


class InvestigationFinding(ContractModel):
    category: FindingCategory
    description: str = Field(min_length=1, max_length=600)
    source_query_ids: list[UUID] = Field(default_factory=list, max_length=12)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def require_source(self) -> InvestigationFinding:
        if not self.source_query_ids and not self.evidence_chunk_ids:
            raise ValueError("finding must reference at least one source")
        return self


class CauseCandidate(ContractModel):
    cause_code: CauseCode
    explanation: str = Field(min_length=1, max_length=400)
    source_query_ids: list[UUID] = Field(default_factory=list, max_length=12)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def require_source(self) -> CauseCandidate:
        if not self.source_query_ids and not self.evidence_chunk_ids:
            raise ValueError("candidate cause must reference at least one source")
        return self


class SuggestedAction(ContractModel):
    action_code: SuggestedActionCode
    reason: str = Field(min_length=1, max_length=400)
    source_query_ids: list[UUID] = Field(default_factory=list, max_length=12)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def require_source(self) -> SuggestedAction:
        if not self.source_query_ids and not self.evidence_chunk_ids:
            raise ValueError("suggested action must reference at least one source")
        return self


class InvestigationReport(ContractModel):
    summary: str = Field(min_length=1, max_length=2000)
    findings: list[InvestigationFinding] = Field(default_factory=list, max_length=12)
    candidate_causes: list[CauseCandidate] = Field(default_factory=list, max_length=12)
    unknowns: list[str] = Field(default_factory=list, max_length=12)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list, max_length=8)
    source_query_ids: list[UUID] = Field(default_factory=list, max_length=30)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_unique_references(self) -> InvestigationReport:
        if len(self.source_query_ids) != len(set(self.source_query_ids)):
            raise ValueError("source_query_ids must be unique")
        chunk_ids = [item.chunk_id for item in self.evidence_refs]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("evidence_refs must not repeat chunk_id")
        return self


class QuestionSourceObservation(ContractModel):
    query_id: UUID
    query_text: str = Field(min_length=1, max_length=2000)
    outcome: Literal["cited_answer", "no_evidence", "failure", "unknown"]
    count: int = Field(ge=1)
    last_asked_at: AwareDatetime


class CourseQuestionSummary(ContractModel):
    recorded_attempts: int = Field(ge=0)
    student_attempts: int = Field(ge=0)
    cited_answer: int = Field(ge=0)
    no_evidence: int = Field(ge=0)
    failure: int = Field(ge=0)
    unknown_outcome: int = Field(ge=0)
    non_student_attempts: int = Field(ge=0)
    unknown_role_attempts: int = Field(ge=0)
    knowledge_attempts: int = Field(ge=0)
    distinct_student_questions: int = Field(ge=0)
    cited_answer_rate: float | None = Field(default=None, ge=0, le=1)
    no_evidence_rate: float | None = Field(default=None, ge=0, le=1)
    failure_rate: float | None = Field(default=None, ge=0, le=1)
    rate_denominator: Literal["student_attempts"] = "student_attempts"
    sample_limited: bool


class InitialInvestigationObservation(ContractModel):
    course_title: str = Field(min_length=1, max_length=200)
    window_start: AwareDatetime
    window_end: AwareDatetime
    focus: InvestigationFocus
    summary: CourseQuestionSummary
    question_sources: list[QuestionSourceObservation] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_window(self) -> InitialInvestigationObservation:
        if self.window_start >= self.window_end:
            raise ValueError("window_start must be earlier than window_end")
        if len({source.query_id for source in self.question_sources}) != len(self.question_sources):
            raise ValueError("question_sources must not repeat query_id")
        return self


class SearchHitObservation(ContractModel):
    chunk_id: UUID
    document_id: UUID
    page: int | None = Field(default=None, ge=1)
    snippet: str = Field(max_length=240)
    score: float = Field(ge=-1, le=1)


class SearchCourseEvidenceResult(ContractModel):
    hits: list[SearchHitObservation] = Field(default_factory=list, max_length=8)


class EvidenceDetailObservation(ContractModel):
    chunk_id: UUID
    document_id: UUID
    page: int | None = Field(default=None, ge=1)
    filename: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(max_length=800)
    quality_warning: str | None = Field(default=None, max_length=32)


class DocumentQualityObservation(ContractModel):
    document_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    job_status: Literal["pending", "running", "succeeded", "failed", "unknown"]
    quality_warning: str | None = Field(default=None, max_length=32)
    chunk_count: int | None = Field(default=None, ge=0)


class SearchCourseEvidenceAction(ContractModel):
    type: Literal["search_course_evidence"]
    query: str = Field(min_length=1, max_length=2000)


class OpenEvidenceAction(ContractModel):
    type: Literal["open_evidence"]
    chunk_id: UUID


class GetDocumentQualityAction(ContractModel):
    type: Literal["get_document_quality"]
    document_id: UUID


class FinishAction(ContractModel):
    type: Literal["finish"]
    report: InvestigationReport


type ActionDecision = Annotated[
    SearchCourseEvidenceAction
    | OpenEvidenceAction
    | GetDocumentQualityAction
    | FinishAction,
    Field(discriminator="type"),
]

_ACTION_ADAPTER = TypeAdapter(ActionDecision)
MAX_ACTION_OUTPUT_CHARS = 20_000


class InvalidActionOutput(ValueError):
    """Raised when a model action cannot be safely parsed and validated."""


def parse_action_decision(raw: str) -> ActionDecision:
    """Parse only a complete JSON action; never execute loosely extracted text."""
    if not raw or len(raw) > MAX_ACTION_OUTPUT_CHARS:
        raise InvalidActionOutput("action_output_size_invalid")
    try:
        return _ACTION_ADAPTER.validate_json(raw)
    except ValidationError:
        # Do not include the model's raw output in errors or logs.
        raise InvalidActionOutput("action_schema_invalid") from None


class InvalidReportReferences(ValueError):
    """Raised when a report references data outside the current task's evidence."""


def validate_report_references(
    report: InvestigationReport,
    *,
    allowed_query_ids: AbstractSet[UUID],
    evidence_by_chunk: Mapping[UUID, tuple[UUID, int | None]],
) -> None:
    """Validate source IDs against server-owned observations, not model assertions."""
    allowed_chunks = set(evidence_by_chunk)

    def check_query_ids(query_ids: list[UUID]) -> None:
        if not set(query_ids).issubset(allowed_query_ids):
            raise InvalidReportReferences("query_reference_not_allowed")

    def check_chunk_ids(chunk_ids: list[UUID]) -> None:
        if not set(chunk_ids).issubset(allowed_chunks):
            raise InvalidReportReferences("chunk_reference_not_allowed")

    check_query_ids(report.source_query_ids)
    for finding in report.findings:
        check_query_ids(finding.source_query_ids)
        check_chunk_ids(finding.evidence_chunk_ids)
    for cause in report.candidate_causes:
        check_query_ids(cause.source_query_ids)
        check_chunk_ids(cause.evidence_chunk_ids)
    for action in report.suggested_actions:
        check_query_ids(action.source_query_ids)
        check_chunk_ids(action.evidence_chunk_ids)

    for reference in report.evidence_refs:
        expected = evidence_by_chunk.get(reference.chunk_id)
        if expected is None:
            raise InvalidReportReferences("evidence_reference_not_allowed")
        expected_document_id, expected_page = expected
        if (
            reference.document_id != expected_document_id
            or reference.page != expected_page
        ):
            raise InvalidReportReferences("evidence_reference_mismatch")


class AgentBudget(ContractModel):
    max_steps: int = Field(default=8, ge=1, le=32)
    max_tool_calls: int = Field(default=6, ge=0, le=24)
    max_model_calls: int = Field(default=8, ge=1, le=32)
    max_runtime_seconds: int = Field(default=120, ge=1, le=600)
    max_evidence_refs: int = Field(default=12, ge=0, le=24)
    max_report_chars: int = Field(default=6000, ge=200, le=12000)


class ReportBudgetExceeded(ValueError):
    """Raised when a structured report exceeds the task's configured limits."""


def validate_report_budget(
    report: InvestigationReport, *, budget: AgentBudget
) -> None:
    """Enforce aggregate report limits after schema validation."""
    evidence_count = len(report.evidence_refs)
    if evidence_count > budget.max_evidence_refs:
        raise ReportBudgetExceeded("report_evidence_budget_exceeded")

    # §7 defines this budget narrowly as summary plus finding descriptions.
    text_parts = [report.summary]
    text_parts.extend(item.description for item in report.findings)
    if sum(len(part) for part in text_parts) > budget.max_report_chars:
        raise ReportBudgetExceeded("report_character_budget_exceeded")


class TraceEvent(ContractModel):
    sequence: int = Field(ge=1)
    event_type: TraceEventType
    step_no: int | None = Field(default=None, ge=1)
    tool_name: str | None = Field(default=None, max_length=64)
    status: TaskStatus | StepStatus | None = None
    safe_summary: str = Field(default="", max_length=500)
    evidence_refs: list[UUID] = Field(default_factory=list, max_length=12)
    error_code: str | None = Field(default=None, max_length=64)
    duration_ms: int | None = Field(default=None, ge=0)
    created_at: AwareDatetime


_TERMINAL_STATUSES = {
    TaskStatus.succeeded,
    TaskStatus.failed,
    TaskStatus.cancelled,
    TaskStatus.budget_exceeded,
}
_ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.queued: {
        TaskStatus.running,
        TaskStatus.cancelled,
        TaskStatus.budget_exceeded,
    },
    TaskStatus.running: {
        TaskStatus.succeeded,
        TaskStatus.failed,
        TaskStatus.cancel_requested,
        TaskStatus.cancelled,
        TaskStatus.interrupted,
        TaskStatus.budget_exceeded,
    },
    TaskStatus.cancel_requested: {TaskStatus.cancelled},
    TaskStatus.interrupted: {TaskStatus.queued, TaskStatus.failed, TaskStatus.cancelled},
    TaskStatus.failed: {TaskStatus.queued},
    TaskStatus.succeeded: set(),
    TaskStatus.cancelled: {TaskStatus.queued},
    TaskStatus.budget_exceeded: {TaskStatus.queued},
}


class InvalidTaskTransition(ValueError):
    """Raised when a task status transition is not permitted."""


_ALLOWED_STEP_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
    StepStatus.pending: {StepStatus.running, StepStatus.skipped},
    StepStatus.running: {StepStatus.succeeded, StepStatus.failed, StepStatus.skipped},
    StepStatus.succeeded: set(),
    StepStatus.failed: set(),
    StepStatus.skipped: set(),
}


class InvalidStepTransition(ValueError):
    """Raised when a step transition is not permitted."""


def validate_step_transition(current: StepStatus, target: StepStatus) -> None:
    """Steps are terminal once completed; retries create a new attempt/step."""
    if target not in _ALLOWED_STEP_TRANSITIONS[current]:
        raise InvalidStepTransition(f"step_transition_not_allowed:{current.value}:{target.value}")


def is_terminal_task_status(status: TaskStatus) -> bool:
    return status in _TERMINAL_STATUSES


def validate_task_transition(
    current: TaskStatus,
    target: TaskStatus,
    *,
    explicit_resume: bool = False,
    explicit_retry: bool = False,
) -> None:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidTaskTransition(f"transition_not_allowed:{current.value}:{target.value}")
    if current == TaskStatus.interrupted and target == TaskStatus.queued and not explicit_resume:
        raise InvalidTaskTransition("explicit_resume_required")
    if (
        current in {TaskStatus.failed, TaskStatus.cancelled, TaskStatus.budget_exceeded}
        and target == TaskStatus.queued
        and not explicit_retry
    ):
        raise InvalidTaskTransition("explicit_retry_required")

