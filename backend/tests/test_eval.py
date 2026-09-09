import json
from uuid import uuid4

import pytest
from app.eval import (
    CaseSetError,
    EvalCase,
    _atomic_write_json,
    _checkpoint_report,
    _classify_failure,
    _evaluation_error,
    _load_checkpoint,
    _report,
    load_cases,
    main,
    run_evaluation,
)
from app.models.course import Course
from app.models.document import Chunk, Document
from app.services.embedder import FakeEmbedder
from app.services.llm import FakeLLM
from sqlalchemy.orm import Session


def _cases() -> list[dict]:
    return [
        {
            "id": f"case-{index}",
            "category": "pdf_fact" if index < 10 else "unrelated",
            "query": f"evaluation query {index}",
            "expected_documents": ["lecture.pdf"] if index < 10 else [],
            "should_refuse": index >= 10,
            "excluded_documents": [],
        }
        for index in range(20)
    ]


def test_eval_dry_run_validates_cases_without_live_backends(tmp_path, capsys) -> None:
    case_file = tmp_path / "cases.json"
    case_file.write_text(json.dumps({"cases": _cases()}), encoding="utf-8")

    assert main(["--case-file", str(case_file)]) == 0

    assert json.loads(capsys.readouterr().out) == {"mode": "dry-run", "case_count": 20}


def test_eval_rejects_conflicting_refusal_case(tmp_path) -> None:
    case_file = tmp_path / "cases.json"
    cases = _cases()
    cases[0]["should_refuse"] = True
    case_file.write_text(json.dumps({"cases": cases}), encoding="utf-8")

    with pytest.raises(CaseSetError, match="conflict"):
        load_cases(case_file)


def test_eval_run_requires_explicit_cloud_authorization(tmp_path) -> None:
    case_file = tmp_path / "cases.json"
    case_file.write_text(json.dumps({"cases": _cases()}), encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["--case-file", str(case_file), "--run"])


