from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.agent.contracts import (
    AgentBudget,
    CauseCandidate,
    EvidenceReference,
    FindingCategory,
    FinishAction,
    InvalidActionOutput,
    InvalidReportReferences,
    InvalidStepTransition,
    InvalidTaskTransition,
    InvestigationFinding,
    InvestigationReport,
    InvestigationRequest,
    ReportBudgetExceeded,
    SearchCourseEvidenceAction,
    StepStatus,
    SuggestedAction,
    SuggestedActionCode,
    TaskStatus,
    is_terminal_task_status,
    parse_action_decision,
    validate_report_budget,
    validate_report_references,
    validate_step_transition,
    validate_task_transition,
)
from pydantic import ValidationError


def test_parse_action_decision_accepts_only_valid_discriminated_json():
    action = parse_action_decision(
        '{"type":"search_course_evidence","query":"线性代数的向量定义"}'
    )
    assert isinstance(action, SearchCourseEvidenceAction)
    assert action.query == "线性代数的向量定义"

    with pytest.raises(InvalidActionOutput, match="action_schema_invalid"):
        parse_action_decision('{"type":"run_sql","query":"select * from users"}')
    with pytest.raises(InvalidActionOutput, match="action_schema_invalid"):
        parse_action_decision(
            '{"type":"search_course_evidence","query":"向量","course_id":"anything"}'
        )
    with pytest.raises(InvalidActionOutput, match="action_schema_invalid"):
        parse_action_decision("not json")
    with pytest.raises(InvalidActionOutput, match="action_output_size_invalid"):
        parse_action_decision("x" * 20_001)


def test_investigation_request_requires_aware_valid_window_and_explicit_consent_field():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = start + timedelta(days=7)
    request = InvestigationRequest.model_validate({
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "focus": "no_evidence",
        "confirm_external_processing": False,
        "idempotency_key": "request-12345678",
    })
    assert request.focus.value == "no_evidence"
    assert request.confirm_external_processing is False

    with pytest.raises(ValidationError):
        InvestigationRequest.model_validate({
            "start_at": start.isoformat(),
            "end_at": start.isoformat(),
            "confirm_external_processing": True,
            "idempotency_key": "request-12345678",
        })
    with pytest.raises(ValidationError):
        InvestigationRequest.model_validate({
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=31)).isoformat(),
            "confirm_external_processing": True,
            "idempotency_key": "request-12345678",
        })
    with pytest.raises(ValidationError):
        InvestigationRequest.model_validate({
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "idempotency_key": "request-12345678",
        })


def make_report(query_id, chunk_id, document_id, page=3):
    return InvestigationReport(
        summary="课程内重复问句需要教师核查。",
        findings=[InvestigationFinding(
            category=FindingCategory.no_evidence,
            description="依据不足线索重复出现。",
            source_query_ids=[query_id],
            evidence_chunk_ids=[chunk_id],
        )],
        candidate_causes=[CauseCandidate(
            cause_code="coverage_gap",
            explanation="当前资料证据可能未覆盖该问题。",
            source_query_ids=[query_id],
            evidence_chunk_ids=[chunk_id],
        )],
        unknowns=["当前日志不能证明历史回答正文是否正确。"],
        suggested_actions=[SuggestedAction(
            action_code=SuggestedActionCode.investigate_system,
            reason="先检查检索和资料覆盖。",
            source_query_ids=[query_id],
        )],
        source_query_ids=[query_id],
        evidence_refs=[EvidenceReference(
            chunk_id=chunk_id,
            document_id=document_id,
            page=page,
            claim_supported="该来源可作为待核查的课程证据。",
        )],
    )


def test_report_references_must_match_server_authorized_observations():
    query_id, chunk_id, document_id = uuid4(), uuid4(), uuid4()
    report = make_report(query_id, chunk_id, document_id)
    validate_report_references(
        report,
        allowed_query_ids={query_id},
        evidence_by_chunk={chunk_id: (document_id, 3)},
    )

    with pytest.raises(InvalidReportReferences, match="query_reference_not_allowed"):
        validate_report_references(
            report,
            allowed_query_ids=set(),
            evidence_by_chunk={chunk_id: (document_id, 3)},
        )

    with pytest.raises(InvalidReportReferences, match="evidence_reference_mismatch"):
        validate_report_references(
            report,
            allowed_query_ids={query_id},
            evidence_by_chunk={chunk_id: (uuid4(), 3)},
        )

    with pytest.raises(InvalidReportReferences, match="chunk_reference_not_allowed"):
        invalid_report = make_report(query_id, uuid4(), document_id)
        validate_report_references(
            invalid_report,
            allowed_query_ids={query_id},
            evidence_by_chunk={chunk_id: (document_id, 3)},
        )


def test_budget_has_bounded_defaults_and_rejects_unbounded_values():
    budget = AgentBudget()
    assert budget.max_steps == 8
    assert budget.max_tool_calls == 6
    assert budget.max_model_calls == 8
    assert budget.max_runtime_seconds == 120
    with pytest.raises(ValidationError):
        AgentBudget(max_steps=10_000)
    with pytest.raises(ValidationError):
        AgentBudget(max_runtime_seconds=10_000)


