"""M2 bounded Fake/Replay investigation. No provider factory is invoked here."""

from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agent.contracts import (
    AgentBudget,
    CauseCandidate,
    CourseQuestionSummary,
    DocumentQualityObservation,
    EvidenceDetailObservation,
    EvidenceReference,
    FinishAction,
    InitialInvestigationObservation,
    InvalidReportReferences,
    InvestigationFinding,
    InvestigationReport,
    QuestionSourceObservation,
    SearchCourseEvidenceAction,
    SearchCourseEvidenceResult,
    SearchHitObservation,
    SuggestedAction,
    TaskStatus,
    TraceEvent,
    validate_report_references,
)
from app.agent.replay_harness import (
    ReplayActionSource,
    ReplayResult,
    ReplayTools,
    run_replay,
)
from app.config import Settings
from app.models import Chunk, Document, QueryLog
from app.models.agent_task import AgentTask
from app.models.course import CourseMember, CourseMemberRole
from app.services.agent_task_runtime import (
    ExecutionRevoked,
    cancellation_requested,
    finish_task,
    progress_task,
    start_task,
)
from app.services.insights import aggregate_course_insights, normalize_query


def external_processing_required(settings: Settings) -> bool:
    # Grouping can build the configured embedder, even when LLM is Fake.
    return settings.llm_backend != "fake" or settings.embedder_backend != "fake"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def build_initial_observation(
    db: Session, row: AgentTask, *, course_title: str, retention_days: int,
) -> InitialInvestigationObservation:
    start = max(_utc(row.window_start), datetime.now(UTC) - timedelta(days=retention_days))
    end = _utc(row.window_end)
    if start >= end:
        raise ValueError("investigation_window_expired")
    summary = aggregate_course_insights(
        db, row.course_id, window_start=start, window_end=end,
    )["summary"]
    # Bounded resolver: IDs belong to the authorized window. Never select user_id.
    sources = db.execute(select(
        QueryLog.id, QueryLog.query, QueryLog.outcome, QueryLog.created_at,
    ).where(
        QueryLog.course_id == row.course_id, QueryLog.created_at >= start,
        QueryLog.created_at < end, QueryLog.member_role_at_ask == "student",
        or_(QueryLog.error_code.is_(None),
            QueryLog.error_code.not_in(["NEEDS_CONTEXT", "INVALID_QUESTION"])),
    ).order_by(QueryLog.created_at.desc(), QueryLog.id).limit(30)).all()
    return InitialInvestigationObservation(
        course_title=course_title, window_start=start, window_end=end, focus=row.focus,
        summary=summary,
        question_sources=[QuestionSourceObservation(
            query_id=qid, query_text=text[:2000] or "[empty question]",
            outcome=outcome if outcome in {"cited_answer", "no_evidence", "failure"} else "unknown",
            count=1, last_asked_at=_utc(created_at),
        ) for qid, text, outcome, created_at in sources],
    )


def fake_report(observation: InitialInvestigationObservation) -> InvestigationReport:
    """Conservative observations only; Fake does not infer teaching/material defects."""
    sources = observation.question_sources
    summary = observation.summary
    findings, causes, actions = [], [], []
    if sources:
        for outcome, category, description in (
            ("no_evidence", "no_evidence", "Sampled attempts recorded no_evidence; this does not establish missing course material."),
            ("failure", "system_failure", "Sampled attempts recorded system failures; operational review is needed, with no teaching inference."),
        ):
            ids = [s.query_id for s in sources if s.outcome == outcome][:12]
            selected = observation.focus in {"all", "no_evidence" if outcome == "no_evidence" else "system_failures"}
            if ids and selected:
                findings.append(InvestigationFinding(
                    category=category, description=description, source_query_ids=ids,
                ))
                if outcome == "no_evidence":
                    causes.append(CauseCandidate(
                        cause_code="undecidable", explanation="Cause remains unknown; material coverage and retrieval require separate verification.",
                        source_query_ids=ids,
                    ))
                actions.append(SuggestedAction(
                    action_code="investigate_system" if outcome == "failure" else "add_regression",
                    reason="Review these sampled attempts before deciding on any course changes.",
                    source_query_ids=ids,
                ))
        counts = Counter(normalize_query(s.query_text) for s in sources
                         if s.outcome in {"cited_answer", "no_evidence"})
        repeated = [s.query_id for s in sources
                    if s.outcome in {"cited_answer", "no_evidence"}
                    and counts[normalize_query(s.query_text)] > 1][:12]
        if repeated and observation.focus in {"all", "repeated_questions"}:
            findings.append(InvestigationFinding(
                category="repeated_question", source_query_ids=repeated,
                description="Normalized question text repeats within the bounded sample; repetition alone does not establish a knowledge gap.",
            ))
    return InvestigationReport(
        summary=(f"Window {observation.window_start.isoformat()} to {observation.window_end.isoformat()}; "
                 f"recorded_attempts={summary.recorded_attempts}, student_attempts={summary.student_attempts}, "
                 f"sample_count={len(sources)}. Fake observation report; causes require verification."),
        findings=findings, candidate_causes=causes, suggested_actions=actions,
        source_query_ids=[s.query_id for s in sources],
        unknowns=["No authorized question data is available; no findings or causes can be inferred."
                  if not sources else
                  "At most 30 recent student attempts are sampled. Logs do not preserve final answers or citation snapshots; teaching quality and material coverage remain unknown."],
    )


