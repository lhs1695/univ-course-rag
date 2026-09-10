import logging
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.document import Document
from app.models.user import UserRole
from app.services.storage import (
    StorageBoundaryError,
    StorageError,
    delete_document_upload,
    get_document_upload,
    store_upload,
)
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user


def login_as(client: TestClient, username: str, password: str) -> None:
    client.post("/auth/logout")
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def add_course(db: Session, title: str) -> Course:
    course = Course(title=title)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def add_teacher_member(db: Session, course: Course, teacher_id: UUID) -> None:
    db.add(
        CourseMember(
            course_id=course.id,
            user_id=teacher_id,
            role=CourseMemberRole.teacher.value,
        )
    )
    db.commit()


def add_member(
    db: Session,
    course: Course,
    user_id: UUID,
    role: CourseMemberRole,
) -> None:
    db.add(CourseMember(course_id=course.id, user_id=user_id, role=role.value))
    db.commit()


def test_document_delete_is_confined_to_expected_course_and_document(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    course_id = uuid4()
    document_id = uuid4()
    other_course_id = uuid4()
    target = store_upload(upload_dir, other_course_id, document_id, "other.txt", b"keep")

    with pytest.raises(StorageBoundaryError, match="outside"):
        delete_document_upload(
            upload_dir,
            course_id,
            document_id,
            str(target),
        )

    assert target.read_bytes() == b"keep"


def test_document_delete_rejects_path_outside_upload_root(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"keep")

    with pytest.raises(StorageBoundaryError, match="outside"):
        delete_document_upload(upload_dir, uuid4(), uuid4(), str(outside))

    assert outside.read_bytes() == b"keep"


def test_store_upload_rejects_traversal_filename(tmp_path: Path) -> None:
    with pytest.raises(StorageBoundaryError, match="filename"):
        store_upload(tmp_path / "uploads", uuid4(), uuid4(), "../escape.txt", b"keep")

    assert not (tmp_path / "escape.txt").exists()


def test_get_document_upload_rejects_other_document_directory(tmp_path: Path) -> None:
    course_id = uuid4()
    document_id = uuid4()
    other_document_id = uuid4()
    target = store_upload(tmp_path, course_id, other_document_id, "other.txt", b"keep")

    with pytest.raises(StorageBoundaryError, match="outside"):
        get_document_upload(tmp_path, course_id, document_id, str(target))


def test_course_members_can_read_document_content(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher.id, CourseMemberRole.teacher)
    add_member(db, course, student.id, CourseMemberRole.student)
    login_as(client, teacher.username, "pass")
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("note.txt", b"bounded source", "text/plain")},
    )
    document_id = uploaded.json()["id"]

    teacher_response = client.get(f"/courses/{course.id}/documents/{document_id}/content")
    login_as(client, student.username, "pass")
    student_response = client.get(f"/courses/{course.id}/documents/{document_id}/content")

    for response in (teacher_response, student_response):
        assert response.status_code == 200
        assert response.content == b"bounded source"
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-disposition"].startswith("inline;")
        assert "note.txt" in response.headers["content-disposition"]


def test_document_content_requires_authentication(client: TestClient, db: Session) -> None:
    course = add_course(db, "Course 1")

    response = client.get(f"/courses/{course.id}/documents/{uuid4()}/content")

    assert response.status_code == 401


