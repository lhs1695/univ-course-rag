"""Explicit local benchmark for synthetic ingest and retrieval scale evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db import Base
from app.models.course import Course
from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.models.user import User, UserRole
from app.services.embedder import FakeEmbedder
from app.services.fusion import RRF_K
from app.services.ingest import process_ingest_job
from app.services.retrieve import SEARCH_MIN_SCORE, SEARCH_TOP_K, retrieve_chunks

BENCHMARK_VERSION = "synthetic-scale-v1"
DEFAULT_SCALES = (100, 500, 1_000)
MAX_SCALES = 6
MAX_CHUNKS_PER_SCALE = 10_000


class BenchmarkError(ValueError):
    pass


class RecordingFakeEmbedder(FakeEmbedder):
    def __init__(self) -> None:
        super().__init__()
        self.batch_sizes: list[int] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(texts))
        return super().embed(texts)


@dataclass(frozen=True)
class BenchmarkConfig:
    scales: tuple[int, ...]
    batch_size: int
    retrieval_runs: int


def parse_scales(value: str) -> tuple[int, ...]:
    try:
        scales = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise BenchmarkError("scales must be comma-separated integers") from exc
    if not scales or len(scales) > MAX_SCALES:
        raise BenchmarkError(f"scales must contain 1 to {MAX_SCALES} values")
    if any(scale < 1 or scale > MAX_CHUNKS_PER_SCALE for scale in scales):
        raise BenchmarkError(f"each scale must be between 1 and {MAX_CHUNKS_PER_SCALE}")
    if len(set(scales)) != len(scales) or tuple(sorted(scales)) != scales:
        raise BenchmarkError("scales must be unique and ascending")
    return scales


def synthetic_markdown(scale: int) -> str:
    """Create deterministic, non-sensitive text that splits into exactly `scale` chunks.

    Each unit is sized just under the production MarkdownSplitter capacity (char800)
    so short headings are not packed into fewer chunks than `scale`. The identifying
    sentence is repeated so FakeEmbedder retrieval still ranks the matching unit first.
    """
    if scale < 1 or scale > MAX_CHUNKS_PER_SCALE:
        raise BenchmarkError("synthetic scale is outside the supported range")
    parts: list[str] = []
    for index in range(scale):
        head = f"# Synthetic Unit {index}\n"
        core = (
            f"Synthetic benchmark scale{scale} unit{index}. "
            "This generated course material measures local indexing and retrieval behavior."
        )
        body = head + core
        while len(body) < 740:
            body += " " + core
        parts.append(body[:750] if len(body) > 750 else body)
    return "\n\n".join(parts)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return round(ordered[index], 1)


def _environment_summary() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "os": platform.system(),
        "machine": platform.machine(),
        "sqlalchemy": sqlalchemy.__version__,
    }


def _create_fixture(
    db: DbSession,
    source_path: Path,
    scale: int,
) -> tuple[UUID, UUID, UUID]:
    user = User(
        username=f"synthetic-benchmark-{uuid4()}",
        password_hash="synthetic-benchmark-not-a-login",
        role=UserRole.teacher.value,
    )
    course = Course(title=f"Synthetic benchmark {scale}")
    db.add_all([user, course])
    db.flush()
    document = Document(
        course_id=course.id,
        uploaded_by=user.id,
        filename=f"synthetic-{scale}.md",
        storage_path=str(source_path),
    )
    db.add(document)
    db.flush()
    job = IngestJob(document_id=document.id, status=IngestJobStatus.pending.value)
    db.add(job)
    db.commit()
    return user.id, course.id, job.id


def _benchmark_scale(
    db: DbSession,
    source_root: Path,
    scale: int,
    config: BenchmarkConfig,
    *,
    cleanup_persistent: bool,
) -> dict:
    source_path = source_root / f"synthetic-{scale}.md"
    source_path.write_text(synthetic_markdown(scale), encoding="utf-8")
    source_bytes = source_path.stat().st_size
    user_id, course_id, job_id = _create_fixture(db, source_path, scale)
    embedder = RecordingFakeEmbedder()
    try:
        started = time.perf_counter()
        process_ingest_job(db, job_id, embedder, batch_size=config.batch_size)
        ingest_latency_ms = (time.perf_counter() - started) * 1_000

        job = db.get(IngestJob, job_id)
        if job is None or job.status != IngestJobStatus.succeeded.value:
            raise BenchmarkError("synthetic ingest did not complete")
        chunks = db.execute(
            select(Chunk).where(Chunk.course_id == course_id)
        ).scalars().all()
        if len(chunks) != scale:
            raise BenchmarkError("synthetic ingest produced an unexpected chunk count")

        query_indices = (0, scale // 2, scale - 1)
        expected_by_query = {
            index: next(chunk.id for chunk in chunks if f"unit{index}." in chunk.text)
            for index in query_indices
        }
        retrieval_latencies: list[float] = []
        returned_counts: list[int] = []
        correct_top = 0
        retrieval_count = 0
        for run in range(config.retrieval_runs):
            index = query_indices[run % len(query_indices)]
            query = f"synthetic benchmark scale{scale} unit{index}"
            retrieval_started = time.perf_counter()
            hits = retrieve_chunks(db, course_id, query, embedder)
            retrieval_latencies.append((time.perf_counter() - retrieval_started) * 1_000)
            returned_counts.append(len(hits))
            correct_top += bool(hits and hits[0].chunk_id == expected_by_query[index])
            retrieval_count += 1
        ingest_batch_sizes = embedder.batch_sizes[:]
        del ingest_batch_sizes[-config.retrieval_runs :]
        return {
            "chunk_scale": scale,
            "actual_chunk_count": len(chunks),
            "ingest": {
                "latency_ms": round(ingest_latency_ms, 1),
                "embedding_batch_count": len(ingest_batch_sizes),
                "largest_embedding_batch": max(ingest_batch_sizes),
            },
            "retrieval": {
                "runs": retrieval_count,
                "latency_ms": {
                    "p50": _percentile(retrieval_latencies, 0.5),
                    "p95": _percentile(retrieval_latencies, 0.95),
                },
                "returned_count": {
                    "min": min(returned_counts),
                    "max": max(returned_counts),
                },
                "correct_top_rate": round(correct_top / retrieval_count, 3),
            },
            "resource_units": {
                "synthetic_source_bytes": source_bytes,
                "embedding_float_values": len(chunks) * 1_024,
            },
        }
    finally:
        if cleanup_persistent:
            _cleanup_postgres_fixture(db, user_id, course_id)


def _cleanup_postgres_fixture(db: DbSession, user_id: UUID, course_id: UUID) -> None:
    db.rollback()
    db.execute(delete(Course).where(Course.id == course_id))
    db.execute(delete(User).where(User.id == user_id))
    db.commit()


def run_benchmark(
    session_factory: sessionmaker,
    *,
    database_path: str,
    source_root: Path,
    config: BenchmarkConfig,
    cleanup_persistent: bool,
) -> dict:
    results: list[dict] = []
    for scale in config.scales:
        with session_factory() as db:
            results.append(
                _benchmark_scale(
                    db,
                    source_root,
                    scale,
                    config,
                    cleanup_persistent=cleanup_persistent,
                )
            )

    return {
        "schema_version": 1,
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "database_path": database_path,
        "synthetic_data": {
            "generator": "deterministic-v2",
            "scales": list(config.scales),
            "source_kind": "generated_markdown",
            "raw_payload_persisted": False,
        },
        "environment": _environment_summary(),
        "configuration": {
            "embedding_backend": "fake",
            "embedding_batch_size": config.batch_size,
            "retrieval_runs_per_scale": config.retrieval_runs,
            "top_k": SEARCH_TOP_K,
            "min_score": SEARCH_MIN_SCORE,
            "retrieval_strategy": "dense",
            "rrf_k": RRF_K,
        },
        "results": results,
        "correctness": {
            "all_ingest_counts_exact": all(
                row["actual_chunk_count"] == row["chunk_scale"] for row in results
            ),
            "all_retrievals_returned_results": all(
                row["retrieval"]["returned_count"]["min"] > 0 for row in results
            ),
            "all_top_hits_correct": all(
                row["retrieval"]["correct_top_rate"] == 1.0 for row in results
            ),
        },
    }


def _atomic_write_json(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _sqlite_benchmark(config: BenchmarkConfig, source_root: Path) -> dict:
    database_path = source_root / "synthetic-benchmark.sqlite3"
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        Base.metadata.create_all(engine)
        factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        return run_benchmark(
            factory,
            database_path="sqlite_exact_python",
            source_root=source_root,
            config=config,
            cleanup_persistent=False,
        )
    finally:
        engine.dispose()


def _postgres_benchmark(config: BenchmarkConfig, source_root: Path) -> dict:
    settings = get_settings()
    if not settings.database_url.startswith("postgresql"):
        raise BenchmarkError("Postgres benchmark requires a postgresql DATABASE_URL")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        return run_benchmark(
            factory,
            database_path="postgresql_pgvector",
            source_root=source_root,
            config=config,
            cleanup_persistent=True,
        )
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="execute the synthetic benchmark")
    parser.add_argument(
        "--database", choices=("sqlite", "postgres"), default="sqlite"
    )
    parser.add_argument(
        "--allow-postgres",
        action="store_true",
        help="acknowledge temporary writes to the configured local Postgres database",
    )
    parser.add_argument("--scales", default=",".join(map(str, DEFAULT_SCALES)))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--retrieval-runs", type=int, default=6)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        config = BenchmarkConfig(
            scales=parse_scales(args.scales),
            batch_size=args.batch_size,
            retrieval_runs=args.retrieval_runs,
        )
        if not 1 <= config.batch_size <= 256:
            raise BenchmarkError("batch size must be between 1 and 256")
        if not 1 <= config.retrieval_runs <= 20:
            raise BenchmarkError("retrieval runs must be between 1 and 20")
        if not args.run:
            print(
                json.dumps(
                    {
                        "mode": "dry-run",
                        "database": args.database,
                        "scales": list(config.scales),
                    }
                )
            )
            return 0
        if args.database == "postgres" and not args.allow_postgres:
            raise BenchmarkError("Postgres run requires --allow-postgres")

        with tempfile.TemporaryDirectory(prefix="univ-course-rag-benchmark-") as temp:
            source_root = Path(temp)
            report = (
                _sqlite_benchmark(config, source_root)
                if args.database == "sqlite"
                else _postgres_benchmark(config, source_root)
            )
        if args.output is not None:
            _atomic_write_json(args.output, report)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except BenchmarkError as exc:
        print(f"benchmark error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
