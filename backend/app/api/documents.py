import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker as SessionMaker

from app.api.schemas import DocumentOut, DocumentUpdateRequest
from app.config import Settings, get_settings
from app.db import get_db, get_session_maker
from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.security.deps import (
    CourseAccess,
    require_course_member,
    require_course_teacher,
)
from app.services.embedder import Embedder, get_embedder
from app.services.ingest import (
    SAFE_INGEST_ERRORS,
    latest_job,
    process_ingest_job,
    retry_ingest_job,
)
from app.services.parse import ParseLimits, parse_limits_from_settings
from app.services.storage import (
    StorageError,
    delete_document_upload,
    get_document_upload,
    store_upload,
)

router = APIRouter(prefix="/courses/{course_id}/documents", tags=["documents"])
logger = logging.getLogger(__name__)

_ALLOWED_SUFFIX = {".pdf", ".pptx", ".docx", ".md", ".markdown", ".txt"}
_MAX_UPLOAD_BYTES = 15 * 1024 * 1024
_UNSUPPORTED_FILE_TYPE = (
    "unsupported file type; accepted: PDF, PPTX, DOCX, Markdown, or plain text"
)
_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown; charset=utf-8",
    ".markdown": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def _document_out(document: Document, job: IngestJob | None) -> DocumentOut:
    error = job.error_message if job is not None else None
    return DocumentOut(
        id=str(document.id),
        filename=document.filename,
        retrieval_enabled=document.retrieval_enabled,
        job_status=job.status if job is not None else IngestJobStatus.pending.value,
        error_message=error if error is None or error in SAFE_INGEST_ERRORS else "INGEST_FAILED",
        source_unit_count=document.source_unit_count,
        extracted_char_count=document.extracted_char_count,
        chunk_count=document.chunk_count,
        quality_warning=document.quality_warning,
        chunking_version=document.chunking_version,
    )


def _run_ingest(
    job_id: UUID,
    maker: SessionMaker,
    embedder: Embedder,
    batch_size: int,
    parse_limits: ParseLimits,
    low_text_chars: int,
) -> None:
    db = maker()
    try:
        process_ingest_job(
            db,
            job_id,
            embedder,
            batch_size=batch_size,
            parse_limits=parse_limits,
            low_text_chars=low_text_chars,
        )
    finally:
        db.close()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    session_maker: Annotated[SessionMaker, Depends(get_session_maker)],
    file: Annotated[UploadFile, File()],
) -> DocumentOut:
    original = Path(file.filename or "").name
    suffix = Path(original).suffix.lower()
    if not original or suffix not in _ALLOWED_SUFFIX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_UNSUPPORTED_FILE_TYPE,
        )
    data = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file too large")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    document_id = uuid4()
    try:
        dest = store_upload(
            settings.upload_dir,
            access.course.id,
            document_id,
            original,
            data,
        )
    except (StorageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload storage unavailable",
        ) from None

    document = Document(
        id=document_id,
        course_id=access.course.id,
        uploaded_by=access.user.id,
        filename=original,
        storage_path=str(dest),
    )
    job = IngestJob(document_id=document.id, status=IngestJobStatus.pending.value)
    db.add(document)
    db.add(job)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            delete_document_upload(
                settings.upload_dir,
                access.course.id,
                document_id,
                str(dest),
            )
        except StorageError as cleanup_error:
            logger.error(
                "storage_cleanup_failed scope=upload_compensation course_id=%s "
                "document_id=%s error_type=%s",
                access.course.id,
                document_id,
                type(cleanup_error).__name__,
            )
        raise
    db.refresh(document)
    db.refresh(job)
    background_tasks.add_task(
        _run_ingest,
        job.id,
        session_maker,
        embedder,
        settings.embedding_batch_size,
        parse_limits_from_settings(settings),
        settings.ingest_low_text_chars,
    )
    return _document_out(document, job)


@router.post("/{document_id}/retry", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def retry_document_ingest(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    session_maker: Annotated[SessionMaker, Depends(get_session_maker)],
) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None or document.course_id != access.course.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    job = latest_job(db, document.id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingest job is missing")
    stale_before = datetime.now(UTC) - timedelta(seconds=settings.ingest_stale_seconds)
    if not retry_ingest_job(db, job.id, stale_before):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingest job is active or already succeeded",
        )
    db.refresh(job)
    background_tasks.add_task(
        _run_ingest,
        job.id,
        session_maker,
        embedder,
        settings.embedding_batch_size,
        parse_limits_from_settings(settings),
        settings.ingest_low_text_chars,
    )
    return _document_out(document, job)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    access: Annotated[CourseAccess, Depends(require_course_member)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[DocumentOut]:
    documents = db.execute(
        select(Document)
        .where(Document.course_id == access.course.id)
        .order_by(Document.created_at)
    ).scalars().all()
    return [_document_out(doc, latest_job(db, doc.id)) for doc in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_member)],
    db: Annotated[DbSession, Depends(get_db)],
) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None or document.course_id != access.course.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _document_out(document, latest_job(db, document.id))


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: UUID,
    body: DocumentUpdateRequest,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None or document.course_id != access.course.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.retrieval_enabled = body.retrieval_enabled
    db.commit()
    db.refresh(document)
    return _document_out(document, latest_job(db, document.id))


@router.get("/{document_id}/content", response_class=FileResponse)
def get_document_content(
    document_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_member)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None or document.course_id != access.course.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        source = get_document_upload(
            settings.upload_dir,
            access.course.id,
            document.id,
            document.storage_path,
        )
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document content unavailable",
        ) from None
    suffix = Path(document.filename).suffix.lower()
    disposition = "inline" if suffix in {".pdf", ".md", ".markdown", ".txt"} else "attachment"
    return FileResponse(
        source,
        media_type=_CONTENT_TYPES.get(suffix, "application/octet-stream"),
        filename=document.filename,
        content_disposition_type=disposition,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    document = db.get(Document, document_id)
    if document is None or document.course_id != access.course.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    storage_path = document.storage_path
    # Keep the metadata/job until file cleanup succeeds so a failed DELETE can
    # be explicitly retried. Missing files are already idempotent in storage.
    try:
        delete_document_upload(
            settings.upload_dir,
            access.course.id,
            document_id,
            storage_path,
        )
    except StorageError as exc:
        logger.error(
            "storage_cleanup_failed scope=document course_id=%s document_id=%s error_type=%s",
            access.course.id,
            document_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage cleanup unavailable",
        ) from None
    db.execute(delete(Chunk).where(Chunk.document_id == document.id))
    db.execute(delete(IngestJob).where(IngestJob.document_id == document.id))
    db.delete(document)
    db.commit()
