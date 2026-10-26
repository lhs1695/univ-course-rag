import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.agent.contracts import (
    EvidenceReference,
    FinishAction,
    InvestigationFinding,
    InvestigationReport,
    InvestigationRequest,
    OpenEvidenceAction,
    SearchCourseEvidenceAction,
)
from app.models import AgentTask, AgentTaskEvent, Chunk, Document, QueryLog
from app.models.course import CourseMemberRole
from app.models.user import UserRole
from app.services import agent_investigation, agent_task_store
from app.services.agent_investigation import read_report, run_investigation
from app.services.agent_task_store import create_task
from sqlalchemy import event, select

from tests.conftest import TestingSessionLocal, add_user
from tests.test_courses import add_course, add_member

FIXTURE_VERSION = "e5a-m2-v1"
FIXED_NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
START = datetime(2026, 10, 24, tzinfo=UTC)
END = datetime(2026, 10, 25, tzinfo=UTC)
QUERY_IDS = [UUID(int=100 + i) for i in range(5)]


@pytest.fixture
def snapshot(db, monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FIXED_NOW if tz else FIXED_NOW.replace(tzinfo=None)

    monkeypatch.setattr(agent_investigation, "datetime", FrozenDatetime)
    monkeypatch.setattr(agent_task_store, "datetime", FrozenDatetime)
    teacher = add_user(db, "fixture-teacher", "pass", UserRole.teacher)
    course = add_course(db, "E5-A fixed snapshot v1")
    course.id = UUID(int=10)
    db.commit()
    add_member(db, course, teacher, CourseMemberRole.teacher)
    other = add_course(db, "Not authorized")
    other.id = UUID(int=11)
    db.commit()
    doc = Document(id=UUID(int=20), course_id=course.id, uploaded_by=teacher.id,
                   filename="fixture.pdf", storage_path="never-open-fixture.pdf",
                   retrieval_enabled=True, chunk_count=1)
    chunk = Chunk(id=UUID(int=30), course_id=course.id, document_id=doc.id,
                  page=3, text="fixture-evidence: definition is documented", embedding=[],
                  embedding_model="fake-fixture")
    db.add_all([doc, chunk])
    db.flush()
    for i, (text, outcome) in enumerate([
        ("Explain the fixed definition", "cited_answer"),
        ("Explain the fixed definition", "cited_answer"),
        ("Compare the fixed cases", "no_evidence"),
        ("Compare the fixed cases", "no_evidence"),
        ("Why did my request time out", "failure"),
    ]):
        db.add(QueryLog(id=QUERY_IDS[i], course_id=course.id, user_id=teacher.id,
                        query=text, hit=outcome == "cited_answer", outcome=outcome,
                        member_role_at_ask="student", error_code=None, chunk_ids="[]",
                        duration_ms=10, created_at=START + timedelta(hours=i + 1)))
    # Excluded course, window, and non-student role can never become report sources.
    for cid, role, when in [(other.id, "student", START), (course.id, "student", END),
                            (course.id, "teacher", START)]:
        db.add(QueryLog(course_id=cid, user_id=teacher.id, query="OUT-OF-SCOPE-SENTINEL",
                        hit=False, outcome="failure", member_role_at_ask=role,
                        chunk_ids="[]", duration_ms=1, created_at=when))
    db.commit()
    row = create_task(db, InvestigationRequest(
        start_at=START, end_at=END, confirm_external_processing=False,
        idempotency_key="fixed-e5a-investigation-v1",
    ), course_id=course.id, created_by=teacher.id, now=FIXED_NOW)
    return course, row, doc, chunk


def evidence_report(snapshot):
    _, _, doc, chunk = snapshot
    return InvestigationReport(
        summary="A current document contains the fixed fixture definition; this is not a historical answer audit.",
        findings=[InvestigationFinding(
            category="normal_review", description="The current document contains the fixture definition.",
            source_query_ids=[QUERY_IDS[0]], evidence_chunk_ids=[chunk.id],
        )],
        source_query_ids=[QUERY_IDS[0]],
        evidence_refs=[EvidenceReference(chunk_id=chunk.id, document_id=doc.id, page=3,
                                        claim_supported="Current fixture definition is documented.")],
        unknowns=["Historical final answers and citation snapshots were not recorded."],
    )


def evidence_replay(snapshot, report=None):
    *_, chunk = snapshot
    return [
        SearchCourseEvidenceAction(type="search_course_evidence", query="fixture-evidence").model_dump_json(),
        OpenEvidenceAction(type="open_evidence", chunk_id=chunk.id).model_dump_json(),
        FinishAction(type="finish", report=report or evidence_report(snapshot)).model_dump_json(),
    ]


def test_runner_persists_validated_report_usage_and_safe_trace(db, snapshot):
    course, row, _, _ = snapshot
    assert run_investigation(db, row, course_title=course.title)
    assert row.status == "succeeded"
    assert row.budget_used_json["model_calls"] == row.budget_used_json["tool_calls"] == 1
    assert row.budget_used_json["steps"] == 1
    assert row.finished_at is not None
    serialized = json.dumps([row.report_json, row.checkpoint_json], ensure_ascii=False)
    assert "Explain the fixed definition" not in serialized
    assert "OUT-OF-SCOPE-SENTINEL" not in serialized
    assert set(row.report_json["source_query_ids"]) == {str(q) for q in QUERY_IDS}
    events = db.scalars(select(AgentTaskEvent)).all()
    assert all("fixed definition" not in (e.safe_summary or "") for e in events)
    count = len(events)
    assert not run_investigation(db, row, course_title=course.title)
    assert len(db.scalars(select(AgentTaskEvent)).all()) == count
    with TestingSessionLocal() as reader:
        persisted = reader.get(AgentTask, row.id)
        assert persisted.report_json == row.report_json


@pytest.mark.parametrize("fault,expected", [
    ("forged_query", "query_reference_not_allowed"),
    ("unobserved_chunk", "chunk_reference_not_allowed"),
    ("invalid_action", "action_schema_invalid"),
    ("exhausted", "replay_exhausted"),
])
def test_runner_rejects_invalid_replay_with_terminal_safe_error(db, snapshot, fault, expected):
    course, row, _, chunk = snapshot
    report = InvestigationReport(summary="Only a replay fixture.")
    responses = []
    if fault == "forged_query":
        report.source_query_ids = [uuid4()]
    elif fault == "unobserved_chunk":
        report.findings = [InvestigationFinding(category="unknown", description="Not observed",
                                                evidence_chunk_ids=[chunk.id])]
    elif fault == "invalid_action":
        responses = ['{"type":"execute_sql","sql":"PRIVATE-SENTINEL"}'] * 2
    if fault in {"forged_query", "unobserved_chunk"}:
        responses = [FinishAction(type="finish", report=report).model_dump_json()]
    assert run_investigation(db, row, course_title=course.title, replay_responses=responses)
    assert row.status == "failed" and row.report_json is None
    assert row.error_code == expected
    assert "PRIVATE-SENTINEL" not in repr(db.scalars(select(AgentTaskEvent)).all())
    assert db.scalars(select(AgentTaskEvent).order_by(AgentTaskEvent.sequence)).all()[-1].status == "failed"


def test_post_validation_rejects_raw_question_copy_without_losing_call_counts(db, snapshot):
    course, row, _, _ = snapshot
    report = InvestigationReport(summary="Explain the fixed definition", source_query_ids=[QUERY_IDS[0]])
    run_investigation(db, row, course_title=course.title, replay_responses=[
        FinishAction(type="finish", report=report).model_dump_json(),
    ])
    assert row.status == "failed" and row.report_json is None
    assert row.error_code == "report_reference_validation_failed"
    assert row.budget_used_json["model_calls"] == row.budget_used_json["tool_calls"] == 1
    terminals = db.scalars(select(AgentTaskEvent).where(AgentTaskEvent.event_type == "task_terminal")).all()
    assert len(terminals) == 1 and terminals[0].status == "failed"


def test_raw_question_with_json_escaping_is_also_rejected(db, snapshot):
    course, row, _, _ = snapshot
    query = db.get(QueryLog, QUERY_IDS[0])
    query.query = 'Private "quoted" question\nwith another line'
    db.commit()
    report = InvestigationReport(summary=f"Observed: {query.query}", source_query_ids=[query.id])
    run_investigation(db, row, course_title=course.title, replay_responses=[
        FinishAction(type="finish", report=report).model_dump_json(),
    ])
    assert row.status == "failed" and row.report_json is None


def test_live_source_is_revalidated_after_replay_before_commit(db, snapshot, monkeypatch):
    course, row, doc, _ = snapshot
    original_tools = agent_investigation._fake_tools

    def tools_with_source_removed(session, task):
        tools = original_tools(session, task)

        def open_then_disable(chunk_id):
            result = tools.open_evidence(chunk_id)
            doc.retrieval_enabled = False
            db.commit()
            return result

        return agent_investigation.ReplayTools(
            tools.search_course_evidence, open_then_disable, tools.get_document_quality,
        )

    monkeypatch.setattr(agent_investigation, "_fake_tools", tools_with_source_removed)
    run_investigation(db, row, course_title=course.title, replay_responses=evidence_replay(snapshot))
    assert row.status == "failed" and row.report_json is None
    assert row.error_code == "report_reference_validation_failed"
    assert row.budget_used_json["model_calls"] == row.budget_used_json["tool_calls"] == 3


@pytest.mark.parametrize("mutation", ["delete_query", "expire_query", "wrong_course_query",
                                     "delete_chunk", "disable_document", "delete_document",
                                     "wrong_course_chunk", "wrong_course_document"])
def test_h12_source_read_metadata_only_and_withholds_unsupported_conclusions(
    db, snapshot, mutation,
):
    course, row, doc, chunk = snapshot
    run_investigation(db, row, course_title=course.title, replay_responses=evidence_replay(snapshot))
    assert row.status == "succeeded"
    query = db.get(QueryLog, QUERY_IDS[0])
    if mutation == "delete_query":
        db.delete(query)
    elif mutation == "expire_query":
        query.created_at = FIXED_NOW - timedelta(days=91)
    elif mutation == "wrong_course_query":
        query.course_id = UUID(int=11)
    elif mutation == "delete_chunk":
        db.delete(chunk)
    elif mutation == "disable_document":
        doc.retrieval_enabled = False
    elif mutation == "delete_document":
        db.delete(doc)
    elif mutation == "wrong_course_chunk":
        chunk.course_id = UUID(int=11)
    else:
        doc.course_id = UUID(int=11)
    db.commit()
    statements = []

    def capture(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement)

    event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        body = read_report(db, row, retention_days=90)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", capture)
    assert any(not s.available for s in [*body.sources, *body.evidence_sources])
    assert body.report.findings == []
    assert "no longer verifiable" in body.report.summary
    assert body.report.unknowns
    assert "excerpt" not in body.model_dump_json() and "query_text" not in body.model_dump_json()
    assert all("query_logs.query" not in sql and "chunks.text" not in sql for sql in statements)
    assert row.report_json["findings"]  # response redaction does not rewrite the original snapshot


def test_runner_tools_do_not_open_cross_course_or_disabled_evidence(db, snapshot):
    course, row, doc, _ = snapshot
    doc.retrieval_enabled = False
    db.commit()
    run_investigation(db, row, course_title=course.title, replay_responses=evidence_replay(snapshot))
    assert row.status == "failed" and row.report_json is None


def test_observation_exception_becomes_safe_terminal_failure(db, snapshot, monkeypatch):
    course, row, _, _ = snapshot

    def broken(*_args, **_kwargs):
        raise RuntimeError("PRIVATE question or provider detail")

    monkeypatch.setattr(agent_investigation, "build_initial_observation", broken)
    run_investigation(db, row, course_title=course.title)
    assert row.status == "failed" and row.error_code == "investigation_execution_failed"
    assert row.finished_at is not None and row.report_json is None
    assert "PRIVATE" not in json.dumps(row.checkpoint_json)


def test_initial_observation_runtime_consumes_budget_before_first_action(db, snapshot, monkeypatch):
    course, row, _, _ = snapshot
    times = iter([0.0, 2.0])
    monkeypatch.setattr(agent_investigation, "monotonic", lambda: next(times, 2.0))
    row.budget_json = {**row.budget_json, "max_runtime_seconds": 1}
    db.commit()
    run_investigation(db, row, course_title=course.title)
    assert row.status == "budget_exceeded" and row.error_code == "agent_runtime_budget_exceeded"
    assert row.budget_used_json["model_calls"] == row.budget_used_json["tool_calls"] == 0
    assert row.budget_used_json["runtime_seconds"] == 2.0


@pytest.mark.parametrize("focus,expected", [
    ("repeated_questions", {"repeated_question"}), ("no_evidence", {"no_evidence"}),
    ("system_failures", {"system_failure"}),
])
def test_focus_limits_findings_without_changing_statistical_denominator(db, snapshot, focus, expected):
    course, row, _, _ = snapshot
    row.focus = focus
    db.commit()
    run_investigation(db, row, course_title=course.title)
    assert row.status == "succeeded"
    assert {f["category"] for f in row.report_json["findings"]} == expected
    assert row.checkpoint_json["summary"]["student_attempts"] == 5


def test_observation_is_bounded_and_summary_keeps_full_denominator(db, snapshot):
    course, row, _, _ = snapshot
    template = db.get(QueryLog, QUERY_IDS[0])
    for i in range(35):
        db.add(QueryLog(course_id=course.id, user_id=template.user_id,
                        query=f"Extra fixture question {i}", hit=True, outcome="cited_answer",
                        member_role_at_ask="student", chunk_ids="[]", duration_ms=1,
                        created_at=START + timedelta(hours=12, minutes=i)))
    db.commit()
    run_investigation(db, row, course_title=course.title)
    assert row.status == "succeeded"
    assert row.checkpoint_json["sample_count"] == len(row.report_json["source_query_ids"]) == 30
    assert row.checkpoint_json["summary"]["student_attempts"] == 40
    assert "At most 30" in row.report_json["unknowns"][0]
