from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import LoginRequest, UserOut
from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.security.deps import get_current_user
from app.security.passwords import verify_password
from app.security.sessions import (
    clear_session_cookie,
    create_session,
    get_valid_session,
    set_session_cookie,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), username=user.username, role=user.role,
                   full_name=user.full_name, student_number=user.student_number)


@router.post("/login", response_model=UserOut)
def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserOut:
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    session = create_session(db, user, settings)
    set_session_cookie(response, session, settings)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    session = get_valid_session(db, request.cookies.get(settings.session_cookie_name))
    if session is not None:
        db.delete(session)
        db.commit()
    clear_session_cookie(response, settings)


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return _user_out(user)
