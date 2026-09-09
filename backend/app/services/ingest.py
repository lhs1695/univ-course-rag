from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.services.chunk import chunk_pages
from app.services.embedder import Embedder
from app.services.parse import parse_document

_SECRET = re.compile(r"sk-[A-Za-z0-9]+")


class IngestError(Exception):
    pass


def safe_error(exc: BaseException) -> str:
    message = f"{type(exc).__name__}: {exc}"
    message = _SECRET.sub("[redacted]", message)
    return message[:400]


def process_ingest_job(db: DbSession, job_id: UUID, embedder: Embedder) -> None:
    job = db.get(IngestJob, job_id)
    if job is None:
        return
    document = db.get(Document, job.document_id)
    if document is None:
        job.status = IngestJobStatus.failed.value
        job.error_message = "document missing"
        db.commit()
        return

    job.status = IngestJobStatus.running.value
    job.error_message = None
    db.commit()

    try:
        data = Path(document.storage_path).read_bytes()
        pages = parse_document(document.filename, data)
        pieces = chunk_pages(pages)
        if not pieces:
            raise IngestError("no chunks produced")
        vectors = embedder.embed([text for _, text in pieces])
        if len(vectors) != len(pieces):
            raise IngestError("embedder returned wrong batch size")
        db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        for (page, text), vector in zip(pieces, vectors, strict=True):
            if len(vector) != 1024:
                raise IngestError("embedding dimension must be 1024")
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
        job.status = IngestJobStatus.succeeded.value
        job.error_message = None
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _fail_job(db, job_id, document.id if document is not None else None, safe_error(exc))


def _fail_job(db: DbSession, job_id: UUID, document_id: UUID | None, message: str) -> None:
    if document_id is not None:
        db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    job = db.get(IngestJob, job_id)
    if job is None:
        db.commit()
        return
    job.status = IngestJobStatus.failed.value
    job.error_message = message
    db.commit()


def latest_job(db: DbSession, document_id: UUID) -> IngestJob | None:
    return db.execute(
        select(IngestJob)
        .where(IngestJob.document_id == document_id)
        .order_by(IngestJob.created_at.desc())
    ).scalars().first()
