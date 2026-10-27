"""Isolated Fake-only PLAN-17 API permissions, CSV and evidence gates."""

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.api import documents
from app.config import Settings, get_settings
from app.db import get_db, get_session_maker
from app.main import app
from app.models import Chunk, Course, CourseClass, CourseMember, Document
from app.models.user import UserRole
from app.services.embedder import FakeEmbedder, get_embedder
from app.services.llm import FakeLLM, get_llm
from app.services.retrieve import retrieve_chunks
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingSessionLocal, add_user


@pytest.fixture
def client(db, monkeypatch):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_session_maker] = lambda: TestingSessionLocal
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, llm_backend="fake", embedder_backend="fake"
    )
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    # Upload bytes and background ingestion are isolated from disk/providers.
    monkeypatch.setattr(
        documents, "store_upload", lambda *args: Path("isolated-fixture.pdf")
    )
    monkeypatch.setattr(
        documents,
        "get_document_upload",
        lambda *args: Path(__file__).parent / "fixtures/sample.pdf",
    )
    monkeypatch.setattr(documents, "_run_ingest", lambda *args: None)
    with TestClient(app) as browser:
        yield browser
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.fixture
def scope(db):
    people = {
        role: add_user(db, role, "pass", UserRole(role))
        for role in ["admin", "teacher", "student"]
    }
    people["other"] = add_user(db, "other", "pass", UserRole.teacher)
    people["student"].full_name = "张同学"
    people["student"].student_number = "00123"
    course = Course(title="测试课程")
    other = Course(title="他课")
    db.add_all([course, other])
    db.flush()
    db.add_all(
        [
            CourseMember(
                course_id=course.id, user_id=people["teacher"].id, role="teacher"
            ),
            CourseMember(
                course_id=other.id, user_id=people["other"].id, role="teacher"
            ),
        ]
    )
    db.commit()
    return SimpleNamespace(people=people, course=course, other=other)


def login(client, role):
    client.post("/auth/logout")
    response = client.post("/auth/login", json={"username": role, "password": "pass"})
    assert response.status_code == 200


def roster(client, course, text):
    return client.post(
        f"/courses/{course.id}/roster",
        files={"file": ("roster.csv", text.encode("utf-8-sig"), "text/csv")},
    )


@pytest.mark.parametrize("role", ["teacher", "student", "other"])
def test_semesters_admin_only(client, scope, role):
    login(client, role)
    body = {"name": "秋季", "starts_on": "2026-09-01", "ends_on": "2027-01-01"}
    assert client.get("/admin/semesters").status_code == 403
    assert client.post("/admin/semesters", json=body).status_code == 403
    assert client.put(f"/admin/semesters/{uuid4()}", json=body).status_code == 403
    assert client.delete(f"/admin/semesters/{uuid4()}").status_code == 403


def test_semester_crud_and_course_assignment(client, scope):
    login(client, "admin")
    body = {"name": " 秋季 ", "starts_on": "2026-09-01", "ends_on": "2027-01-01"}
    assert (
        client.post(
            "/admin/semesters", json={**body, "ends_on": "2026-08-01"}
        ).status_code
        == 422
    )
    row = client.post("/admin/semesters", json=body)
    assert row.status_code == 201 and row.json()["name"] == "秋季"
    sid = row.json()["id"]
    assert client.post("/admin/semesters", json=body).status_code == 409
    assert client.get("/admin/semesters").json()[0]["id"] == sid
    assert (
        client.put(
            f"/admin/semesters/{sid}", json={**body, "name": "秋学期"}
        ).status_code
        == 200
    )
    path = f"/admin/courses/{scope.course.id}"
    assert client.patch(path, json={"semester_id": sid}).json()["semester_id"] == sid
    assert client.patch(path, json={"title": "更名"}).json()["semester_id"] == sid
    assert client.patch(path, json={"semester_id": str(uuid4())}).status_code == 404
    assert client.patch(path, json={"title": None}).status_code == 422
    assert client.delete(f"/admin/semesters/{sid}").status_code == 409
    assert client.patch(path, json={"semester_id": None}).json()["semester_id"] is None
    assert client.delete(f"/admin/semesters/{sid}").status_code == 204


@pytest.mark.parametrize(
    "role,allowed",
    [("admin", True), ("teacher", True), ("student", False), ("other", False)],
)
def test_classes_roster_permission_matrix(client, scope, role, allowed):
    login(client, role)
    root = f"/courses/{scope.course.id}"
    assert client.get(root + "/classes").status_code == (200 if allowed else 403)
    assert client.post(root + "/classes", json={"name": "一班"}).status_code == (
        201 if allowed else 403
    )
    response = roster(client, scope.course, "学号,姓名,班级\n00123,张同学,一班\n")
    assert response.status_code == (200 if allowed else 403)
    if allowed:
        assert response.json()["imported"] == 1


