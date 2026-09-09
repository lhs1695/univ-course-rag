from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.main import app
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.models.user import User, UserRole
from app.services.embedder import FakeEmbedder, get_embedder
from app.services.ingest import (
    IngestLeaseLost,
    _touch_running_job,
    process_ingest_job,
    retry_ingest_job,
)
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


class RecordingEmbedder(FakeEmbedder):
    def __init__(self, *, fail_on_call: int | None = None) -> None:
        super().__init__()
        self.batch_sizes: list[int] = []
        self.fail_on_call = fail_on_call

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(texts))
        if self.fail_on_call == len(self.batch_sizes):
            raise RuntimeError("scripted embedding failure")
        return super().embed(texts)


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


def test_ingest_sends_configured_embedding_batches(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "t1", "pass")
    embedder = RecordingEmbedder()
    app.dependency_overrides[get_embedder] = lambda: embedder
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "2")

    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("large.txt", ("batch boundary " * 200).encode(), "text/plain")},
    )

    assert uploaded.status_code == 201
    assert len(embedder.batch_sizes) > 1
    assert all(size <= 2 for size in embedder.batch_sizes)
    assert sum(embedder.batch_sizes) > 2


def test_mid_batch_failure_preserves_previous_complete_chunks(
    db: Session, tmp_path: Path
) -> None:
    course = add_course(db, "Course 1")
    source = tmp_path / "retry.txt"
    source.write_text("transactional chunks " * 150, encoding="utf-8")
    document = Document(
        course_id=course.id,
        uploaded_by=uuid4(),
        filename=source.name,
        storage_path=str(source),
    )
    db.add(document)
    db.flush()
    embedder = RecordingEmbedder(fail_on_call=2)
    old_chunk = Chunk(
        course_id=course.id,
        document_id=document.id,
        page=1,
        text="previous complete index",
        embedding=embedder.embed(["previous complete index"])[0],
        embedding_model=embedder.index_identity,
    )
    embedder.batch_sizes.clear()
    job = IngestJob(document_id=document.id, status=IngestJobStatus.pending.value)
    db.add_all([old_chunk, job])
    db.commit()

    process_ingest_job(db, job.id, embedder, batch_size=1)

    db.expire_all()
    stored_job = db.get(IngestJob, job.id)
    chunks = db.execute(select(Chunk).where(Chunk.document_id == document.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.status == IngestJobStatus.failed.value
    assert stored_job.run_token is None
    assert [chunk.id for chunk in chunks] == [old_chunk.id]
    assert chunks[0].text == "previous complete index"


@pytest.mark.parametrize(
    "recoverable_status",
    [
        IngestJobStatus.failed.value,
        IngestJobStatus.pending.value,
        IngestJobStatus.running.value,
    ],
)
def test_teacher_can_recover_failed_or_stale_ingest_job(
    client: TestClient,
    db: Session,
    recoverable_status: str,
) -> None:
    teacher = add_user(db, f"teacher-{recoverable_status}", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    document = Document(
        course_id=course.id,
        uploaded_by=teacher.id,
        filename=SAMPLE_MD.name,
        storage_path=str(SAMPLE_MD),
    )
    db.add(document)
    db.flush()
    job = IngestJob(
        document_id=document.id,
        status=recoverable_status,
        run_token=(
            uuid4() if recoverable_status == IngestJobStatus.running.value else None
        ),
        updated_at=(
            datetime.now(UTC)
            if recoverable_status == IngestJobStatus.failed.value
            else datetime.now(UTC) - timedelta(hours=1)
        ),
    )
    db.add(job)
    db.commit()
    login_as(client, teacher.username, "pass")

    retried = client.post(f"/courses/{course.id}/documents/{document.id}/retry")

    assert retried.status_code == 202
    db.expire_all()
    stored_job = db.get(IngestJob, job.id)
    chunks = db.execute(select(Chunk).where(Chunk.document_id == document.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.status == IngestJobStatus.succeeded.value
    assert stored_job.run_token is None
    assert chunks
    chunk_ids = [chunk.id for chunk in chunks]

    duplicate = client.post(f"/courses/{course.id}/documents/{document.id}/retry")
    assert duplicate.status_code == 409
    db.expire_all()
    after_duplicate = db.execute(
        select(Chunk).where(Chunk.document_id == document.id)
    ).scalars().all()
    assert [chunk.id for chunk in after_duplicate] == chunk_ids


def test_revoked_worker_lease_cannot_refresh_or_change_retried_job(db: Session) -> None:
    course = add_course(db, "Course 1")
    document = Document(
        course_id=course.id,
        uploaded_by=uuid4(),
        filename=SAMPLE_MD.name,
        storage_path=str(SAMPLE_MD),
    )
    old_token = uuid4()
    db.add(document)
    db.flush()
    job = IngestJob(
        document_id=document.id,
        status=IngestJobStatus.running.value,
        run_token=old_token,
        updated_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db.add(job)
    db.commit()

    assert retry_ingest_job(db, job.id, datetime.now(UTC) - timedelta(minutes=15))
    with pytest.raises(IngestLeaseLost, match="lease lost"):
        _touch_running_job(db, job.id, old_token)

    db.expire_all()
    stored_job = db.get(IngestJob, job.id)
    assert stored_job is not None
    assert stored_job.status == IngestJobStatus.pending.value
    assert stored_job.run_token is None


def test_active_ingest_job_cannot_be_retried(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    document = Document(
        course_id=course.id,
        uploaded_by=teacher.id,
        filename=SAMPLE_MD.name,
        storage_path=str(SAMPLE_MD),
    )
    db.add(document)
    db.flush()
    db.add(
        IngestJob(
            document_id=document.id,
            status=IngestJobStatus.running.value,
            run_token=uuid4(),
            updated_at=datetime.now(UTC),
        )
    )
    db.commit()
    login_as(client, "t1", "pass")

    response = client.post(f"/courses/{course.id}/documents/{document.id}/retry")

    assert response.status_code == 409


def test_student_cannot_retry_ingest_job(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    student = add_user(db, "alice", "pass", UserRole.student)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    document = Document(
        course_id=course.id,
        uploaded_by=teacher.id,
        filename=SAMPLE_MD.name,
        storage_path=str(SAMPLE_MD),
    )
    db.add(document)
    db.flush()
    db.add(IngestJob(document_id=document.id, status=IngestJobStatus.failed.value))
    db.commit()
    login_as(client, "alice", "pass")

    response = client.post(f"/courses/{course.id}/documents/{document.id}/retry")

    assert response.status_code == 403
