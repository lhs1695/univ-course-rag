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