def _fake_tools(db: Session, row: AgentTask) -> ReplayTools:
    def document(document_id):
        doc = db.scalar(select(Document).where(
            Document.id == document_id, Document.course_id == row.course_id,
            Document.retrieval_enabled.is_(True),
        ))
        if doc is None:
            raise InvalidReportReferences("source_unavailable")
        return doc

    def chunk(chunk_id):
        item = db.scalar(select(Chunk).join(Document, Chunk.document_id == Document.id).where(
            Chunk.id == chunk_id, Chunk.course_id == row.course_id,
            Document.course_id == row.course_id, Document.retrieval_enabled.is_(True),
        ))
        if item is None:
            raise InvalidReportReferences("source_unavailable")
        return item

    def search(query):
        # Explicit Fake literal lookup, not a replacement for production retrieval.
        items = db.scalars(select(Chunk).join(Document, Chunk.document_id == Document.id).where(
            Chunk.course_id == row.course_id, Document.course_id == row.course_id,
            Document.retrieval_enabled.is_(True), Chunk.text.contains(query, autoescape=True),
        ).order_by(Chunk.id).limit(8)).all()
        return SearchCourseEvidenceResult(hits=[SearchHitObservation(
            chunk_id=c.id, document_id=c.document_id, page=c.page, snippet=c.text[:240], score=1,
        ) for c in items])

    def open_evidence(chunk_id):
        c = chunk(chunk_id)
        doc = document(c.document_id)
        return EvidenceDetailObservation(
            chunk_id=c.id, document_id=doc.id, page=c.page, filename=doc.filename,
            excerpt=c.text[:800], quality_warning=doc.quality_warning,
        )

    def quality(document_id):
        doc = document(document_id)
        return DocumentQualityObservation(
            document_id=doc.id, filename=doc.filename, job_status="unknown",
            quality_warning=doc.quality_warning, chunk_count=doc.chunk_count,
        )

    return ReplayTools(search, open_evidence, quality)


def _evidence_metadata(db: Session, row: AgentTask, ids: set[UUID]) -> dict:
    # Project metadata only: unavailable evidence text is never selected or parsed.
    return {cid: (did, page) for cid, did, page in db.execute(select(
        Chunk.id, Document.id, Chunk.page,
    ).join(Document, Chunk.document_id == Document.id).where(
        Chunk.id.in_(ids), Chunk.course_id == row.course_id,
        Document.course_id == row.course_id, Document.retrieval_enabled.is_(True),
    ))}


def _query_metadata(db: Session, row: AgentTask, ids: set[UUID], retention_days: int) -> dict:
    return {qid: outcome if outcome in {"cited_answer", "no_evidence", "failure"} else "unknown"
            for qid, outcome in db.execute(select(QueryLog.id, QueryLog.outcome).where(
                QueryLog.id.in_(ids), QueryLog.course_id == row.course_id,
                QueryLog.member_role_at_ask == "student",
                QueryLog.created_at >= max(_utc(row.window_start), datetime.now(UTC) - timedelta(days=retention_days)),
                QueryLog.created_at < _utc(row.window_end),
                or_(QueryLog.error_code.is_(None),
                    QueryLog.error_code.not_in(["NEEDS_CONTEXT", "INVALID_QUESTION"])),
            ))}


