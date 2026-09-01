from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import CreateUserRequest, UserOut
from app.db import get_db
from app.models.user import User
from app.security.deps import require_admin
from app.security.passwords import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), username=user.username, role=user.role)


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
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username taken") from None
    db.refresh(user)
    return _user_out(user)
