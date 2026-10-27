"""Course folder behavior using isolated database and fake upload processing."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.api import documents
from app.config import Settings, get_settings
from app.db import get_db, get_session_maker
from app.main import app
from app.models import Course, CourseFolder, CourseMember
from app.models.user import UserRole
from app.services.embedder import FakeEmbedder, get_embedder
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from tests.conftest import TestingSessionLocal, add_user


@pytest.fixture
def client(db, monkeypatch):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_session_maker] = lambda: TestingSessionLocal
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, llm_backend="fake", embedder_backend="fake",
    )
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    monkeypatch.setattr(documents, "store_upload", lambda *args: Path("isolated-folder.pdf"))
    monkeypatch.setattr(documents, "_run_ingest", lambda *args: None)
    try:
        with TestClient(app) as browser:
            yield browser
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def scope(db):
    people = {
        role: add_user(db, role, "pass", UserRole(role))
        for role in ["admin", "teacher", "student"]
    }
    people["other"] = add_user(db, "other", "pass", UserRole.teacher)
    course, other = Course(title="本课"), Course(title="他课")
    db.add_all([course, other])
    db.flush()
    db.add_all([
        CourseMember(course_id=course.id, user_id=people["teacher"].id, role="teacher"),
        CourseMember(course_id=course.id, user_id=people["student"].id, role="student"),
        CourseMember(course_id=other.id, user_id=people["other"].id, role="teacher"),
    ])
    db.commit()
    return SimpleNamespace(people=people, course=course, other=other)


def login(client, role):
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"username": role, "password": "pass"}).status_code == 200


def root(scope):
    return f"/courses/{scope.course.id}"


def create(client, scope, name="讲义", parent_id=None):
    response = client.post(root(scope) + "/folders", json={"name": name, "parent_id": parent_id})
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, scope, folder_id=None):
    return client.post(
        root(scope) + "/documents",
        data={"folder_id": folder_id} if folder_id else {},
        files={"file": ("lesson.pdf", b"fake isolated bytes", "application/pdf")},
    )


def test_crud_depth_and_nonempty_children(client, scope):
    login(client, "teacher")
    parent = create(client, scope, "  讲义  ")
    assert parent["name"] == "讲义" and parent["parent_id"] is None
    assert parent["course_id"] == str(scope.course.id) and parent["created_at"]
    child = create(client, scope, "第一章", parent["id"])
    path = root(scope) + "/folders"
    assert client.post(path, json={"name": "第三层", "parent_id": child["id"]}).status_code == 400
    assert client.patch(path + "/" + parent["id"], json={"name": "讲义", "parent_id": child["id"]}).status_code == 422
    assert client.delete(path + "/" + parent["id"]).status_code == 409
    assert client.patch(path + "/" + child["id"], json={"name": "绪论"}).json()["name"] == "绪论"
    assert len(client.get(path).json()) == 2
    assert client.delete(path + "/" + child["id"]).status_code == 204
    assert client.delete(path + "/" + parent["id"]).status_code == 204
    assert client.get(path).json() == []
    assert client.delete(path + "/" + parent["id"]).status_code == 404


def test_name_uniqueness_and_rename_conflict(client, scope):
    login(client, "teacher")
    first = create(client, scope)
    second = create(client, scope, "练习")
    path = root(scope) + "/folders"
    assert client.post(path, json={"name": "讲义"}).status_code == 409
    assert client.patch(path + "/" + second["id"], json={"name": "讲义"}).status_code == 409
    create(client, scope, "第一章", first["id"])
    assert client.post(path, json={"name": "第一章", "parent_id": first["id"]}).status_code == 409
    create(client, scope, "第一章", second["id"])
    assert len(client.get(path).json()) == 4


@pytest.mark.parametrize("name", ["", "   ", "长" * 101, None])
def test_invalid_names(client, scope, name):
    login(client, "teacher")
    folder = create(client, scope)
    path = root(scope) + "/folders"
    assert client.post(path, json={"name": name}).status_code == 422
    assert client.patch(path + "/" + folder["id"], json={"name": name}).status_code == 422


@pytest.mark.parametrize("role,read_status,write_status", [
    (None, 401, 401), ("student", 200, 403), ("other", 403, 403), ("admin", 200, 200),
])
def test_permissions(client, scope, role, read_status, write_status):
    login(client, "teacher")
    folder = create(client, scope)
    if role:
        login(client, role)
    else:
        client.post("/auth/logout")
    path = root(scope) + "/folders"
    assert client.get(path).status_code == read_status
    expected_create = 201 if write_status == 200 else write_status
    assert client.post(path, json={"name": "练习"}).status_code == expected_create
    assert client.patch(path + "/" + folder["id"], json={"name": "更新"}).status_code == write_status
    expected_delete = 204 if write_status == 200 else write_status
    assert client.delete(path + "/" + folder["id"]).status_code == expected_delete


def test_cross_course_and_missing_folder_rejected(client, scope):
    login(client, "other")
    foreign = client.post(f"/courses/{scope.other.id}/folders", json={"name": "他课资料"}).json()
    login(client, "teacher")
    doc = upload(client, scope).json()
    login(client, "admin")
    path = root(scope) + "/folders"
    for folder_id in [foreign["id"], str(uuid4())]:
        assert client.post(path, json={"name": "子夹", "parent_id": folder_id}).status_code == 404
        assert client.patch(path + "/" + folder_id, json={"name": "改名"}).status_code == 404
        assert client.delete(path + "/" + folder_id).status_code == 404
        login(client, "teacher")
        assert upload(client, scope, folder_id).status_code == 404
        login(client, "admin")
        assert client.patch(root(scope) + "/documents/" + doc["id"], json={"folder_id": folder_id}).status_code == 404
    assert len(client.get(root(scope) + "/documents").json()) == 1


def test_upload_move_out_fields_and_retrieval_permissions(client, scope):
    login(client, "teacher")
    parent = create(client, scope)
    child = create(client, scope, "第一章", parent["id"])
    uploaded = upload(client, scope, child["id"])
    assert uploaded.status_code == 201
    doc = uploaded.json()
    assert (doc["folder_id"], doc["folder_name"], doc["retrieval_enabled"]) == (child["id"], "第一章", False)
    path = root(scope) + "/documents/" + doc["id"]
    assert client.delete(root(scope) + "/folders/" + child["id"]).status_code == 409
    assert client.patch(path, json={"retrieval_enabled": True, "folder_id": parent["id"]}).status_code == 403
    assert client.get(path).json()["folder_id"] == child["id"]
    login(client, "admin")
    assert client.patch(path, json={"retrieval_enabled": True}).json()["folder_id"] == child["id"]
    login(client, "teacher")
    moved = client.patch(path, json={"folder_id": parent["id"]}).json()
    assert moved["folder_name"] == "讲义" and moved["retrieval_enabled"] is True
    renamed = client.patch(root(scope) + "/folders/" + parent["id"], json={"name": "新讲义"})
    assert renamed.status_code == 200
    assert client.get(root(scope) + "/documents").json()[0]["folder_name"] == "新讲义"
    login(client, "student")
    assert client.get(path).json()["folder_name"] == "新讲义"
    assert client.patch(path, json={"folder_id": None}).status_code == 403
    assert upload(client, scope, parent["id"]).status_code == 403
    login(client, "teacher")
    ungrouped = client.patch(path, json={"folder_id": None}).json()
    assert ungrouped["folder_id"] is None and ungrouped["folder_name"] is None
    assert ungrouped["retrieval_enabled"] is True
    assert client.patch(path, json={"retrieval_enabled": False, "folder_id": child["id"]}).json()["retrieval_enabled"] is False
    login(client, "student")
    assert client.get(root(scope) + "/documents").json() == []
    assert client.get(path).status_code == 404


def test_upload_ungrouped_and_invalid_patch(client, scope):
    login(client, "teacher")
    result = upload(client, scope)
    assert result.status_code == 201
    assert result.json()["folder_id"] is None and result.json()["folder_name"] is None
    path = root(scope) + "/documents/" + result.json()["id"]
    for body in [{}, {"retrieval_enabled": None}, {"retrieval_enabled": "true"}, {"folder_id": "invalid"}]:
        assert client.patch(path, json=body).status_code == 422


def test_model_root_name_uniqueness(db, scope):
    db.add(CourseFolder(course_id=scope.course.id, name="重复"))
    db.commit()
    with pytest.raises(IntegrityError):
        db.add(CourseFolder(course_id=scope.course.id, name="重复"))
        db.commit()
    db.rollback()