def checkpoint_is_safe(db: Session, row: AgentTask, *, retention_days: int) -> bool:
    """Metadata-only resume validation; never restore source text from a snapshot."""
    snapshot = row.checkpoint_json or {}
    if snapshot.get("version") != 1 or snapshot.get("safe_boundary") is not True:
        return False
    try:
        queries = {UUID(q) for q in snapshot.get("source_query_ids", [])}
        evidence = {UUID(k): (UUID(v["document_id"]), v["page"])
                    for k, v in snapshot.get("evidence_metadata", {}).items()}
        return (set(_query_metadata(db, row, queries, retention_days)) == queries
                and _evidence_metadata(db, row, set(evidence)) == evidence)
    except (ValueError, KeyError, TypeError):
        return False


def run_investigation(
    db: Session, row: AgentTask, *, course_title: str, retention_days: int = 90,
    replay_responses: list[str] | None = None,
    mode: str = "fake",
    actor_id: UUID | None = None,
) -> bool:
    """Explicit synchronous Fake/Replay only, including when confirmation=True."""
    if not start_task(db, row):
        return False
    token = row.run_token
    previous = dict(row.budget_used_json)
    limits = dict(row.budget_json)
    started = monotonic()
    snapshot = dict(row.checkpoint_json)
    result = ReplayResult(
        status=TaskStatus.failed, report=None, trace=(), steps=0, model_calls=0, tool_calls=0,
        error_code="investigation_execution_failed",
    )
    try:
        def boundary():
            cancelled = cancellation_requested(db, row, token)
            if cancelled:
                return True
            membership = db.scalar(select(CourseMember.id).where(
                CourseMember.course_id == row.course_id,
                CourseMember.user_id == (actor_id or row.created_by),
                CourseMember.role == CourseMemberRole.teacher,
            ))
            if membership is None:
                raise InvalidReportReferences("source_unavailable")
            return False

        if boundary():
            finish_task(db, row, token, replace(result, status=TaskStatus.cancelled), snapshot=snapshot)
            return True
        if snapshot.get("restart_operation") == "resume" and not checkpoint_is_safe(
            db, row, retention_days=retention_days,
        ):
            raise InvalidReportReferences("source_unavailable")
        observation = build_initial_observation(
            db, row, course_title=course_title, retention_days=retention_days,
        )
        snapshot = {
            "version": 1, "safe_boundary": True,
            "summary": observation.summary.model_dump(mode="json"),
            "sample_count": len(observation.question_sources),
            "source_query_ids": [str(s.query_id) for s in observation.question_sources],
            "mode": "fake_replay", "similar_groups": "N/A: semantic grouping is not run in M2",
        }
        allowed = {s.query_id for s in observation.question_sources}
        observed_evidence = {}
        tools = _fake_tools(db, row)

        def search(query):
            result = tools.search_course_evidence(query)
            observed_evidence.update({h.chunk_id: (h.document_id, h.page) for h in result.hits})
            snapshot["evidence_metadata"] = {
                str(cid): {"document_id": str(did), "page": page}
                for cid, (did, page) in observed_evidence.items()
            }
            return result

        def persist(event, counts):
            if event and event.event_type in {"task_created", "task_started", "task_terminal"}:
                return
            usage = {**previous, **{k: previous.get(k, 0) + v for k, v in counts.items()}}
            progress_task(db, row, token, usage=usage, snapshot=snapshot, event=event)

        # Re-observe only read-only state with the cumulative remaining budget.
        # model_copy permits a positive fractional remaining runtime internally.
        remaining = AgentBudget.model_validate(limits).model_copy(update={
            limit: limits[limit] - previous.get(counter, 0)
            for counter, limit in {"steps": "max_steps", "tool_calls": "max_tool_calls",
                                   "model_calls": "max_model_calls",
                                   "runtime_seconds": "max_runtime_seconds"}.items()
        })
        progress_task(db, row, token, usage=previous, snapshot=snapshot)

        responses = replay_responses if replay_responses is not None else [
            FinishAction(type="finish", report=fake_report(observation)).model_dump_json(),
        ]
        source = ReplayActionSource(responses)
        if mode == "replay" and observation.question_sources and replay_responses is None:
            class CurrentEvidenceReplay:
                searched = False

                def next_action(self, *, validation_error=None):
                    if not self.searched:
                        self.searched = True
                        return SearchCourseEvidenceAction(
                            type="search_course_evidence",
                            query=observation.question_sources[0].query_text,
                        ).model_dump_json()
                    report = fake_report(observation)
                    if observed_evidence:
                        cid, (did, page) = next(iter(observed_evidence.items()))
                        report.evidence_refs = [EvidenceReference(
                            chunk_id=cid, document_id=did, page=page,
                            claim_supported="The sampled question text has a literal match in current authorized material; this does not verify a historical answer.",
                        )]
                        report.findings.append(InvestigationFinding(
                            category="normal_review", evidence_chunk_ids=[cid],
                            source_query_ids=[observation.question_sources[0].query_id],
                            description="A literal match was found in current material; material completeness and answer correctness remain unverified.",
                        ))
                    return FinishAction(type="finish", report=report).model_dump_json()

            source = CurrentEvidenceReplay()
        first_clock_read = True

        def execution_clock():
            nonlocal first_clock_read
            if first_clock_read:
                first_clock_read = False
                return started
            return monotonic()

        result = run_replay(
            action_source=source,
            tools=ReplayTools(search, tools.open_evidence, tools.get_document_quality),
            allowed_query_ids=allowed, budget=remaining,
            monotonic_clock=execution_clock,
            cancel_requested=boundary, progress=persist,
        )
        if result.report is not None and boundary():
            result = replace(result, status=TaskStatus.cancelled, report=None)
        if result.report is not None:
            # Recheck live metadata before committing, using only this task's tool observations.
            current = _evidence_metadata(db, row, set(observed_evidence))
            validate_report_references(result.report,
                                       allowed_query_ids=set(_query_metadata(db, row, allowed, retention_days)),
                                       evidence_by_chunk={k: v for k, v in current.items()
                                                          if observed_evidence[k] == v})
            report_text = [result.report.summary, *result.report.unknowns,
                           *(f.description for f in result.report.findings),
                           *(c.explanation for c in result.report.candidate_causes),
                           *(a.reason for a in result.report.suggested_actions),
                           *(r.claim_supported for r in result.report.evidence_refs)]
            if any(s.query_text in text for s in observation.question_sources for text in report_text):
                raise InvalidReportReferences("report_contains_question_text")
            snapshot["evidence_metadata"] = {
                str(cid): {"document_id": str(did), "page": page}
                for cid, (did, page) in observed_evidence.items()
            }
    except ExecutionRevoked:
        db.rollback()
        db.refresh(row)
        return False
    except Exception as exc:  # noqa: BLE001 - persist a safe terminal state at the execution boundary
        # No exception text, raw responses, question text or evidence is persisted.
        db.rollback()
        code = "report_reference_validation_failed" if isinstance(exc, InvalidReportReferences) else "investigation_execution_failed"
        result = replace(result, status=TaskStatus.failed, report=None, error_code=code,
                         trace=tuple(e for e in result.trace if e.event_type != "task_terminal"))
    runtime = monotonic() - started
    # A legal finish may complete at the limit; post-validation/persistence time
    # must not turn that success into a spurious runtime failure (§7).
    if runtime + previous["runtime_seconds"] > limits["max_runtime_seconds"] and result.status != TaskStatus.succeeded:
        result = replace(result, status=TaskStatus.budget_exceeded, report=None,
                         error_code="agent_runtime_budget_exceeded",
                         trace=tuple(e for e in result.trace if e.event_type != "task_terminal"))
    result = replace(result, runtime_seconds=runtime)
    # Post-replay failures also get an explicit safe terminal event.
    if not result.trace or result.trace[-1].status != result.status:
        result = replace(result, trace=(*result.trace, TraceEvent(
            sequence=len(result.trace) + 1, event_type="task_terminal", status=result.status,
            error_code=result.error_code, safe_summary="Investigation ended", created_at=datetime.now(UTC),
        )))
    try:
        # Counts are already durable, including failures interrupted inside a call.
        usage = dict(row.budget_used_json)
        usage["runtime_seconds"] = previous["runtime_seconds"] + runtime
        usage["evidence_refs"] = len(result.report.evidence_refs) if result.report else 0
        usage["report_chars"] = (len(result.report.summary) + sum(
            len(f.description) for f in result.report.findings)) if result.report else 0
        progress_task(db, row, token, usage=usage, snapshot=snapshot)
        return finish_task(db, row, token, result, snapshot=snapshot)
    except ExecutionRevoked:
        return False


