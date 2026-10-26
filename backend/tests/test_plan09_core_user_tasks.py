"""Developer Fake HTTP rehearsal only; no independent trial or browser claims."""

import fitz
import pytest
from app.config import Settings, get_settings
from app.main import app
from app.models.course import CourseMemberRole
from app.models.document import Document, IngestJob
from app.models.query_log import QueryLog
from app.models.user import UserRole
from app.services.embedder import FakeEmbedder
from app.services.llm import FakeLLM, get_llm
from app.services.storage import store_upload
from app.services.upstream import UpstreamTimeout
from sqlalchemy import select

from tests.conftest import add_user
from tests.test_plan08_stream_performance import assert_terminal, parse_events
from tests.test_retrieve import _scaled_chunk, add_course, add_member, login_as

QUERY = "请说明本课的事务隔离级别"
SOURCE_TEXT = "Transaction isolation: read committed."


@pytest.fixture
def core_tasks(client, db, tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None, upload_dir=tmp_path, retrieval_strategy="dense",
        reranker_backend="disabled", query_expansion_backend="disabled",
    )
    monkeypatch.setattr("app.api.ask.get_settings", lambda: settings)
    app.dependency_overrides[get_settings] = lambda: settings
    teacher = add_user(db, "p09-teacher", "pass", UserRole.teacher)
    student = add_user(db, "p09-student", "pass", UserRole.student)
    course = add_course(db, "PLAN-09 synthetic rehearsal")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)
    chunk = _scaled_chunk(db, course, FakeEmbedder(), QUERY, SOURCE_TEXT, 1.0)
    chunk.page = 2
    document = db.get(Document, chunk.document_id)
    # Seed a sparse first page and a citable second page, without running ingest.
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.new_page().insert_text((72, 72), SOURCE_TEXT)
        source_bytes = pdf.tobytes()
    document.filename = "p09-synthetic.pdf"
    document.uploaded_by = teacher.id
    document.storage_path = str(store_upload(
        tmp_path, course.id, document.id, document.filename, source_bytes,
    ))
    document.source_unit_count = 2
    document.extracted_char_count = len(SOURCE_TEXT)
    document.chunk_count = 1
    document.quality_warning = "COVERAGE_INCOMPLETE"
    db.add(IngestJob(document_id=document.id, status="succeeded"))
    db.commit()
    return course, teacher, student, chunk, source_bytes


@pytest.mark.parametrize("transport", ["json", "stream"])
def test_student_answer_evidence_and_pdf_content(client, core_tasks, transport):
    course, _, student, chunk, source_bytes = core_tasks
    login_as(client, student.username, "pass")
    endpoint = "ask" if transport == "json" else "ask/stream"
    response = client.post(f"/courses/{course.id}/{endpoint}", json={"query": QUERY})
    assert response.status_code == 200, response.text
    body = response.json() if transport == "json" else assert_terminal(parse_events(response.text))
    assert body["error_code"] is None
    assert body["answer"]
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["chunk_id"] == str(chunk.id)
    assert citation["document_id"] == str(chunk.document_id)
    assert citation["snippet"] == SOURCE_TEXT
    assert citation["page"] == 2
    assert citation["content_url"] == (
        f"/courses/{course.id}/documents/{chunk.document_id}/content"
    )
    source = client.get(citation["content_url"])
    assert source.status_code == 200
    assert source.headers["content-type"] == "application/pdf"
    assert source.headers["content-disposition"].startswith("inline;")
    assert source.content == source_bytes
    with fitz.open(stream=source.content, filetype="pdf") as pdf:
        assert len(pdf) == 2
        assert SOURCE_TEXT in pdf[citation["page"] - 1].get_text()
    # HTTP checks the source and page metadata; it cannot check browser #page navigation.
    assert client.get(f"/courses/{course.id}/insight-reviews").status_code == 403