def test_roster_summary_idempotency_conflicts_profile(client, db, scope):
    login(client, "teacher")
    # Blank line and duplicate occurrences are reported, never silently imported.
    response = roster(
        client,
        scope.course,
        "学号,姓名,班级\n\n00123,张同学,一班\n00123,张同学,二班\n99999,缺账号,一班\n缺字段\n",
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["imported"], body["rejected"]) == (5, 0, 5)
    assert [e["code"] for e in body["errors"]] == [
        "empty_row",
        "duplicate_student_number",
        "duplicate_student_number",
        "student_account_missing",
        "invalid_fields",
    ]
    assert (
        db.scalar(
            select(CourseMember).where(
                CourseMember.user_id == scope.people["student"].id
            )
        )
        is None
    )
    text = "学号,姓名,班级\n00123,张同学,一班\n"
    assert roster(client, scope.course, text).json()["imported"] == 1
    assert roster(client, scope.course, text).json()["unchanged"] == 1
    assert (
        roster(client, scope.course, text.replace("一班", "二班")).json()["errors"][0][
            "code"
        ]
        == "membership_conflict"
    )
    assert (
        roster(client, scope.course, text.replace("张同学", "错名")).json()["errors"][
            0
        ]["code"]
        == "name_mismatch"
    )
    klass = client.get(f"/courses/{scope.course.id}/classes").json()[0]
    assert klass["student_count"] == 1
    assert (
        client.delete(f"/courses/{scope.course.id}/classes/{klass['id']}").status_code
        == 409
    )
    member = client.get(f"/courses/{scope.course.id}/members").json()
    assert next(m for m in member if m["role"] == "student")["class_name"] == "一班"
    login(client, "student")
    profile = client.get("/auth/profile").json()
    assert set(profile) == {
        "full_name", "student_number", "employee_number", "role", "classes",
        "college_id", "college_name",
    }
    assert profile == {
        "college_id": None,
        "college_name": None,
        "full_name": "张同学",
        "student_number": "00123",
        "employee_number": None,
        "role": "student",
        "classes": [{"course_title": "测试课程", "class_name": "一班"}],
    }
    # Course members who are students still cannot import or maintain classes.
    assert roster(client, scope.course, text).status_code == 403
    login(client, "teacher")
    assert (
        client.delete(
            f"/courses/{scope.course.id}/members/{scope.people['student'].id}"
        ).status_code
        == 204
    )
    login(client, "student")
    assert client.get("/auth/profile").json()["classes"] == []


def test_class_scope_crud_and_no_cross_course_import(client, scope):
    login(client, "admin")
    foreign = client.post(
        f"/courses/{scope.other.id}/classes", json={"name": "他课班"}
    ).json()["id"]
    login(client, "teacher")
    root = f"/courses/{scope.course.id}/classes"
    row = client.post(root, json={"name": "一班"}).json()
    assert client.post(root, json={"name": "一班"}).status_code == 409
    assert (
        client.put(root + "/" + row["id"], json={"name": "新班"}).json()["name"]
        == "新班"
    )
    assert client.put(root + "/" + foreign, json={"name": "越权"}).status_code == 404
    assert client.delete(root + "/" + foreign).status_code == 404
    assert (
        roster(client, scope.other, "学号,姓名,班级\n00123,张同学,一班").status_code
        == 403
    )
    assert client.delete(root + "/" + row["id"]).status_code == 204


@pytest.mark.parametrize(
    "text",
    [
        "",
        "学号,姓名,班级\n",
        "姓名,学号,班级\n张同学,00123,一班",
        '学号,姓名,班级\n"unfinished',
    ],
)
def test_csv_bad_format(client, scope, text):
    login(client, "teacher")
    assert roster(client, scope.course, text).status_code == 422


def test_admin_profile_management_and_identity_reuse(client, db, scope):
    uid = scope.people["student"].id
    login(client, "teacher")
    assert (
        client.patch(f"/admin/users/{uid}", json={"full_name": "改名"}).status_code
        == 403
    )
    login(client, "admin")
    created = client.post(
        "/admin/users",
        json={
            "username": "student2",
            "password": "pass",
            "role": "student",
            "full_name": "李同学",
            "student_number": "00002",
        },
    )
    assert created.status_code == 201 and created.json()["student_number"] == "00002"
    assert (
        client.patch(
            f"/admin/users/{uid}", json={"student_number": "00002"}
        ).status_code
        == 409
    )
    assert (
        client.patch(f"/admin/users/{uid}", json={"full_name": "张三"}).json()[
            "full_name"
        ]
        == "张三"
    )
    assert (
        roster(client, scope.course, "学号,姓名,班级\n00123,张三,一班").json()[
            "imported"
        ]
        == 1
    )
    db.refresh(scope.people["student"])
    assert scope.people["student"].role == "student"


