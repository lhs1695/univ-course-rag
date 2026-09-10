from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session as DbSession

from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.services.chunk import chunk_pages
from app.services.embedder import Embedder
from app.services.parse import (
    DEFAULT_PARSE_LIMITS,
    ParseError,
    ParseLimits,
    parse_document,
)
from app.services.upstream import UPSTREAM_UNAVAILABLE, UpstreamUnavailable

_SECRET = re.compile(r"sk-[A-Za-z0-9]+")


class IngestError(Exception):
    pass


class IngestLeaseLost(IngestError):
    pass


def safe_error(exc: BaseException) -> str:
    if isinstance(exc, UpstreamUnavailable):
        return UPSTREAM_UNAVAILABLE
    if isinstance(exc, ParseError):
        return str(exc)
    message = f"{type(exc).__name__}: {exc}"
    message = _SECRET.sub("[redacted]", message)
    return message[:400]


def _claim_pending_job(db: DbSession, job_id: UUID) -> UUID | None:
    run_token = uuid4()
    result = db.execute(
        update(IngestJob)
        .where(
            IngestJob.id == job_id,
            IngestJob.status == IngestJobStatus.pending.value,
        )
        .values(
            status=IngestJobStatus.running.value,
            run_token=run_token,
            error_message=None,
            updated_at=datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return run_token if result.rowcount == 1 else None


def _touch_running_job(db: DbSession, job_id: UUID, run_token: UUID) -> None:
    result = db.execute(
        update(IngestJob)
        .where(
            IngestJob.id == job_id,
            IngestJob.status == IngestJobStatus.running.value,
            IngestJob.run_token == run_token,
        )
        .values(updated_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if result.rowcount != 1:
        raise IngestLeaseLost("ingest lease lost")


def process_ingest_job(
    db: DbSession,
    job_id: UUID,
    embedder: Embedder,
    *,
    batch_size: int = 32,
    parse_limits: ParseLimits = DEFAULT_PARSE_LIMITS,
) -> None:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    run_token = _claim_pending_job(db, job_id)
    if run_token is None:
        return
    job = db.get(IngestJob, job_id)
    if job is None:
        return
    document = db.get(Document, job.document_id)
    if document is None:
        _fail_job(db, job_id, run_token, "document missing")
        return

    try:
        data = Path(document.storage_path).read_bytes()
        pages = parse_document(document.filename, data, limits=parse_limits)
        pieces = chunk_pages(pages)
        if not pieces:
            raise IngestError("no chunks produced")
        vectors: list[list[float]] = []
        for start in range(0, len(pieces), batch_size):
            batch = pieces[start : start + batch_size]
            batch_vectors = embedder.embed([text for _, text in batch])
            if len(batch_vectors) != len(batch):
                raise IngestError("embedder returned wrong batch size")
            if any(len(vector) != 1024 for vector in batch_vectors):
                raise IngestError("embedding dimension must be 1024")
            vectors.extend(batch_vectors)
            _touch_running_job(db, job_id, run_token)

        db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        for (page, text), vector in zip(pieces, vectors, strict=True):
            db.add(
                Chunk(
                    course_id=document.course_id,
                    document_id=document.id,
                    page=page,
                    text=text,
                    embedding=vector,
                    embedding_model=embedder.index_identity,
                )
            )
        db.flush()
        completed = db.execute(
            update(IngestJob)
            .where(
                IngestJob.id == job_id,
                IngestJob.status == IngestJobStatus.running.value,
                IngestJob.run_token == run_token,
            )
            .values(
                status=IngestJobStatus.succeeded.value,
                run_token=None,
                error_message=None,
                updated_at=datetime.now(UTC),
            )
            .execution_options(synchronize_session=False)
        )
        if completed.rowcount != 1:
            raise IngestLeaseLost("ingest lease lost")
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _fail_job(db, job_id, run_token, safe_error(exc))


def _fail_job(db: DbSession, job_id: UUID, run_token: UUID, message: str) -> None:
    db.execute(
        update(IngestJob)
        .where(
            IngestJob.id == job_id,
            IngestJob.status == IngestJobStatus.running.value,
            IngestJob.run_token == run_token,
        )
        .values(
            status=IngestJobStatus.failed.value,
            run_token=None,
            error_message=message,
            updated_at=datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()


def retry_ingest_job(db: DbSession, job_id: UUID, stale_before: datetime) -> bool:
    result = db.execute(
        update(IngestJob)
        .where(
            IngestJob.id == job_id,
            (
                (IngestJob.status == IngestJobStatus.failed.value)
                | (
                    IngestJob.status.in_(
                        [
                            IngestJobStatus.pending.value,
                            IngestJobStatus.running.value,
                        ]
                    )
                    & (IngestJob.updated_at <= stale_before)
                )
            ),
        )
        .values(
            status=IngestJobStatus.pending.value,
            run_token=None,
            error_message=None,
            updated_at=datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def latest_job(db: DbSession, document_id: UUID) -> IngestJob | None:
    return db.execute(
        select(IngestJob)
        .where(IngestJob.document_id == document_id)
        .order_by(IngestJob.created_at.desc())
    ).scalars().first()