def test_report_budget_enforces_aggregate_text_and_evidence_limits():
    query_id, chunk_id, document_id = uuid4(), uuid4(), uuid4()
    report = make_report(query_id, chunk_id, document_id)
    validate_report_budget(report, budget=AgentBudget())

    with pytest.raises(ReportBudgetExceeded, match="report_evidence_budget_exceeded"):
        validate_report_budget(report, budget=AgentBudget(max_evidence_refs=0))

    long_report = report.model_copy(update={"summary": "x" * 250})
    with pytest.raises(ReportBudgetExceeded, match="report_character_budget_exceeded"):
        validate_report_budget(long_report, budget=AgentBudget(max_report_chars=200))


def test_report_character_budget_counts_only_summary_and_finding_descriptions():
    query_id, chunk_id, document_id = uuid4(), uuid4(), uuid4()
    report = make_report(query_id, chunk_id, document_id).model_copy(update={
        "unknowns": ["u" * 1000],
        "candidate_causes": [],
        "suggested_actions": [],
        "evidence_refs": [EvidenceReference(
            chunk_id=chunk_id,
            document_id=document_id,
            page=3,
            claim_supported="e" * 400,
        )],
    })
    validate_report_budget(report, budget=AgentBudget(max_report_chars=200))

    over_limit = report.model_copy(update={
        "summary": "s" * 150,
        "findings": [InvestigationFinding(
            category=FindingCategory.no_evidence,
            description="d" * 60,
            source_query_ids=[query_id],
        )],
    })
    with pytest.raises(ReportBudgetExceeded, match="report_character_budget_exceeded"):
        validate_report_budget(over_limit, budget=AgentBudget(max_report_chars=200))


def test_task_transitions_require_explicit_resume_and_retry():
    validate_task_transition(TaskStatus.queued, TaskStatus.running)
    validate_task_transition(TaskStatus.running, TaskStatus.succeeded)
    validate_task_transition(TaskStatus.running, TaskStatus.cancel_requested)
    validate_task_transition(TaskStatus.cancel_requested, TaskStatus.cancelled)
    validate_task_transition(TaskStatus.running, TaskStatus.interrupted)
    validate_task_transition(TaskStatus.running, TaskStatus.budget_exceeded)
    validate_task_transition(TaskStatus.running, TaskStatus.cancelled)
    validate_task_transition(TaskStatus.queued, TaskStatus.budget_exceeded)
    validate_task_transition(TaskStatus.interrupted, TaskStatus.cancelled)
    validate_task_transition(
        TaskStatus.interrupted, TaskStatus.queued, explicit_resume=True
    )
    validate_task_transition(TaskStatus.failed, TaskStatus.queued, explicit_retry=True)
    validate_task_transition(TaskStatus.cancelled, TaskStatus.queued, explicit_retry=True)
    validate_task_transition(TaskStatus.budget_exceeded, TaskStatus.queued, explicit_retry=True)

    with pytest.raises(InvalidTaskTransition, match="explicit_resume_required"):
        validate_task_transition(TaskStatus.interrupted, TaskStatus.queued)
    with pytest.raises(InvalidTaskTransition, match="explicit_retry_required"):
        validate_task_transition(TaskStatus.failed, TaskStatus.queued)
    with pytest.raises(InvalidTaskTransition, match="explicit_retry_required"):
        validate_task_transition(TaskStatus.cancelled, TaskStatus.queued)
    with pytest.raises(InvalidTaskTransition, match="explicit_retry_required"):
        validate_task_transition(TaskStatus.budget_exceeded, TaskStatus.queued)
    with pytest.raises(InvalidTaskTransition, match="transition_not_allowed"):
        validate_task_transition(TaskStatus.succeeded, TaskStatus.running)
    with pytest.raises(InvalidTaskTransition, match="transition_not_allowed"):
        validate_task_transition(TaskStatus.cancel_requested, TaskStatus.failed)

    assert is_terminal_task_status(TaskStatus.succeeded)
    assert is_terminal_task_status(TaskStatus.failed)
    assert not is_terminal_task_status(TaskStatus.running)


def test_step_transitions_are_terminal_and_retries_need_new_steps():
    validate_step_transition(StepStatus.pending, StepStatus.running)
    validate_step_transition(StepStatus.running, StepStatus.succeeded)
    validate_step_transition(StepStatus.running, StepStatus.failed)
    validate_step_transition(StepStatus.pending, StepStatus.skipped)

    with pytest.raises(InvalidStepTransition, match="step_transition_not_allowed"):
        validate_step_transition(StepStatus.succeeded, StepStatus.running)
    with pytest.raises(InvalidStepTransition, match="step_transition_not_allowed"):
        validate_step_transition(StepStatus.failed, StepStatus.running)


def test_finish_action_validates_nested_report_schema():
    query_id, chunk_id, document_id = uuid4(), uuid4(), uuid4()
    report = make_report(query_id, chunk_id, document_id)
    parsed = parse_action_decision(FinishAction(type="finish", report=report).model_dump_json())
    assert isinstance(parsed, FinishAction)
    assert parsed.report.source_query_ids == [query_id]

