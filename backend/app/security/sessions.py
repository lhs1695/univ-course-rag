import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.models.session import Session
from app.models.user import User


def create_session(db: DbSession, user: User, settings: Settings) -> Session:
    session = Session(
        id=uuid.uuid4(),
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def set_session_cookie(response: Response, session: Session, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=str(session.id),
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )


def get_valid_session(db: DbSession, session_id: str | None) -> Session | None:
    if not session_id:
        return None
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return None
    row = db.get(Session, sid)
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        return None
    return row
