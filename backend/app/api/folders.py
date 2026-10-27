from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.api.documents import document_folder, require_document_access
from app.api.schemas import FolderCreateRequest, FolderOut, FolderUpdateRequest
from app.db import get_db
from app.models.course_folder import CourseFolder
from app.models.document import Document
from app.security.deps import CourseAccess

router = APIRouter(prefix="/courses/{course_id}/folders", tags=["folders"])
Access = Annotated[CourseAccess, Depends(require_document_access)]
Database = Annotated[DbSession, Depends(get_db)]


def _teacher(access: CourseAccess) -> None:
    if not access.is_teacher:
        raise HTTPException(403, "Course teacher or admin only")


def _out(folder: CourseFolder) -> FolderOut:
    return FolderOut(
        id=str(folder.id), course_id=str(folder.course_id),
        parent_id=str(folder.parent_id) if folder.parent_id else None,
        name=folder.name, created_at=folder.created_at,
    )


def _commit(db: DbSession) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Folder name already exists") from None


@router.get("", response_model=list[FolderOut])
def list_folders(access: Access, db: Database) -> list[FolderOut]:
    return [_out(folder) for folder in db.scalars(
        select(CourseFolder).where(CourseFolder.course_id == access.course.id)
        .order_by(CourseFolder.created_at, CourseFolder.name, CourseFolder.id)
    )]


@router.post("", response_model=FolderOut, status_code=201)
def create_folder(body: FolderCreateRequest, access: Access, db: Database) -> FolderOut:
    _teacher(access)
    parent = document_folder(db, access.course.id, body.parent_id)
    if parent is not None and parent.parent_id is not None:
        raise HTTPException(400, "Folder depth cannot exceed two levels")
    folder = CourseFolder(course_id=access.course.id, parent_id=body.parent_id, name=body.name)
    db.add(folder)
    _commit(db)
    db.refresh(folder)
    return _out(folder)


@router.patch("/{folder_id}", response_model=FolderOut)
def update_folder(folder_id: UUID, body: FolderUpdateRequest, access: Access, db: Database) -> FolderOut:
    _teacher(access)
    folder = document_folder(db, access.course.id, folder_id)
    if "parent_id" in body.model_fields_set:
        parent = document_folder(db, access.course.id, body.parent_id)
        if parent is not None:
            if parent.id == folder.id:
                raise HTTPException(400, "Folder cannot be its own parent")
            if parent.parent_id is not None:
                raise HTTPException(400, "Folder depth cannot exceed two levels")
            child = db.scalar(select(CourseFolder.id).where(
                CourseFolder.parent_id == folder.id,
            ).limit(1))
            if child is not None:
                raise HTTPException(400, "Folder with children must remain at root")
        folder.parent_id = body.parent_id
    if "name" in body.model_fields_set:
        folder.name = body.name
    _commit(db)
    db.refresh(folder)
    return _out(folder)


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: UUID, access: Access, db: Database) -> None:
    _teacher(access)
    folder = document_folder(db, access.course.id, folder_id)
    child = db.scalar(select(CourseFolder.id).where(CourseFolder.parent_id == folder_id).limit(1))
    document = db.scalar(select(Document.id).where(Document.folder_id == folder_id).limit(1))
    if child is not None or document is not None:
        raise HTTPException(409, "Folder is not empty")
    db.delete(folder)
    db.commit()
