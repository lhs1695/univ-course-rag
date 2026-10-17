from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session as DbSession

from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.services.chunk import CHUNKING_VERSION, chunk_pages
from app.services.embedder import Embedder
from app.services.parse import (
    DEFAULT_PARSE_LIMITS,
    ParseError,
    ParseLimits,
    parse_document_with_quality,
)
from app.services.parse_quality import ParseStatus
from app.services.upstream import UpstreamUnavailable

LOW_EXTRACTED_TEXT = "LOW_EXTRACTED_TEXT"
COVERAGE_INCOMPLETE = "COVERAGE_INCOMPLETE"
_POSTGRES_NUL = "\x00"
SAFE_INGEST_ERRORS = frozenset({
    "UPSTREAM_UNAVAILABLE", "UPSTREAM_TIMEOUT", "INGEST_FAILED",
    "no extractable text", "text file is not valid UTF-8",
    "PDF parser is not installed", "unreadable PDF", "incomplete PDF parse",
    "PPT parser is not installed", "unreadable PPT",
    "Word parser is not installed", "unreadable Word", "unreadable OOXML",
    "OOXML resource limit exceeded", "extracted text exceeds resource limit",
})


class IngestError(Exception):
    pass


class IngestLeaseLost(IngestError):
    pass


def safe_error(exc: BaseException) -> str:
    if isinstance(exc, UpstreamUnavailable):
        return exc.error_code
    if isinstance(exc, ParseError) and str(exc) in SAFE_INGEST_ERRORS:
        return str(exc)
    return "INGEST_FAILED"


def _sanitize_extracted_pages(
    pages: list[tuple[int | None, str]],
) -> list[tuple[int | None, str]]:
    """Remove the one code point PostgreSQL text fields cannot store.

    Apply this before chunking and embedding so the indexed text, metadata count,
    and persisted text describe the same extract on every supported database.
    """
    return [
        (page, clean) for page, text in pages
        if (clean := text.replace(_POSTGRES_NUL, "")).strip()
    ]


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
    low_text_chars: int = 200,
) -> None:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if low_text_chars < 1:
        raise ValueError("low_text_chars must be positive")
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
        pages, quality = parse_document_with_quality(
            document.filename, data, limits=parse_limits,
        )
        if quality is not None and quality.status is ParseStatus.FAILED:
            raise ParseError("incomplete PDF parse")
        pages = _sanitize_extracted_pages(pages)
        extracted_char_count = sum(len(text) for _, text in pages)
        pieces = chunk_pages(pages, filename=document.filename)
        if not pieces:
            raise IngestError("no chunks produced")
        if quality is not None:
            for piece in pieces:
                piece.source_metadata.update({
                    "parser_version": quality.parser_version,
                    "structured_hash": quality.structured_hash,
                })
        vectors: list[list[float]] = []
        for start in range(0, len(pieces), batch_size):
            batch = pieces[start : start + batch_size]
            batch_vectors = embedder.embed([piece.text for piece in batch])
            if len(batch_vectors) != len(batch):
                raise IngestError("embedder returned wrong batch size")
            if any(len(vector) != 1024 for vector in batch_vectors):
                raise IngestError("embedding dimension must be 1024")
            vectors.extend(batch_vectors)
            _touch_running_job(db, job_id, run_token)

        db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        for piece, vector in zip(pieces, vectors, strict=True):
            db.add(
                Chunk(
                    course_id=document.course_id,
                    document_id=document.id,
                    page=piece.page,
                    text=piece.text,
                    source_metadata=piece.source_metadata,
                    embedding=vector,
                    embedding_model=embedder.index_identity,
                )
            )
        db.flush()
        document.source_unit_count = len(pages)
        document.extracted_char_count = extracted_char_count
        document.chunk_count = len(pieces)
        document.quality_warning = (
            COVERAGE_INCOMPLETE if quality is not None and quality.status is ParseStatus.PARTIAL
            else LOW_EXTRACTED_TEXT if extracted_char_count < low_text_chars else None
        )
        document.chunking_version = CHUNKING_VERSION
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
