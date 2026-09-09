"""Explicit, local-only runner for an independently curated live-model evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
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


def _classify_failure(
    *,
    should_refuse: bool,
    mismatch: bool,
    recall: bool,
    reliable: bool,
) -> str | None:
    if mismatch:
        return "embedding_mismatch"
    if not should_refuse and not recall:
        return "retrieval_miss"
    if not should_refuse and not reliable:
        return "missing_valid_citation"
    if should_refuse and reliable:
        return "unexpected_answer"
    return None


def _report(results: list[dict], cases: list[EvalCase]) -> dict:
    by_id = {case.case_id: case for case in cases}
    completed = [
        row for row in results if row.get("id") in by_id and "latency_ms" in row
    ]
    answered = [case for case in cases if not case.should_refuse]
    answered_results = [
        row for row in completed if not by_id[row["id"]].should_refuse
    ]
    latencies = [row["latency_ms"] for row in completed]
    return {
        "summary": {
            "case_count": len(completed),
            "recall_at_k": (
                round(sum(row["recall_at_k"] for row in answered_results) / len(answered), 3)
                if len(answered_results) == len(answered)
                else None
            ),
            "valid_citation_rate": (
                round(
                    sum(row["reliable_citation"] for row in answered_results) / len(answered),
                    3,
                )
                if len(answered_results) == len(answered)
                else None
            ),
            "refusal_accuracy": (
                round(sum(row["refusal_correct"] for row in completed) / len(cases), 3)
                if len(completed) == len(cases)
                else None
            ),
            "latency_ms": {
                "p50": _percentile(latencies, 0.5),
                "p95": _percentile(latencies, 0.95),
            },
            "failure_counts": {
                name: sum(row["failure_type"] == name for row in results)
                for name in sorted(
                    {row["failure_type"] for row in results if row["failure_type"]}
                )
            },
        },
        "failures": [row for row in results if row["failure_type"]],
    }


def _metadata(case_file: Path, course_id: UUID, settings: Settings) -> dict:
    return {
        "case_set_sha256": hashlib.sha256(case_file.read_bytes()).hexdigest(),
        "course_id": str(course_id),
        "embedding_backend": settings.embedder_backend,
        "embedding_model": settings.embedding_model,
        "llm_backend": settings.llm_backend,
        "llm_model": settings.deepseek_model,
    }


def _public_metadata(metadata: dict) -> dict:
    return {key: value for key, value in metadata.items() if key != "course_id"}


def _atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _checkpoint_report(metadata: dict, cases: list[EvalCase], results: list[dict]) -> dict:
    report = _report(results, cases)
    report["metadata"] = metadata
    report["checkpoint"] = {
        "status": "in_progress",
        "total_case_count": len(cases),
        "completed_case_ids": [row["id"] for row in results if "latency_ms" in row],
        "results": results,
    }
    return report


def _load_checkpoint(path: Path, metadata: dict, cases: list[EvalCase]) -> list[dict]:
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaseSetError("cannot read evaluation checkpoint") from exc
    if not isinstance(saved, dict) or saved.get("metadata") != metadata:
        raise CaseSetError("checkpoint metadata does not match this evaluation")
    checkpoint = saved.get("checkpoint")
    if not isinstance(checkpoint, dict) or checkpoint.get("status") != "in_progress":
        raise CaseSetError("checkpoint is not an unfinished evaluation")
    results = checkpoint.get("results")
    if not isinstance(results, list):
        raise CaseSetError("checkpoint results are invalid")
    case_ids = {case.case_id for case in cases}
    completed_ids = checkpoint.get("completed_case_ids")
    if (
        not isinstance(completed_ids, list)
        or len(completed_ids) != len(set(completed_ids))
        or not set(completed_ids) <= case_ids
    ):
        raise CaseSetError("checkpoint completed cases are invalid")
    completed = [row for row in results if isinstance(row, dict) and row.get("id") in completed_ids]
    if {row.get("id") for row in completed} != set(completed_ids):
        raise CaseSetError("checkpoint result records are invalid")
    return completed


def _evaluation_error(case: EvalCase, exc: Exception) -> dict:
    error_type = type(exc).__name__
    return {
        "id": case.case_id,
        "category": case.category,
        "failure_type": "evaluation_error",
        "error_type": error_type,
        "error_summary": f"{error_type}: evaluation request failed",
    }


def run_evaluation(
    db: DbSession,
    course_id: UUID,
    cases: list[EvalCase],
    *,
    completed_results: list[dict] | None = None,
    on_case_complete: Callable[[list[dict]], None] | None = None,
) -> dict:
    settings = get_settings()
    embedder = build_embedder(settings)
    llm = build_llm(settings)
    document_names = {
        document.id: document.filename
        for document in db.execute(
            select(Document).where(Document.course_id == course_id)
        ).scalars()
    }
    results = completed_results if completed_results is not None else []
    completed_ids = {row["id"] for row in results}
    for case in cases:
        if case.case_id in completed_ids:
            continue
        started = time.perf_counter()
        excluded_document_ids = {
            document_id
            for document_id, filename in document_names.items()
            if filename in case.excluded_documents
        }
        mismatch = has_incompatible_chunks(
            db,
            course_id,
            embedder,
            excluded_document_ids=excluded_document_ids,
        )
        hits = (
            []
            if mismatch
            else retrieve_chunks(
                db,
                course_id,
                case.query,
                embedder,
                excluded_document_ids=excluded_document_ids,
            )
        )
        cited_ids = []
        if hits:
            _, cited_ids = generate_answer(db, case.query, hits, llm)
        latency_ms = (time.perf_counter() - started) * 1000
        retrieved_documents = {document_names.get(hit.document_id) for hit in hits}
        retrieved_documents.discard(None)
        recall = bool(set(case.expected_documents) & retrieved_documents)
        reliable = bool(cited_ids)
        actual_refusal = mismatch or not reliable
        failure_type = _classify_failure(
            should_refuse=case.should_refuse,
            mismatch=mismatch,
            recall=recall,
            reliable=reliable,
        )
        row = {
            "id": case.case_id,
            "category": case.category,
            "recall_at_k": recall,
            "reliable_citation": reliable,
            "refusal_correct": case.should_refuse == actual_refusal,
            "failure_type": failure_type,
            "latency_ms": round(latency_ms, 1),
        }
        results.append(row)
        if on_case_complete is not None:
            on_case_complete(results)

    return _report(results, cases)


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
    parser.add_argument("--resume", action="store_true", help="resume a matching unfinished checkpoint")
    args = parser.parse_args(argv)
    cases = load_cases(args.case_file)
    if not args.run:
        print(json.dumps({"mode": "dry-run", "case_count": len(cases)}, ensure_ascii=False))
        return 0
    if not args.allow_cloud or args.course_id is None or args.output is None:
        parser.error("--run requires --allow-cloud, --course-id, and --output")
    settings = get_settings()
    _require_live_configuration(settings)
    metadata = _metadata(args.case_file, args.course_id, settings)
    if args.resume:
        completed_results = _load_checkpoint(args.output, metadata, cases)
    else:
        completed_results = []

    def save_checkpoint(results: list[dict]) -> None:
        _atomic_write_json(args.output, _checkpoint_report(metadata, cases, results))

    db = SessionLocal()
    try:
        try:
            report = run_evaluation(
                db,
                args.course_id,
                cases,
                completed_results=completed_results,
                on_case_complete=save_checkpoint,
            )
        except Exception as exc:  # noqa: BLE001 - cloud clients expose provider-specific errors.
            current_case = next(
                case for case in cases if case.case_id not in {row["id"] for row in completed_results}
            )
            failed_results = [*completed_results, _evaluation_error(current_case, exc)]
            _atomic_write_json(args.output, _checkpoint_report(metadata, cases, failed_results))
            print("evaluation interrupted; safe checkpoint saved", file=sys.stderr)
            return 1
    finally:
        db.close()
    report["metadata"] = _public_metadata(metadata)
    _atomic_write_json(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
