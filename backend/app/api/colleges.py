"""Administrator maintenance for display affiliations, not permission scopes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import College, Course, User
from app.security.deps import require_admin

router = APIRouter(prefix="/admin/colleges", tags=["admin-colleges"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


class CollegeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)


class CollegeOut(CollegeInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


def validate_college_id(db: Session, college_id: UUID | None) -> None:
    if college_id is not None and db.get(College, college_id) is None:
        raise HTTPException(404, "College not found")


def _get_college(db: Session, college_id: UUID) -> College:
    row = db.get(College, college_id)
    if row is None:
        raise HTTPException(404, "College not found")
    return row


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "College code conflict or affiliation exists") from None


@router.get("", response_model=list[CollegeOut])
def list_colleges(db: Db, _admin: Admin):
    return db.scalars(select(College).order_by(College.code)).all()


@router.post("", response_model=CollegeOut, status_code=201)
def create_college(body: CollegeInput, db: Db, _admin: Admin):
    row = College(**body.model_dump())
    db.add(row)
    _commit(db)
    return row


@router.put("/{college_id}", response_model=CollegeOut)
def update_college(college_id: UUID, body: CollegeInput, db: Db, _admin: Admin):
    row = _get_college(db, college_id)
    row.code, row.name = body.code, body.name
    _commit(db)
    return row


@router.delete("/{college_id}", status_code=204)
def delete_college(college_id: UUID, db: Db, _admin: Admin):
    row = _get_college(db, college_id)
    if (
        db.scalar(select(User.id).where(User.college_id == college_id).limit(1))
        or db.scalar(select(Course.id).where(Course.college_id == college_id).limit(1))
    ):
        raise HTTPException(409, "College is assigned to users or courses")
    db.delete(row)
    _commit(db)
