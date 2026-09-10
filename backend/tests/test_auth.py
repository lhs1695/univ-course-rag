from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.session import Session as AuthSession
from app.models.user import UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user


def add_session(db: Session, user_id: UUID, expires_at: datetime) -> AuthSession:
    session = AuthSession(user_id=user_id, expires_at=expires_at)
    db.add(session)
    db.commit()
    return session


def test_login_wrong_password(client: TestClient, db: Session) -> None:
    add_user(db, "student", "correct-password", UserRole.student)
    response = client.post(
        "/auth/login",
        json={"username": "student", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert client.cookies.get("session_id") is None


def test_me_without_cookie_is_401(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_login_sets_httponly_cookie_and_me(client: TestClient, db: Session) -> None:
    add_user(db, "teacher", "teacher-pass", UserRole.teacher)
    login = client.post(
        "/auth/login",
        json={"username": "teacher", "password": "teacher-pass"},
    )
    assert login.status_code == 200
    assert login.json()["username"] == "teacher"
    assert login.json()["role"] == "teacher"
    cookie = login.headers.get("set-cookie", "")
    assert "session_id=" in cookie.lower()
    assert "httponly" in cookie.lower()
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.headers.get("X-Request-ID")
    assert me.json()["username"] == "teacher"
    assert me.json()["role"] == "teacher"


def test_logout_then_me_is_401(client: TestClient, db: Session) -> None:
    add_user(db, "student", "student-pass", UserRole.student)
    client.post("/auth/login", json={"username": "student", "password": "student-pass"})
    assert client.get("/auth/me").status_code == 200
    logout = client.post("/auth/logout")
    assert logout.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_login_cleanup_preserves_valid_sessions(
    client: TestClient, db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("SESSION_CLEANUP_BATCH_SIZE", "2")
    user = add_user(db, "student", "student-pass", UserRole.student)
    expired = add_session(db, user.id, datetime.now(UTC) - timedelta(minutes=1))
    valid = add_session(db, user.id, datetime.now(UTC) + timedelta(minutes=1))

    response = client.post("/auth/login", json={"username": "student", "password": "student-pass"})

    assert response.status_code == 200
    assert db.get(AuthSession, expired.id) is None
    assert db.get(AuthSession, valid.id) is not None


def test_login_cleanup_is_bounded_and_runs_in_later_batches(
    client: TestClient, db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("SESSION_CLEANUP_BATCH_SIZE", "2")
    user = add_user(db, "student", "student-pass", UserRole.student)
    expired = [
        add_session(db, user.id, datetime.now(UTC) - timedelta(minutes=minutes))
        for minutes in (3, 2, 1)
    ]

    assert client.post("/auth/login", json={"username": "student", "password": "student-pass"}).status_code == 200
    remaining = [session for session in expired if db.get(AuthSession, session.id) is not None]
    assert len(remaining) == 1
    assert remaining[0].id == expired[2].id

    assert client.post("/auth/login", json={"username": "student", "password": "student-pass"}).status_code == 200
    assert db.get(AuthSession, expired[2].id) is None


def test_expired_current_session_is_unauthenticated_without_cleanup(
    client: TestClient, db: Session
) -> None:
    user = add_user(db, "student", "student-pass", UserRole.student)
    expired = add_session(db, user.id, datetime.now(UTC) - timedelta(minutes=1))
    client.cookies.set("session_id", str(expired.id))

    assert client.get("/auth/me").status_code == 401
    assert db.get(AuthSession, expired.id) is not None


def test_malformed_session_cookie_is_unauthenticated(client: TestClient) -> None:
    client.cookies.set("session_id", "not-a-uuid")
    assert client.get("/auth/me").status_code == 401


def test_only_admin_creates_users(client: TestClient, db: Session) -> None:
    add_user(db, "admin", "admin-pass", UserRole.admin)
    add_user(db, "student", "student-pass", UserRole.student)

    unauth = client.post(
        "/admin/users",
        json={"username": "newone", "password": "x", "role": "student"},
    )
    assert unauth.status_code == 401

    client.post("/auth/login", json={"username": "student", "password": "student-pass"})
    forbidden = client.post(
        "/admin/users",
        json={"username": "newone", "password": "x", "role": "student"},
    )
    assert forbidden.status_code == 403

    client.post("/auth/logout")
    client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})
    created = client.post(
        "/admin/users",
        json={"username": "newone", "password": "x", "role": "teacher"},
    )
    assert created.status_code == 201
    assert created.json()["username"] == "newone"
    assert created.json()["role"] == "teacher"
    assert "password" not in created.json()
