"""Explicit, local-only runner for an independently curated live-model evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.models.document import Document
from app.services.embedder import build_embedder
from app.services.generate import generate_answer
from app.services.llm import build_llm
from app.services.retrieve import has_incompatible_chunks, retrieve_chunks

CASE_COUNT_MIN = 20
CASE_COUNT_MAX = 30
CATEGORIES = {
    "pdf_fact",
    "pptx_fact",
    "cross_page",
    "zh_question_en_source",
    "similar_no_answer",
    "unrelated",
    "post_delete",
}


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    category: str
    query: str
    expected_documents: tuple[str, ...]
    should_refuse: bool
    excluded_documents: tuple[str, ...]


class CaseSetError(ValueError):
    pass


def load_cases(path: Path) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases") if isinstance(raw, dict) else None
    if not isinstance(cases, list) or not CASE_COUNT_MIN <= len(cases) <= CASE_COUNT_MAX:
        raise CaseSetError(f"cases must contain {CASE_COUNT_MIN} to {CASE_COUNT_MAX} items")

    parsed: list[EvalCase] = []
    ids: set[str] = set()
    for item in cases:
        if not isinstance(item, dict):
            raise CaseSetError("each case must be an object")
        case_id = item.get("id")
        category = item.get("category")
        query = item.get("query")
        expected = item.get("expected_documents", [])
        excluded = item.get("excluded_documents", [])
        should_refuse = item.get("should_refuse")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise CaseSetError("case ids must be unique, non-empty strings")
        if category not in CATEGORIES or not isinstance(query, str) or not query.strip():
            raise CaseSetError(f"invalid category or query for case {case_id}")
        if not isinstance(expected, list) or not all(isinstance(name, str) and name for name in expected):
            raise CaseSetError(f"expected_documents must be a list of filenames for case {case_id}")
        if not isinstance(excluded, list) or not all(isinstance(name, str) and name for name in excluded):
            raise CaseSetError(f"excluded_documents must be a list of filenames for case {case_id}")
        if not isinstance(should_refuse, bool) or (should_refuse and expected) or (
            not should_refuse and not expected
        ):
            raise CaseSetError(f"expected documents and refusal label conflict for case {case_id}")
        ids.add(case_id)
        parsed.append(
            EvalCase(
                case_id,
                category,
                query.strip(),
                tuple(expected),
                should_refuse,
                tuple(excluded),
            )
        )
    return parsed


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return round(ordered[index], 1)


def run_evaluation(db: DbSession, course_id: UUID, cases: list[EvalCase]) -> dict:
    settings = get_settings()
    embedder = build_embedder(settings)
    llm = build_llm(settings)
    document_names = {
        document.id: document.filename
        for document in db.execute(
            select(Document).where(Document.course_id == course_id)
        ).scalars()
    }
    results: list[dict] = []
    latencies: list[float] = []
    for case in cases:
        started = time.perf_counter()
        mismatch = has_incompatible_chunks(db, course_id, embedder)
        hits = [] if mismatch else retrieve_chunks(db, course_id, case.query, embedder)
        hits = [
            hit
            for hit in hits
            if document_names.get(hit.document_id) not in case.excluded_documents
        ]
        cited_ids = []
        if hits:
            _, cited_ids = generate_answer(db, case.query, hits, llm)
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        retrieved_documents = {document_names.get(hit.document_id) for hit in hits}
        retrieved_documents.discard(None)
        recall = bool(set(case.expected_documents) & retrieved_documents)
        reliable = bool(cited_ids)
        actual_refusal = mismatch or not reliable
        if mismatch:
            failure_type = "embedding_mismatch"
        elif case.should_refuse != actual_refusal:
            failure_type = "unexpected_answer" if case.should_refuse else "unexpected_refusal"
        elif not case.should_refuse and not recall:
            failure_type = "retrieval_miss"
        elif not case.should_refuse and not reliable:
            failure_type = "missing_valid_citation"
        else:
            failure_type = None
        results.append(
            {
                "id": case.case_id,
                "category": case.category,
                "recall_at_k": recall,
                "reliable_citation": reliable,
                "refusal_correct": case.should_refuse == actual_refusal,
                "failure_type": failure_type,
                "latency_ms": round(latency_ms, 1),
            }
        )

    answered = [case for case in cases if not case.should_refuse]
    answered_results = [
        row for case, row in zip(cases, results, strict=True) if not case.should_refuse
    ]
    summary = {
        "case_count": len(cases),
        "recall_at_k": round(
            sum(row["recall_at_k"] for row in answered_results) / len(answered), 3
        ),
        "valid_citation_rate": round(
            sum(row["reliable_citation"] for row in answered_results) / len(answered), 3
        ),
        "refusal_accuracy": round(
            sum(row["refusal_correct"] for row in results) / len(cases), 3
        ),
        "latency_ms": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95)},
        "failure_counts": {
            name: sum(row["failure_type"] == name for row in results)
            for name in sorted({row["failure_type"] for row in results if row["failure_type"]})
        },
    }
    return {"summary": summary, "failures": [row for row in results if row["failure_type"]]}


def _require_live_configuration(settings: Settings) -> None:
    if (
        settings.embedder_backend != "siliconflow"
        or settings.llm_backend != "deepseek"
        or not settings.siliconflow_api_key
        or not settings.deepseek_api_key
    ):
        raise CaseSetError("live evaluation requires configured SiliconFlow and DeepSeek backends")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-file", type=Path, required=True)
    parser.add_argument("--course-id", type=UUID)
    parser.add_argument("--run", action="store_true", help="execute the local course evaluation")
    parser.add_argument("--allow-cloud", action="store_true", help="acknowledge live API use and cost")
    parser.add_argument("--output", type=Path, help="write summary and failure list JSON")
    args = parser.parse_args(argv)
    cases = load_cases(args.case_file)
    if not args.run:
        print(json.dumps({"mode": "dry-run", "case_count": len(cases)}, ensure_ascii=False))
        return 0
    if not args.allow_cloud or args.course_id is None or args.output is None:
        parser.error("--run requires --allow-cloud, --course-id, and --output")
    settings = get_settings()
    _require_live_configuration(settings)
    db = SessionLocal()
    try:
        report = run_evaluation(db, args.course_id, cases)
    finally:
        db.close()
    report["metadata"] = {
        "case_set_sha256": hashlib.sha256(args.case_file.read_bytes()).hexdigest(),
        "embedding_backend": settings.embedder_backend,
        "embedding_model": settings.embedding_model,
        "llm_backend": settings.llm_backend,
        "llm_model": settings.deepseek_model,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
