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
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker as SessionMaker

from app.api.schemas import DocumentOut, DocumentUpdateRequest
from app.config import Settings, get_settings
from app.db import get_db, get_session_maker
from app.models.course import CourseMember
from app.models.course_folder import CourseFolder
from app.models.document import Document, IngestJob, IngestJobStatus
from app.models.user import User
from app.security.deps import (
    CourseAccess,
    get_course_or_404,
    get_current_user,
    get_membership,
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
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
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


def require_document_access(
    course_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CourseAccess:
    """Admin visibility is limited to resource operations; Agent permissions stay unchanged."""
    course = get_course_or_404(db, course_id)
    member = get_membership(db, course_id, user.id)
    if user.role == "admin":
        member = CourseMember(course_id=course_id, user_id=user.id, role="teacher")
    if member is None:
        raise HTTPException(403, "Not a course member")
    return CourseAccess(course=course, member=member, user=user)


def visible_document(db: DbSession, document_id: UUID, access: CourseAccess) -> Document:
    document = db.get(Document, document_id)
    if (document is None or document.course_id != access.course.id
            or (not access.is_teacher and not document.retrieval_enabled)):
        raise HTTPException(404, "Document not found")
    return document


def _document_out(document: Document, job: IngestJob | None) -> DocumentOut:
    error = job.error_message if job is not None else None
    return DocumentOut(
        id=str(document.id),
        filename=document.filename,
        folder_id=str(document.folder_id) if document.folder_id else None,
        folder_name=document.folder.name if document.folder else None,
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
    folder_id: Annotated[UUID | None, Form()] = None,
) -> DocumentOut:
    folder = document_folder(db, access.course.id, folder_id)
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
        retrieval_enabled=False,
        folder=folder,
    )
    db.add(document)
    try:
        # Flush document first so ingest_jobs.document_id FK is satisfied
        # (IngestJob has no relationship(); bare UUID does not create UOW dependency).
        db.flush()
        job = IngestJob(document_id=document.id, status=IngestJobStatus.pending.value)
        db.add(job)
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
    access: Annotated[CourseAccess, Depends(require_document_access)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[DocumentOut]:
    documents = db.execute(
        select(Document)
        .where(Document.course_id == access.course.id,
               True if access.is_teacher else Document.retrieval_enabled.is_(True))
        .order_by(Document.created_at)
    ).scalars().all()
    return [_document_out(doc, latest_job(db, doc.id)) for doc in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    access: Annotated[CourseAccess, Depends(require_document_access)],
    db: Annotated[DbSession, Depends(get_db)],
) -> DocumentOut:
    document = visible_document(db, document_id, access)
    return _document_out(document, latest_job(db, document.id))


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: UUID,
    body: DocumentUpdateRequest,
    access: Annotated[CourseAccess, Depends(require_document_access)],
    db: Annotated[DbSession, Depends(get_db)],
) -> DocumentOut:
    if not access.is_teacher:
        raise HTTPException(403, "Course teacher or admin only")
    if body.retrieval_enabled and access.user.role != "admin":
        raise HTTPException(403, "Admin only")
    document = visible_document(db, document_id, access)
    if "folder_id" in body.model_fields_set:
        document.folder = document_folder(db, access.course.id, body.folder_id)
    if "retrieval_enabled" in body.model_fields_set:
        document.retrieval_enabled = body.retrieval_enabled
    db.commit()
    db.refresh(document)
    return _document_out(document, latest_job(db, document.id))


def document_folder(db: DbSession, course_id: UUID, folder_id: UUID | None) -> CourseFolder | None:
    if folder_id is None:
        return None
    folder = db.scalar(
        select(CourseFolder).where(
            CourseFolder.id == folder_id, CourseFolder.course_id == course_id,
        ).with_for_update()
    )
    if folder is None:
        raise HTTPException(404, "Folder not found")
    return folder


@router.get("/{document_id}/content", response_class=FileResponse)
def get_document_content(
    document_id: UUID,
    access: Annotated[CourseAccess, Depends(require_document_access)],
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    document = visible_document(db, document_id, access)
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
    access: Annotated[CourseAccess, Depends(require_document_access)],
    db: Annotated[DbSession, Depends(get_db)],
) -> None:
    if not access.is_teacher:
        raise HTTPException(403, "Course teacher or admin only")
    document = visible_document(db, document_id, access)
    # Soft removal keeps the source and ingestion records. All evidence readers
    # already enforce this flag; only an administrator may enable it again.
    document.retrieval_enabled = False
    db.commit()