class QuerySourceOut(BaseModel):
    query_id: UUID
    available: bool
    outcome: str | None = None


class EvidenceSourceOut(BaseModel):
    chunk_id: UUID
    document_id: UUID
    page: int | None
    available: bool
    content_url: str | None = None


class InvestigationReportOut(BaseModel):
    task_id: UUID
    status: TaskStatus
    error_code: str | None
    report: InvestigationReport | None
    sample_count: int
    summary: CourseQuestionSummary | None
    sources: list[QuerySourceOut]
    evidence_sources: list[EvidenceSourceOut]


def read_report(db: Session, row: AgentTask, *, retention_days: int) -> InvestigationReportOut:
    snapshot = row.checkpoint_json or {}
    report = InvestigationReport.model_validate(row.report_json) if row.report_json else None
    query_ids, chunk_ids = set(), set()
    expected_evidence = {
        UUID(cid): (UUID(meta["document_id"]), meta["page"])
        for cid, meta in snapshot.get("evidence_metadata", {}).items()
    }
    if report:
        query_ids.update(report.source_query_ids)
        chunk_ids.update(r.chunk_id for r in report.evidence_refs)
        expected_evidence.update({r.chunk_id: (r.document_id, r.page) for r in report.evidence_refs})
        for item in [*report.findings, *report.candidate_causes, *report.suggested_actions]:
            query_ids.update(item.source_query_ids)
            chunk_ids.update(item.evidence_chunk_ids)
    # Metadata-only projection deliberately excludes QueryLog.query / Chunk.text.
    available_queries = _query_metadata(db, row, query_ids, retention_days)
    available_chunks = _evidence_metadata(db, row, chunk_ids)
    if report:
        # Evidence metadata must still match the originally validated document/page.
        for cid in chunk_ids:
            if available_chunks.get(cid) != expected_evidence.get(cid):
                available_chunks.pop(cid, None)
        def supported(item):
            return (set(item.source_query_ids).issubset(available_queries)
                    and set(item.evidence_chunk_ids).issubset(available_chunks))

        if query_ids - available_queries.keys() or chunk_ids - available_chunks.keys():
            report = report.model_copy(deep=True)
            report.summary = "Source availability has changed; the original summary is no longer verifiable."
            report.findings = [f for f in report.findings if supported(f)]
            report.candidate_causes = [c for c in report.candidate_causes if supported(c)]
            report.suggested_actions = [a for a in report.suggested_actions if supported(a)]
            report.source_query_ids = [q for q in report.source_query_ids if q in available_queries]
            report.evidence_refs = [r for r in report.evidence_refs if r.chunk_id in available_chunks]
            report.unknowns = ["Some sources are unavailable; dependent conclusions have been withheld."]
    return InvestigationReportOut(
        task_id=row.id, status=row.status, error_code=row.error_code, report=report,
        sample_count=snapshot.get("sample_count", 0), summary=snapshot.get("summary"),
        sources=[QuerySourceOut(query_id=qid, available=qid in available_queries,
                                outcome=available_queries.get(qid)) for qid in sorted(query_ids)],
        evidence_sources=[EvidenceSourceOut(
            chunk_id=cid, document_id=did, page=page, available=cid in available_chunks,
            content_url=f"/courses/{row.course_id}/documents/{did}/content" if cid in available_chunks else None,
        ) for cid, (did, page) in sorted(expected_evidence.items()) if cid in chunk_ids],
    )