def test_insufficient_evidence_and_system_fault_have_distinct_recovery(client, db, core_tasks):
    course, teacher, student, chunk, _ = core_tasks
    document_url = f"/courses/{course.id}/documents/{chunk.document_id}"
    ask_url = f"/courses/{course.id}/ask"
    login_as(client, teacher.username, "pass")
    assert client.patch(document_url, json={"retrieval_enabled": False}).status_code == 200
    login_as(client, student.username, "pass")
    insufficient = client.post(ask_url, json={"query": QUERY})
    assert insufficient.status_code == 200
    assert insufficient.json()["error_code"] == "NO_EVIDENCE"
    assert insufficient.json()["answer"] is None
    assert insufficient.json()["citations"] == []
    # Disabled sources are hidden from students; teachers can still preview them.
    assert client.get(f"{document_url}/content").status_code == 404

    login_as(client, teacher.username, "pass")
    assert client.get(f"{document_url}/content").status_code == 200
    assert client.patch(document_url, json={"retrieval_enabled": True}).status_code == 403
    admin = add_user(db, "p09-admin", "pass", UserRole.admin)
    login_as(client, admin.username, "pass")
    assert client.patch(document_url, json={"retrieval_enabled": True}).status_code == 200
    login_as(client, student.username, "pass")

    class TimeoutLLM(FakeLLM):
        def generate(self, prompt):
            raise UpstreamTimeout("private-p09-provider-detail")

    app.dependency_overrides[get_llm] = TimeoutLLM
    failed = client.post(ask_url, json={"query": QUERY})
    assert failed.status_code == 504
    assert failed.json()["error_code"] == "UPSTREAM_TIMEOUT"
    assert failed.json()["answer"] is None
    assert failed.json()["citations"] == []
    assert "private-p09-provider-detail" not in failed.text

    app.dependency_overrides[get_llm] = FakeLLM
    retried = client.post(ask_url, json={"query": QUERY})
    assert retried.status_code == 200
    assert retried.json()["error_code"] is None
    assert retried.json()["citations"][0]["chunk_id"] == str(chunk.id)
    db.expire_all()
    logs = list(db.scalars(select(QueryLog)))
    assert len(logs) == 3
    assert {row.outcome for row in logs} == {"no_evidence", "failure", "cited_answer"}
    assert {row.error_code for row in logs} == {"NO_EVIDENCE", "UPSTREAM_TIMEOUT", None}


def test_teacher_quality_candidate_action_and_refetch(client, db, core_tasks):
    course, teacher, student, chunk, _ = core_tasks
    failed_document = Document(
        course_id=course.id, uploaded_by=teacher.id, filename="p09-failed.pdf",
        storage_path="unused", chunk_count=0,
    )
    db.add(failed_document)
    db.flush()
    db.add(IngestJob(
        document_id=failed_document.id, status="failed", error_message="INGEST_FAILED",
    ))
    db.commit()
    login_as(client, student.username, "pass")
    # Themes only surface cited_answer repeats when count >= 2 (exact_normalize).
    for _ in range(2):
        asked = client.post(f"/courses/{course.id}/ask", json={"query": QUERY})
        assert asked.status_code == 200
        assert asked.json()["error_code"] is None

    login_as(client, teacher.username, "pass")
    documents = client.get(f"/courses/{course.id}/documents")
    assert documents.status_code == 200
    by_id = {row["id"]: row for row in documents.json()}
    warning = by_id[str(chunk.document_id)]
    assert warning["job_status"] == "succeeded"
    assert warning["quality_warning"] == "COVERAGE_INCOMPLETE"
    assert warning["chunk_count"] == 1
    failure = by_id[str(failed_document.id)]
    assert failure["job_status"] == "failed"
    assert failure["error_message"] == "INGEST_FAILED"
    assert failure["chunk_count"] == 0

    insights = client.get(f"/courses/{course.id}/insights")
    assert insights.status_code == 200
    assert insights.json()["summary"]["sample_limited"] is True
    candidate = next(row for row in insights.json()["themes"] if row["label"] == QUERY)
    assert candidate["status"] == "candidate"
    assert candidate["kind"] == "cited_repeat"
    assert candidate["ask_count"] == 2
    # Match the current UI form, which fixes confirmed/undecidable rather than editing them.
    payload = {
        "subject_type": "clue", "subject_key": candidate["label"],
        "intent_code": "concept", "knowledge_point": "事务/隔离级别",
        "review_status": "confirmed", "cause_code": "undecidable",
        "action_code": "clarify_in_class",
    }
    reviews_url = f"/courses/{course.id}/insight-reviews"
    created = client.post(reviews_url, json=payload)
    assert created.status_code == 201, created.text
    saved = created.json()
    assert saved["teacher_id"] == str(teacher.id)
    assert saved["course_id"] == str(course.id)
    for key, value in payload.items():
        assert saved[key] == value

    db.expire_all()
    login_as(client, teacher.username, "pass")
    for _ in range(2):
        refreshed = client.get(reviews_url)
        assert refreshed.status_code == 200
        assert refreshed.json() == [saved]
    login_as(client, student.username, "pass")
    assert client.post(reviews_url, json=payload).status_code == 403
