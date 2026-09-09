import json
from uuid import uuid4

import pytest
from app.eval import (
    CaseSetError,
    EvalCase,
    _classify_failure,
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
