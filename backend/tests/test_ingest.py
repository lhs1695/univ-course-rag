from pathlib import Path
from uuid import UUID

from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.document import Chunk
from app.models.user import User, UserRole
from app.services.embedder import FakeEmbedder
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import add_user

UNIQUE_SENTENCE = "紫石英口令：本课向量必须绑定 course_id-alpha-9371。"
PPTX_SENTENCE = "紫石英PPT口令：幻灯片锚点 delta-8820。"
DOCX_SENTENCE = "紫石英Word口令：实验指导锚点 epsilon-5503。"
SAMPLE_MD = Path(__file__).parent / "fixtures" / "sample.md"
SAMPLE_PPTX = Path(__file__).parent / "fixtures" / "sample.pptx"
SAMPLE_DOCX = Path(__file__).parent / "fixtures" / "sample.docx"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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


def add_member(db: Session, course: Course, user: User, role: CourseMemberRole) -> None:
    db.add(CourseMember(course_id=course.id, user_id=user.id, role=role.value))
    db.commit()


def test_upload_sample_md_indexes_unique_sentence(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    content = SAMPLE_MD.read_bytes()
    assert UNIQUE_SENTENCE.encode("utf-8") in content
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("sample.md", content, "text/markdown")},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])

    detail = client.get(f"/courses/{course.id}/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["job_status"] == "succeeded"
    assert detail.json()["error_message"] is None

    db.expire_all()
    chunks = db.execute(select(Chunk).where(Chunk.document_id == doc_id)).scalars().all()
    assert chunks
    assert all(chunk.course_id == course.id for chunk in chunks)
    assert any(UNIQUE_SENTENCE in chunk.text for chunk in chunks)
    assert all(len(chunk.embedding) == 1024 for chunk in chunks)
    assert all(chunk.embedding_model == FakeEmbedder().index_identity for chunk in chunks)


def test_upload_sample_pptx_indexes_unique_sentence(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    content = SAMPLE_PPTX.read_bytes()
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("sample.pptx", content, PPTX_MIME)},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])

    detail = client.get(f"/courses/{course.id}/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["job_status"] == "succeeded"
    assert detail.json()["error_message"] is None

    db.expire_all()
    chunks = db.execute(select(Chunk).where(Chunk.document_id == doc_id)).scalars().all()
    assert chunks
    assert all(chunk.course_id == course.id for chunk in chunks)
    assert any(PPTX_SENTENCE in chunk.text for chunk in chunks)
    assert all(len(chunk.embedding) == 1024 for chunk in chunks)


def test_corrupt_pptx_fails_without_chunks(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("broken.pptx", b"PK\x03\x04-not-a-real-pptx", PPTX_MIME)},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])
    detail = client.get(f"/courses/{course.id}/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["job_status"] == "failed"
    assert detail.json()["error_message"]

    db.expire_all()
    chunks = db.execute(select(Chunk).where(Chunk.document_id == doc_id)).scalars().all()
    assert chunks == []


def test_upload_sample_docx_indexes_unique_sentence(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    content = SAMPLE_DOCX.read_bytes()
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("sample.docx", content, DOCX_MIME)},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])

    detail = client.get(f"/courses/{course.id}/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["job_status"] == "succeeded"
    assert detail.json()["error_message"] is None

    db.expire_all()
    chunks = db.execute(select(Chunk).where(Chunk.document_id == doc_id)).scalars().all()
    assert chunks
    assert all(chunk.course_id == course.id for chunk in chunks)
    assert any(DOCX_SENTENCE in chunk.text for chunk in chunks)
    assert all(len(chunk.embedding) == 1024 for chunk in chunks)


def test_corrupt_docx_fails_without_chunks(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("broken.docx", b"PK\x03\x04-not-a-real-docx", DOCX_MIME)},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])
    detail = client.get(f"/courses/{course.id}/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["job_status"] == "failed"
    assert detail.json()["error_message"]

    db.expire_all()
    chunks = db.execute(select(Chunk).where(Chunk.document_id == doc_id)).scalars().all()
    assert chunks == []


def test_corrupt_pdf_fails_without_chunks(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")

    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("broken.pdf", b"%PDF-not-a-real-file", "application/pdf")},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])
    detail = client.get(f"/courses/{course.id}/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["job_status"] == "failed"
    assert detail.json()["error_message"]

    db.expire_all()
    chunks = db.execute(select(Chunk).where(Chunk.document_id == doc_id)).scalars().all()
    assert chunks == []


def test_student_cannot_delete_document(client: TestClient, db: Session) -> None:
    student = add_user(db, "alice", "pass", UserRole.student)
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    login_as(client, "t1", "pass")
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("sample.md", SAMPLE_MD.read_bytes(), "text/markdown")},
    )
    assert uploaded.status_code == 201
    doc_id = UUID(uploaded.json()["id"])
    login_as(client, "alice", "pass")
    deleted = client.delete(f"/courses/{course.id}/documents/{doc_id}")
    assert deleted.status_code == 403


def test_student_cannot_upload(client: TestClient, db: Session) -> None:
    student = add_user(db, "alice", "pass", UserRole.student)
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    login_as(client, "alice", "pass")
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("sample.md", SAMPLE_MD.read_bytes(), "text/markdown")},
    )
    assert uploaded.status_code == 403
