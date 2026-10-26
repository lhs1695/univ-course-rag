"""E5-A v1: fixed developer oracle; Fake control evidence, not model quality."""

import json

from app.agent.contracts import InvestigationReport, validate_report_references
from app.services.agent_investigation import (
    build_initial_observation,
    fake_report,
    read_report,
    run_investigation,
)
from app.services.insights import aggregate_course_insights

from tests.test_agent_investigation_runner import (
    END,
    FIXTURE_VERSION,
    QUERY_IDS,
    START,
    evidence_replay,
    evidence_report,
)
from tests.test_agent_investigation_runner import (
    snapshot as fixed_snapshot,
)

snapshot = fixed_snapshot


def test_e5a_fixed_snapshot_a_b_c_all_contract_92_gates(db, snapshot):
    course, task, doc, chunk = snapshot
    # A uses the existing independent statistical/list baseline for the same scope.
    baseline_a = aggregate_course_insights(db, course.id, window_start=START, window_end=END)
    assert baseline_a["summary"]["recorded_attempts"] == 6
    assert baseline_a["summary"]["student_attempts"] == 5
    assert baseline_a["summary"]["non_student_attempts"] == 1
    assert {k: baseline_a["summary"][k] for k in ("cited_answer", "no_evidence", "failure")} == {
        "cited_answer": 2, "no_evidence": 2, "failure": 1,
    }
    assert baseline_a["frequent"] == [{"query": "Explain the fixed definition", "count": 2}]
    assert [(r["query"], r["count"]) for r in baseline_a["no_evidence"]] == [("Compare the fixed cases", 2)]
    # B is explicitly unavailable: no semantic-group provider is invoked for M2.
    baseline_b = {"status": "N/A", "reason": "Semantic grouping is not run in M2 Fake/Replay"}
    assert baseline_b["status"] == "N/A"

    observation = build_initial_observation(db, task, course_title=course.title, retention_days=90)
    report = fake_report(observation)
    # A recorded Replay may also investigate the current course document/page.
    document_report = evidence_report(snapshot)
    report.findings.extend(document_report.findings)
    report.evidence_refs = document_report.evidence_refs
    run_investigation(db, task, course_title=course.title,
                      replay_responses=evidence_replay(snapshot, report))
    assert task.status == "succeeded" and task.error_code is None
    stored = InvestigationReport.model_validate(task.report_json)
    result_c = read_report(db, task, retention_days=90)
    assert result_c.report == stored
    assert result_c.sample_count == result_c.summary.student_attempts == 5
    assert task.checkpoint_json["summary"] == baseline_a["summary"]
    assert task.checkpoint_json["similar_groups"].startswith("N/A")

    # Prelisted required facts (5), with independent expected support and wording.
    by_category = {f.category.value: f for f in stored.findings}
    expected_sources = {
        "no_evidence": set(QUERY_IDS[2:4]), "system_failure": {QUERY_IDS[4]},
        "repeated_question": set(QUERY_IDS[:4]), "normal_review": {QUERY_IDS[0]},
    }
    assert set(by_category) == set(expected_sources)
    for category, ids in expected_sources.items():
        assert set(by_category[category].source_query_ids) == ids
    assert "student_attempts=5" in stored.summary and "sample_count=5" in stored.summary
    assert "recorded_attempts=6" in stored.summary  # fifth required fact: scope/sample totals
    assert set(stored.source_query_ids) == set(QUERY_IDS)
    assert by_category["normal_review"].evidence_chunk_ids == [chunk.id]
    assert [(r.chunk_id, r.document_id, r.page) for r in stored.evidence_refs] == [(chunk.id, doc.id, 3)]
    validate_report_references(stored, allowed_query_ids=set(QUERY_IDS),
                               evidence_by_chunk={chunk.id: (doc.id, 3)})

    # Meaning gates, not just UUID existence: exact fixture claims are reviewed here.
    assert "does not establish missing course material" in by_category["no_evidence"].description
    assert "operational review" in by_category["system_failure"].description
    assert "no teaching inference" in by_category["system_failure"].description
    assert "does not establish a knowledge gap" in by_category["repeated_question"].description
    assert "current document" in by_category["normal_review"].description
    assert len(stored.candidate_causes) == 1
    candidate = stored.candidate_causes[0]
    assert candidate.cause_code == "undecidable"
    assert candidate.explanation == "Cause remains unknown; material coverage and retrieval require separate verification."
    assert set(candidate.source_query_ids) == set(QUERY_IDS[2:4])
    assert stored.unknowns and "citation snapshots" in stored.unknowns[0]
    assert {a.action_code.value for a in stored.suggested_actions} == {"add_regression", "investigate_system"}
    assert all(a.source_query_ids for a in stored.suggested_actions)
    serialized = stored.model_dump_json()
    assert all(s.query_text not in serialized for s in observation.question_sources)
    assert all(s.available for s in [*result_c.sources, *result_c.evidence_sources])
    usage = task.budget_used_json
    assert usage["model_calls"] == usage["tool_calls"] == usage["steps"] == 3
    assert 0 <= usage["runtime_seconds"] <= task.budget_json["max_runtime_seconds"]
    # Distinct report source references = five QueryLogs plus one Chunk/page.
    print(json.dumps({
        "fixture": FIXTURE_VERSION, "window": [START.isoformat(), END.isoformat()],
        "A_recorded": 6, "student_denominator": 5, "sample_count": 5, "B": baseline_b,
        "required_facts_covered": "5/5", "fabricated_references": "0/6",
        "asserted_candidate_causes": "0/1", "no_evidence_as_missing_material": 0,
        "system_failure_as_teaching_issue": 0, "status": task.status,
        "model_calls": usage["model_calls"], "tool_calls": usage["tool_calls"],
        "runtime_seconds": usage["runtime_seconds"], "cost": "Fake; no real cost estimate",
        "verifier": "developer fixture assertions; no independent teacher or real-model quality claim",
    }, ensure_ascii=False))
