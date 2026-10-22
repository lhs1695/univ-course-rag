"""Offline PLAN-06 arithmetic only; no DB, settings, providers or label inference.

Run from the repository root::

    backend/.venv/Scripts/python.exe backend/app/services/analytics_evaluation.py INPUT.json

JSON schema and denominator rules: docs/analytics-validation-protocol.md.
All rates include n/N; an empty denominator yields JSON null, never a passing score.
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("IDs must be nonblank strings")
    return value


def _assignment_map(assignments: list[dict]) -> dict[str, str | None]:
    result = {}
    for row in assignments:
        question_id = _identifier(row["question_id"])
        cluster_id = row["cluster_id"]
        if cluster_id is not None:
            _identifier(cluster_id)
        if question_id in result:
            raise ValueError("Duplicate question_id")
        result[question_id] = cluster_id
    return result


def _rate(n: int, denominator: int) -> dict:
    return {"n": n, "N": denominator, "value": n / denominator if denominator else None}


def evaluate_assignments(assignments: list[dict]) -> dict:
    """One row per eligible distinct question; null means absent from any cluster.

    Coverage counts questions in clusters of size >=2. Singleton rate counts
    questions in clusters of size 1, not singleton clusters / all clusters.
    Null assignments are separate from singletons; all three share the full N.
    """
    mapping = _assignment_map(assignments)
    sizes = Counter(cluster for cluster in mapping.values() if cluster is not None)
    ungrouped = sorted(q for q, cluster in mapping.items() if cluster is None)
    singleton = sorted(q for q, cluster in mapping.items() if sizes[cluster] == 1)
    total = len(mapping)
    return {
        "distinct_questions": total,
        "coverage": _rate(total - len(singleton) - len(ungrouped), total),
        "singleton_rate": _rate(len(singleton), total),
        "ungrouped_rate": _rate(len(ungrouped), total),
        "singleton_ids": singleton,
        "ungrouped_ids": ungrouped,
    }


def evaluate_pairs(labeled_pairs: list[dict], assignments: list[dict]) -> dict:
    """Score only explicit, unique unordered pairs, without transitive gold labels.

    Labels: same / different / uncertain. Uncertain pairs are counted but excluded
    from TP/FP/FN/TN. Two null assignments never imply the same cluster. Missing
    question IDs, self-pairs and duplicate (even reversed) pairs fail closed.
    """
    mapping = _assignment_map(assignments)
    seen = set()
    counts = dict.fromkeys(("tp", "fp", "fn", "tn"), 0)
    errors = {"mis_merge": [], "mis_split": [], "uncertain_pairs": []}
    for row in labeled_pairs:
        pair = tuple(sorted((_identifier(row["left"]), _identifier(row["right"]))))
        if pair[0] == pair[1]:
            raise ValueError("Self-pairs are not evaluable")
        if pair in seen:
            raise ValueError("Duplicate unordered pair")
        seen.add(pair)
        if any(question_id not in mapping for question_id in pair):
            raise ValueError("Pair references an unknown question_id")
        label = row["label"]
        if label not in ("same", "different", "uncertain"):
            raise ValueError("Unknown pair label")
        if label == "uncertain":
            errors["uncertain_pairs"].append(list(pair))
            continue
        predicted_same = mapping[pair[0]] is not None and mapping[pair[0]] == mapping[pair[1]]
        if label == "same":
            outcome = "tp" if predicted_same else "fn"
        else:
            outcome = "fp" if predicted_same else "tn"
        counts[outcome] += 1
        if outcome in ("fp", "fn"):
            errors["mis_merge" if outcome == "fp" else "mis_split"].append(list(pair))
    for pairs in errors.values():
        pairs.sort()
    tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn"))
    evaluated = sum(counts.values())
    return {
        **counts,
        "labeled_pairs": len(seen),
        "evaluated_pairs": evaluated,
        "uncertain_count": len(errors["uncertain_pairs"]),
        "precision": _rate(tp, tp + fp),
        "recall": _rate(tp, tp + fn),
        "mis_merge_rate": _rate(fp, tp + fp),
        "mis_split_rate": _rate(fn, tp + fn),
        **errors,
    }


def evaluate_fixture(document: dict) -> dict:
    """Echo provenance/config verbatim, compute counts; never declare acceptance.

    This helper does not authenticate metadata or perform human label checks.
    Knowledge/theme checks and teacher observation belong in the report template.
    """
    return {
        "sample_version": document["sample_version"],
        "evidence_level": document["evidence_level"],
        "config": document["config"],
        "pairs": evaluate_pairs(document["labeled_pairs"], document["assignments"]),
        "assignments": evaluate_assignments(document["assignments"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as source:
        result = evaluate_fixture(json.load(source))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