def test_eval_excludes_documents_before_mismatch_check_and_top_k(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    course = Course(title="Evaluation course")
    db.add(course)
    db.flush()
    excluded = Document(
        course_id=course.id,
        uploaded_by=uuid4(),
        filename="deleted.pdf",
        storage_path="deleted.pdf",
    )
    included = Document(
        course_id=course.id,
        uploaded_by=uuid4(),
        filename="remaining.pdf",
        storage_path="remaining.pdf",
    )
    db.add_all([excluded, included])
    db.flush()

    embedder = FakeEmbedder()
    query = "alpha beta gamma"
    db.add_all(
        [
            Chunk(
                course_id=course.id,
                document_id=excluded.id,
                page=index,
                text=query,
                embedding=embedder.embed([query])[0],
                embedding_model=embedder.index_identity,
            )
            for index in range(8)
        ]
    )
    db.add(
        Chunk(
            course_id=course.id,
            document_id=excluded.id,
            page=9,
            text=query,
            embedding=embedder.embed([query])[0],
            embedding_model="legacy-model",
        )
    )
    db.add(
        Chunk(
            course_id=course.id,
            document_id=included.id,
            page=1,
            text="alpha beta",
            embedding=embedder.embed(["alpha beta"])[0],
            embedding_model=embedder.index_identity,
        )
    )
    db.commit()
    monkeypatch.setattr("app.eval.build_embedder", lambda _settings: embedder)
    monkeypatch.setattr("app.eval.build_llm", lambda _settings: FakeLLM())

    report = run_evaluation(
        db,
        course.id,
        [
            EvalCase(
                case_id="post-delete",
                category="post_delete",
                query=query,
                expected_documents=("remaining.pdf",),
                should_refuse=False,
                excluded_documents=("deleted.pdf",),
            )
        ],
    )

    assert report["summary"]["recall_at_k"] == 1.0
    assert report["summary"]["valid_citation_rate"] == 1.0
    assert report["summary"]["failure_counts"] == {}


@pytest.mark.parametrize(
    ("should_refuse", "mismatch", "recall", "reliable", "expected"),
    [
        (False, True, False, False, "embedding_mismatch"),
        (False, False, False, False, "retrieval_miss"),
        (False, False, True, False, "missing_valid_citation"),
        (True, False, False, True, "unexpected_answer"),
        (False, False, True, True, None),
        (True, False, False, False, None),
    ],
)
def test_eval_failure_classification(
    should_refuse: bool,
    mismatch: bool,
    recall: bool,
    reliable: bool,
    expected: str | None,
) -> None:
    assert (
        _classify_failure(
            should_refuse=should_refuse,
            mismatch=mismatch,
            recall=recall,
            reliable=reliable,
        )
        == expected
    )


def test_eval_checkpoint_preserves_completed_cases_and_resume_skips_them(
    db: Session, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    course = Course(title="Checkpoint course")
    db.add(course)
    db.flush()
    document = Document(
        course_id=course.id,
        uploaded_by=uuid4(),
        filename="lecture.pdf",
        storage_path="lecture.pdf",
    )
    db.add(document)
    db.commit()
    cases = [
        EvalCase("first", "pdf_fact", "first query", ("lecture.pdf",), False, ()),
        EvalCase("second", "pdf_fact", "second query", ("lecture.pdf",), False, ()),
    ]
    embedder = FakeEmbedder()
    calls: list[str] = []
    metadata = {"course_id": str(course.id), "case_set_sha256": "test"}
    output = tmp_path / "checkpoint.json"

    monkeypatch.setattr("app.eval.build_embedder", lambda _settings: embedder)
    monkeypatch.setattr("app.eval.build_llm", lambda _settings: FakeLLM())
    monkeypatch.setattr("app.eval.has_incompatible_chunks", lambda *args, **kwargs: False)

    def retrieve(_db, _course_id, query, _embedder, **_kwargs):
        calls.append(query)
        if query == "second query" and calls.count(query) == 1:
            raise RuntimeError("query text must not be persisted")
        return []

    monkeypatch.setattr("app.eval.retrieve_chunks", retrieve)

    with pytest.raises(RuntimeError):
        run_evaluation(
            db,
            course.id,
            cases,
            on_case_complete=lambda rows: _atomic_write_json(
                output, _checkpoint_report(metadata, cases, rows)
            ),
        )

    completed = _load_checkpoint(output, metadata, cases)
    _atomic_write_json(
        output,
        _checkpoint_report(
            metadata,
            cases,
            [*completed, _evaluation_error(cases[1], RuntimeError("private query detail"))],
        ),
    )
    completed = _load_checkpoint(output, metadata, cases)
    assert [row["id"] for row in completed] == ["first"]
    assert "first query" not in output.read_text(encoding="utf-8")
    assert "private query detail" not in output.read_text(encoding="utf-8")
    report = run_evaluation(db, course.id, cases, completed_results=completed)

    assert calls == ["first query", "second query", "second query"]
    assert report["summary"]["case_count"] == 2
    assert "checkpoint" not in report


def test_eval_checkpoint_rejects_different_metadata_and_redacts_exception(tmp_path) -> None:
    cases = [EvalCase("case", "pdf_fact", "private question", ("lecture.pdf",), False, ())]
    metadata = {
        "case_set_sha256": "same-cases",
        "course_id": str(uuid4()),
        "embedding_backend": "siliconflow",
        "embedding_model": "BAAI/bge-m3",
        "llm_backend": "deepseek",
        "llm_model": "deepseek-v4-flash",
    }
    output = tmp_path / "checkpoint.json"
    output.write_text(
        json.dumps(_checkpoint_report(metadata, cases, [])), encoding="utf-8"
    )

    changed = {**metadata, "llm_model": "other-model"}
    with pytest.raises(CaseSetError, match="metadata"):
        _load_checkpoint(output, changed, cases)

    row = _evaluation_error(cases[0], RuntimeError("private question and API detail"))
    assert row == {
        "id": "case",
        "category": "pdf_fact",
        "failure_type": "evaluation_error",
        "error_type": "RuntimeError",
        "error_summary": "RuntimeError: evaluation request failed",
    }


def test_eval_final_report_keeps_existing_public_shape() -> None:
    cases = [EvalCase("case", "pdf_fact", "query", ("lecture.pdf",), False, ())]
    report = _report(
        [
            {
                "id": "case",
                "category": "pdf_fact",
                "recall_at_k": True,
                "reliable_citation": True,
                "refusal_correct": True,
                "failure_type": None,
                "latency_ms": 1.0,
            }
        ],
        cases,
    )

    assert set(report) == {"summary", "failures"}
    assert report["summary"]["case_count"] == 1
