from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.api.colleges import validate_college_id
from app.api.schemas import CreateUserRequest, UserOut
from app.db import get_db
from app.models.user import User
from app.security.deps import require_admin
from app.security.passwords import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), username=user.username, role=user.role,
                   full_name=user.full_name, student_number=user.student_number,
                   employee_number=user.employee_number, college_id=user.college_id,
                   college_name=user.college.name if user.college else None)


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> list[UserOut]:
    rows = db.execute(select(User).order_by(User.created_at)).scalars().all()
    return [_user_out(user) for user in rows]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateUserRequest,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> UserOut:
    validate_college_id(db, body.college_id)
    user = User(
        college_id=body.college_id,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role.value,
        full_name=body.full_name.strip() if body.full_name else None,
        student_number=body.student_number,
        employee_number=body.employee_number,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username, student number or employee number taken") from None
    db.refresh(user)
    return _user_out(user)


class UserProfileUpdate(BaseModel):
    college_id: UUID | None = None
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    student_number: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    employee_number: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user_profile(user_id: UUID, body: UserProfileUpdate,
                        db: Annotated[DbSession, Depends(get_db)],
                        _admin: Annotated[User, Depends(require_admin)]):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    validate_college_id(db, body.college_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username, student number or employee number taken") from None
    db.refresh(user)
    return _user_out(user)
