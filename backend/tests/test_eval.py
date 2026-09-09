import json

import pytest
from app.eval import CaseSetError, load_cases, main


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