def test_document_content_requires_course_membership(client: TestClient, db: Session) -> None:
    outsider = add_user(db, "outsider", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    login_as(client, outsider.username, "pass")

    response = client.get(f"/courses/{course.id}/documents/{uuid4()}/content")

    assert response.status_code == 403


def test_document_content_does_not_cross_courses(
    client: TestClient, db: Session, tmp_path: Path
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    other_course = add_course(db, "Course 2")
    add_member(db, course, teacher.id, CourseMemberRole.teacher)
    add_member(db, other_course, teacher.id, CourseMemberRole.teacher)
    document_id = uuid4()
    stored = store_upload(tmp_path, other_course.id, document_id, "other.txt", b"secret")
    db.add(
        Document(
            id=document_id,
            course_id=other_course.id,
            uploaded_by=teacher.id,
            filename="other.txt",
            storage_path=str(stored),
        )
    )
    db.commit()
    login_as(client, teacher.username, "pass")

    response = client.get(f"/courses/{course.id}/documents/{document_id}/content")

    assert response.status_code == 404
    assert response.content != b"secret"


@pytest.mark.parametrize("storage_kind", ["outside", "missing"])
def test_document_content_hides_invalid_storage_paths(
    client: TestClient,
    db: Session,
    tmp_path: Path,
    storage_kind: str,
) -> None:
    teacher = add_user(db, f"teacher-{storage_kind}", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher.id, CourseMemberRole.teacher)
    document_id = uuid4()
    if storage_kind == "outside":
        storage_path = tmp_path / "outside.txt"
        storage_path.write_bytes(b"must not leak")
    else:
        storage_path = tmp_path / str(course.id) / str(document_id) / "missing.txt"
    db.add(
        Document(
            id=document_id,
            course_id=course.id,
            uploaded_by=teacher.id,
            filename="note.txt",
            storage_path=str(storage_path),
        )
    )
    db.commit()
    login_as(client, teacher.username, "pass")

    response = client.get(f"/courses/{course.id}/documents/{document_id}/content")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document content unavailable"}
    assert response.content != b"must not leak"


@pytest.mark.parametrize(
    ("filename", "expected_type"),
    [
        (
            "slides.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        (
            "notes.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
def test_office_document_content_is_attachment(
    client: TestClient,
    db: Session,
    tmp_path: Path,
    filename: str,
    expected_type: str,
) -> None:
    teacher = add_user(db, f"teacher-{filename}", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher.id, CourseMemberRole.teacher)
    document_id = uuid4()
    stored = store_upload(tmp_path, course.id, document_id, filename, b"safe fixture")
    db.add(
        Document(
            id=document_id,
            course_id=course.id,
            uploaded_by=teacher.id,
            filename=filename,
            storage_path=str(stored),
        )
    )
    db.commit()
    login_as(client, teacher.username, "pass")

    response = client.get(f"/courses/{course.id}/documents/{document_id}/content")

    assert response.status_code == 200
    assert response.headers["content-type"] == expected_type
    assert response.headers["content-disposition"].startswith("attachment;")


def test_document_api_deletes_file_and_empty_directories(
    client: TestClient, db: Session
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_teacher_member(db, course, teacher.id)
    login_as(client, "t1", "pass")
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("note.txt", b"bounded upload", "text/plain")},
    )
    document_id = UUID(uploaded.json()["id"])
    db.expire_all()
    document = db.get(Document, document_id)
    assert document is not None
    stored = Path(document.storage_path)
    document_dir = stored.parent

    deleted = client.delete(f"/courses/{course.id}/documents/{document_id}")

    assert deleted.status_code == 204
    assert not stored.exists()
    assert not document_dir.exists()


def test_course_delete_removes_only_its_upload_tree(
    client: TestClient, db: Session, tmp_path: Path
) -> None:
    admin = add_user(db, "admin1", "pass", UserRole.admin)
    deleted_course = add_course(db, "Delete me")
    kept_course = add_course(db, "Keep me")
    deleted_file = store_upload(tmp_path, deleted_course.id, uuid4(), "delete.txt", b"delete")
    kept_file = store_upload(tmp_path, kept_course.id, uuid4(), "keep.txt", b"keep")
    login_as(client, admin.username, "pass")

    response = client.delete(f"/admin/courses/{deleted_course.id}")

    assert response.status_code == 204
    assert not deleted_file.exists()
    assert not deleted_file.parents[1].exists()
    assert kept_file.read_bytes() == b"keep"


def test_upload_database_failure_removes_just_written_file(
    client: TestClient,
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_teacher_member(db, course, teacher.id)
    login_as(client, "t1", "pass")

    def fail_commit() -> None:
        raise RuntimeError("scripted database failure")

    monkeypatch.setattr(db, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="scripted database failure"):
        client.post(
            f"/courses/{course.id}/documents",
            files={"file": ("orphan.txt", b"must be removed", "text/plain")},
        )

    assert not any(path.is_file() for path in tmp_path.rglob("*"))


def test_cleanup_failure_is_logged_without_rolling_back_database_delete(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_teacher_member(db, course, teacher.id)
    login_as(client, "t1", "pass")
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("note.txt", b"cleanup failure", "text/plain")},
    )
    document_id = UUID(uploaded.json()["id"])

    def fail_cleanup(*_args) -> None:
        raise StorageError("scripted cleanup failure")

    monkeypatch.setattr("app.api.documents.delete_document_upload", fail_cleanup)
    caplog.set_level(logging.ERROR, logger="app.api.documents")

    response = client.delete(f"/courses/{course.id}/documents/{document_id}")

    assert response.status_code == 204
    db.expire_all()
    assert db.get(Document, document_id) is None
    assert "storage_cleanup_failed scope=document" in caplog.text
    assert "document_id=" in caplog.text