@pytest.mark.parametrize("strategy", ["dense", "hybrid"])
def test_upload_admin_enable_retrieval_gate(client, db, scope, strategy):
    login(client, "teacher")
    root = f"/courses/{scope.course.id}"
    uploaded = client.post(
        root + "/documents",
        files={"file": ("pending.pdf", b"fake isolated bytes", "application/pdf")},
    )
    assert uploaded.status_code == 201 and uploaded.json()["retrieval_enabled"] is False
    did = UUID(uploaded.json()["id"])
    embedder = FakeEmbedder()
    text = "PLAN17 evidence unique token"
    chunk = Chunk(
        course_id=scope.course.id,
        document_id=did,
        page=2,
        text=text,
        embedding=embedder.embed([text])[0],
        embedding_model=embedder.index_identity,
    )
    db.add(chunk)
    db.commit()
    assert retrieve_chunks(db, scope.course.id, text, embedder, strategy=strategy) == []
    path = root + f"/documents/{did}"
    assert client.patch(path, json={"retrieval_enabled": True}).status_code == 403
    login(client, "other")
    assert client.get(root + "/documents").status_code == 403
    assert client.patch(path, json={"retrieval_enabled": False}).status_code == 403
    db.add(
        CourseMember(
            course_id=scope.course.id,
            user_id=scope.people["student"].id,
            role="student",
        )
    )
    db.commit()
    login(client, "student")
    assert client.get(root + "/documents").json() == []
    assert (
        client.get(path).status_code == client.get(path + "/content").status_code == 404
    )
    assert client.patch(path, json={"retrieval_enabled": False}).status_code == 403
    login(client, "admin")
    assert client.get(root + "/documents").json()[0]["id"] == str(did)
    assert client.get(path).status_code == 200  # Admin has no course membership.
    assert client.get(path + "/content").content.startswith(b"%PDF")
    assert (
        client.patch(
            f"/courses/{scope.other.id}/documents/{did}",
            json={"retrieval_enabled": True},
        ).status_code
        == 404
    )
    assert client.patch(path, json={"retrieval_enabled": True}).status_code == 200
    assert (
        retrieve_chunks(db, scope.course.id, text, embedder, strategy=strategy)[
            0
        ].document_id
        == did
    )
    login(client, "student")
    assert client.get(path + "/content").content.startswith(b"%PDF")
    login(client, "teacher")
    assert client.delete(path).status_code == 204
    assert db.get(Document, did) is not None and db.get(Chunk, chunk.id) is not None
    assert retrieve_chunks(db, scope.course.id, text, embedder, strategy=strategy) == []


def test_anonymous_profile_and_business_denied(client, scope):
    assert client.get("/auth/profile").status_code == 401
    assert client.get("/admin/semesters").status_code == 401
    assert client.get(f"/courses/{scope.course.id}/classes").status_code == 401


def test_csv_partial_success_and_no_nonstudent_enrollment(client, db, scope):
    login(client, "teacher")
    scope.people["other"].student_number = "T001"
    scope.people["other"].full_name = "教师"
    db.commit()
    body = roster(
        client,
        scope.course,
        "学号,姓名,班级\n00123,张同学,一班\n999,无账号,一班\nT001,教师,一班",
    ).json()
    assert (body["total"], body["imported"], body["rejected"]) == (3, 1, 2)
    assert [e["code"] for e in body["errors"]] == [
        "student_account_missing",
        "not_student",
    ]


def test_roster_constraint_race_rolls_back_import(client, db, scope, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    login(client, "teacher")
    original = db.flush

    def conflicting_flush(*args, **kwargs):
        if any(isinstance(row, CourseMember) for row in db.new):
            raise IntegrityError("synthetic concurrent member", {}, None)
        return original(*args, **kwargs)

    monkeypatch.setattr(db, "flush", conflicting_flush)
    assert (
        roster(client, scope.course, "学号,姓名,班级\n00123,张同学,一班").status_code
        == 409
    )
    assert db.scalar(select(CourseClass)) is None
    assert (
        db.scalar(
            select(CourseMember).where(
                CourseMember.user_id == scope.people["student"].id
            )
        )
        is None
    )
