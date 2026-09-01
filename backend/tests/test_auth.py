from app.models.user import UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user


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
    assert me.json()["username"] == "teacher"
    assert me.json()["role"] == "teacher"


def test_logout_then_me_is_401(client: TestClient, db: Session) -> None:
    add_user(db, "student", "student-pass", UserRole.student)
    client.post("/auth/login", json={"username": "student", "password": "student-pass"})
    assert client.get("/auth/me").status_code == 200
    logout = client.post("/auth/logout")
    assert logout.status_code == 204
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
