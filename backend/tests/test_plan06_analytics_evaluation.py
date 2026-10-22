"""Synthetic arithmetic assertions, not semantic accuracy or teacher trials."""

import copy
import json
from pathlib import Path

import pytest
from app.services.analytics_evaluation import (
    evaluate_assignments,
    evaluate_fixture,
    evaluate_pairs,
    main,
)

FIXTURE = Path(__file__).parent / "fixtures" / "plan06_analytics_synthetic_v1.json"


@pytest.fixture
def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_synthetic_counts_and_error_cases_are_recomputable(sample):
    result = evaluate_fixture(sample)
    pairs = result["pairs"]
    assert {key: pairs[key] for key in ("tp", "fp", "fn", "tn")} == {
        "tp": 1, "fp": 1, "fn": 1, "tn": 2,
    }
    assert pairs["labeled_pairs"] == 6
    assert pairs["evaluated_pairs"] == 5
    assert pairs["uncertain_count"] == 1
    assert pairs["precision"] == pairs["recall"] == {"n": 1, "N": 2, "value": 0.5}
    assert pairs["mis_merge_rate"] == pairs["mis_split_rate"] == pairs["precision"]
    assert pairs["mis_merge"] == [["q1", "q3"]]
    assert pairs["mis_split"] == [["q3", "q4"]]
    assert pairs["uncertain_pairs"] == [["q7", "q8"]]
    assert result["assignments"] == {
        "distinct_questions": 8,
        "coverage": {"n": 3, "N": 8, "value": 0.375},
        "singleton_rate": {"n": 3, "N": 8, "value": 0.375},
        "ungrouped_rate": {"n": 2, "N": 8, "value": 0.25},
        "singleton_ids": ["q4", "q5", "q6"],
        "ungrouped_ids": ["q7", "q8"],
    }
    assert result["config"] == sample["config"]
    assert result["sample_version"] == "plan06-synthetic-v1"
    assert result["evidence_level"] == "synthetic_fake_arithmetic"


def test_order_invariance_and_no_input_mutation(sample):
    original = copy.deepcopy(sample)
    expected = evaluate_fixture(sample)
    assert sample == original
    sample["assignments"].reverse()
    sample["labeled_pairs"].reverse()
    for row in sample["labeled_pairs"]:
        row["left"], row["right"] = row["right"], row["left"]
    assert evaluate_fixture(sample) == expected


def test_precision_and_recall_have_distinct_denominators():
    assignments = [{"question_id": q, "cluster_id": "c"} for q in ("a", "b", "c")]
    pairs = [{"left": "a", "right": "b", "label": "same"},
             {"left": "a", "right": "c", "label": "different"}]
    result = evaluate_pairs(pairs, assignments)
    assert result["precision"] == {"n": 1, "N": 2, "value": 0.5}
    assert result["recall"] == {"n": 1, "N": 1, "value": 1.0}


def test_empty_and_uncertain_only_are_undefined_not_perfect(sample):
    result = evaluate_pairs([], [])
    assert result["precision"] == result["recall"] == {"n": 0, "N": 0, "value": None}
    for key in ("coverage", "singleton_rate", "ungrouped_rate"):
        assert evaluate_assignments([])[key] == {"n": 0, "N": 0, "value": None}
    result = evaluate_pairs([sample["labeled_pairs"][-1]], sample["assignments"])
    assert result["evaluated_pairs"] == 0
    assert result["uncertain_count"] == 1
    assert result["precision"]["value"] is result["recall"]["value"] is None


def test_null_assignments_never_merge_and_positive_pair_is_missed():
    assignments = [{"question_id": q, "cluster_id": None} for q in ("a", "b", "c")]
    pairs = [{"left": "a", "right": "b", "label": "same"},
             {"left": "a", "right": "c", "label": "different"}]
    result = evaluate_pairs(pairs, assignments)
    assert result["tp"] == result["fp"] == 0
    assert result["fn"] == result["tn"] == 1
    assert result["precision"]["value"] is None
    assert result["recall"] == {"n": 0, "N": 1, "value": 0.0}
    assert result["mis_split"] == [["a", "b"]]
    assert evaluate_assignments(assignments)["ungrouped_rate"]["n"] == 3


@pytest.mark.parametrize("pairs, message", [
    ([{"left": "q1", "right": "q1", "label": "same"}], "Self-pairs"),
    ([{"left": "q1", "right": "missing", "label": "same"}], "unknown question_id"),
    ([{"left": "q1", "right": "q2", "label": True}], "Unknown pair label"),
    ([{"left": "q1", "right": "q2", "label": "same"},
      {"left": "q2", "right": "q1", "label": "uncertain"}], "Duplicate unordered pair"),
])
def test_invalid_pairs_are_not_silently_dropped(sample, pairs, message):
    with pytest.raises(ValueError, match=message):
        evaluate_pairs(pairs, sample["assignments"])


@pytest.mark.parametrize("assignments", [
    [{"question_id": "a", "cluster_id": "c"}, {"question_id": "a", "cluster_id": None}],
    [{"question_id": "", "cluster_id": "c"}],
    [{"question_id": "a", "cluster_id": " "}],
    [{"question_id": "a", "cluster_id": 0}],
])
def test_invalid_assignments_fail_both_entry_points(assignments):
    with pytest.raises(ValueError):
        evaluate_assignments(assignments)
    with pytest.raises(ValueError):
        evaluate_pairs([], assignments)


def test_cli_outputs_json_to_stdout_without_writing_fixture(sample, monkeypatch, capsys):
    before = FIXTURE.read_bytes()
    monkeypatch.setattr("sys.argv", ["analytics_evaluation", str(FIXTURE)])
    main()
    assert json.loads(capsys.readouterr().out) == evaluate_fixture(sample)
    assert FIXTURE.read_bytes() == before
