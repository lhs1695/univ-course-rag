"""PLAN-02: synthetic uploads, conftest SQLite, FakeEmbedder/FakeLLM only."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.main import app
from app.models.course import CourseMember, CourseMemberRole
from app.models.document import Chunk, Document, IngestJob, IngestJobStatus
from app.models.user import UserRole
from app.services.embedder import FakeEmbedder, get_embedder
from app.services.generate import NO_EVIDENCE, generate_answer_result
from app.services.keyword import retrieve_keyword_candidates
from app.services.llm import FakeLLM, get_llm
from app.services.retrieve import (
    has_incompatible_chunks,
    merge_definition_hits,
    retrieve_chunks,
    retrieve_expanded_chunks,
)
from app.services.storage import StorageError
from sqlalchemy import select

from tests.conftest import add_user
from tests.test_ingest import add_course, add_member, login_as, upload_as_teacher
from tests.test_parse import make_pdf

TEXT = "Lifecycle evidence describes the course document permission boundary."
QUERY = "What does lifecycle evidence describe?"


@pytest.fixture
def library(client, db):
    first_id = upload_as_teacher(client, db, "same.pdf", make_pdf(TEXT))
    first = db.get(Document, first_id)
    course_id = first.course_id
    sibling = client.post(
        f"/courses/{course_id}/documents",
        files={"file": ("same.pdf", make_pdf(TEXT + " Enabled sibling evidence."), "application/pdf")},
    )
    assert sibling.status_code == 201
    second_id = UUID(sibling.json()["id"])
    student = add_user(db, "student", "pass", UserRole.student)
    course = add_course(db, "Other course")
    add_member(db, db.get(type(course), course_id), student, CourseMemberRole.student)
    other = Document(
        course_id=course.id, uploaded_by=first.uploaded_by,
        filename="other.pdf", storage_path="unused-synthetic-path",
    )
    db.add(other)
    db.commit()
    return SimpleNamespace(
        course_id=course_id, first_id=first_id, second_id=second_id,
        base=f"/courses/{course_id}", student=student,
        other_course_id=course.id, other_id=other.id,
    )


def chunks_for(db, document_id):
    return db.scalars(select(Chunk).where(Chunk.document_id == document_id)).all()


def toggle(client, library, document_id, enabled):
    response = client.patch(
        f"{library.base}/documents/{document_id}", json={"retrieval_enabled": enabled},
    )
    assert response.status_code == 200, response.text
    assert response.json()["retrieval_enabled"] is enabled
    return response.json()


@pytest.mark.parametrize("role", [UserRole.student, UserRole.teacher, UserRole.admin])
def test_global_role_cannot_override_student_membership(client, db, library, role):
    library.student.role = role.value
    db.commit()
    login_as(client, "student", "pass")
    url = f"{library.base}/documents/{library.first_id}"
    responses = [
        client.post(f"{library.base}/documents", files={"file": ("denied.txt", b"denied")}),
        client.delete(url), client.post(f"{url}/retry"),
        client.patch(url, json={"retrieval_enabled": False}),
    ]
    assert [response.status_code for response in responses] == [403] * 4
    assert client.get(url).json()["retrieval_enabled"] is True
    assert client.get(f"{url}/content").status_code == 200
    assert len(client.get(f"{library.base}/documents").json()) == 2
    assert chunks_for(db, library.first_id)


def test_teacher_toggle_is_idempotent_preserves_metadata_chunks_and_preview(client, db, library):
    url = f"{library.base}/documents/{library.first_id}"
    before = client.get(url).json()
    ids = [chunk.id for chunk in chunks_for(db, library.first_id)]
    for enabled in [False, False, True, True]:
        updated = toggle(client, library, library.first_id, enabled)
        assert updated == {**before, "retrieval_enabled": enabled}
        assert client.get(f"{url}/content").status_code == 200
        assert [chunk.id for chunk in chunks_for(db, library.first_id)] == ids
    toggle(client, library, library.first_id, False)
    login_as(client, "student", "pass")
    rows = client.get(f"{library.base}/documents").json()
    assert {row["id"]: row["retrieval_enabled"] for row in rows} == {
        str(library.first_id): False, str(library.second_id): True,
    }
    assert client.get(url).json()["retrieval_enabled"] is False
    assert client.get(f"{url}/content").content.startswith(b"%PDF")


@pytest.mark.parametrize("value", [None, "false", 0, 1, [], {}])
def test_toggle_requires_json_boolean(client, library, value):
    url = f"{library.base}/documents/{library.first_id}"
    assert client.patch(url, json={"retrieval_enabled": value}).status_code == 422
    assert client.get(url).json()["retrieval_enabled"] is True


def test_toggle_missing_or_wrong_course_document_is_404(client, library):
    for document_id in [uuid4(), library.other_id]:
        response = client.patch(
            f"{library.base}/documents/{document_id}", json={"retrieval_enabled": False},
        )
        assert response.status_code == 404
    assert client.patch(f"{library.base}/documents/{library.first_id}", json={}).status_code == 422


@pytest.mark.parametrize("strategy", ["dense", "hybrid"])
def test_disabled_document_never_reaches_retrieval_context_or_citations(
    client, db, library, monkeypatch, strategy,
):
    from app.config import Settings

    settings = Settings(_env_file=None, retrieval_strategy=strategy)
    monkeypatch.setattr("app.api.ask.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.search.get_settings", lambda: settings)
    embedder = FakeEmbedder()
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    original_hits = retrieve_chunks(db, library.course_id, QUERY, embedder)
    assert {hit.document_id for hit in original_hits} == {library.first_id, library.second_id}
    disabled_chunk_ids = {str(chunk.id) for chunk in chunks_for(db, library.first_id)}
    toggle(client, library, library.first_id, False)
    stale = generate_answer_result(db, QUERY, original_hits, llm)
    assert stale.cited_ids
    assert not disabled_chunk_ids.intersection(map(str, stale.cited_ids))
    for prompt in llm.prompts:
        assert all(chunk_id not in prompt for chunk_id in disabled_chunk_ids)
    for hits in [
        retrieve_chunks(db, library.course_id, QUERY, embedder, strategy=strategy),
        retrieve_keyword_candidates(
            db, library.course_id, "lifecycle", index_identity=embedder.index_identity,
        ),
        merge_definition_hits(db, library.course_id, "Lifecycle", embedder, []),
        retrieve_expanded_chunks(db, library.course_id, QUERY, embedder, ["lifecycle evidence"]),
    ]:
        assert hits
        assert {hit.document_id for hit in hits} == {library.second_id}
    # Disabled incompatible vectors must not block the enabled sibling's ask.
    for chunk in chunks_for(db, library.first_id):
        chunk.embedding_model = "obsolete-index"
    db.commit()
    assert not has_incompatible_chunks(db, library.course_id, embedder)
    login_as(client, "student", "pass")
    search = client.post(f"{library.base}/search", json={"query": QUERY})
    assert search.status_code == 200
    assert {hit["document_id"] for hit in search.json()["hits"]} == {str(library.second_id)}
    response = client.post(f"{library.base}/ask", json={"query": QUERY})
    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] is None
    assert body["answer"]
    assert {citation["document_id"] for citation in body["citations"]} == {str(library.second_id)}
    citation = body["citations"][0]
    assert citation["page"] == 1
    assert client.get(citation["content_url"].split("#")[0]).content.startswith(b"%PDF")
    login_as(client, "t1", "pass")
    toggle(client, library, library.second_id, False)
    calls = len(llm.prompts)
    empty = client.post(f"{library.base}/ask", json={"query": QUERY})
    assert empty.status_code == 200
    assert empty.json()["error_code"] == NO_EVIDENCE
    assert empty.json()["answer"] is None
    assert empty.json()["citations"] == []
    assert len(llm.prompts) == calls
    assert client.post(f"{library.base}/search", json={"query": QUERY}).json()["hits"] == []
    toggle(client, library, library.second_id, True)
    assert client.post(f"{library.base}/ask", json={"query": QUERY}).json()["citations"]


@pytest.mark.parametrize("username", ["t1", "student", "admin"])
def test_course_membership_required_for_all_document_and_evidence_routes(client, db, library, username):
    if username == "admin":
        add_user(db, "admin", "pass", UserRole.admin)
    login_as(client, username, "pass")
    base = f"/courses/{library.other_course_id}"
    url = f"{base}/documents/{library.other_id}"
    responses = [
        client.get(f"{base}/documents"), client.get(url), client.get(f"{url}/content"),
        client.post(f"{base}/documents", files={"file": ("denied.txt", b"denied")}),
        client.delete(url), client.post(f"{url}/retry"),
        client.patch(url, json={"retrieval_enabled": False}),
        client.post(f"{base}/ask", json={"query": QUERY}),
        client.post(f"{base}/search", json={"query": QUERY}),
    ]
    assert [response.status_code for response in responses] == [403] * len(responses)


def test_removing_membership_revokes_metadata_content_search_ask_and_toggle(client, db, library):
    login_as(client, "student", "pass")
    url = f"{library.base}/documents/{library.first_id}"
    assert client.get(f"{url}/content").status_code == 200
    member = db.scalar(select(CourseMember).where(
        CourseMember.course_id == library.course_id, CourseMember.user_id == library.student.id,
    ))
    db.delete(member)
    db.commit()
    assert client.get(f"{library.base}/documents").status_code == 403
    assert client.get(url).status_code == 403
    assert client.get(f"{url}/content").status_code == 403
    for action in ["ask", "search"]:
        assert client.post(f"{library.base}/{action}", json={"query": QUERY}).status_code == 403
    assert client.patch(url, json={"retrieval_enabled": False}).status_code == 403


def test_delete_removes_database_chunks_jobs_file_and_old_content_only_for_target(client, db, library):
    toggle(client, library, library.first_id, False)
    first_path = Path(db.get(Document, library.first_id).storage_path)
    second_path = Path(db.get(Document, library.second_id).storage_path)
    sibling_bytes = second_path.read_bytes()
    sibling_chunk_ids = [chunk.id for chunk in chunks_for(db, library.second_id)]
    assert first_path != second_path  # Same filename still has isolated storage.
    url = f"{library.base}/documents/{library.first_id}"
    assert client.delete(url).status_code == 204
    db.expire_all()
    assert db.get(Document, library.first_id) is None
    assert chunks_for(db, library.first_id) == []
    assert db.scalars(select(IngestJob).where(IngestJob.document_id == library.first_id)).all() == []
    assert not first_path.exists()
    assert client.get(url).status_code == 404
    assert client.get(f"{url}/content").status_code == 404
    assert client.delete(url).status_code == 404
    assert client.post(f"{url}/retry").status_code == 404
    assert second_path.read_bytes() == sibling_bytes
    assert [chunk.id for chunk in chunks_for(db, library.second_id)] == sibling_chunk_ids
    assert client.get(f"{library.base}/documents/{library.second_id}/content").status_code == 200
    assert db.get(Document, library.other_id) is not None
    body = client.post(f"{library.base}/ask", json={"query": QUERY}).json()
    assert {citation["document_id"] for citation in body["citations"]} == {str(library.second_id)}


def test_delete_storage_failure_is_visible_and_retryable_without_losing_records(
    client, db, library, monkeypatch,
):
    from app.api import documents

    original = documents.delete_document_upload
    path = Path(db.get(Document, library.first_id).storage_path)
    ids = [chunk.id for chunk in chunks_for(db, library.first_id)]

    def fail_cleanup(*args):
        raise StorageError("synthetic cleanup failure")

    monkeypatch.setattr(documents, "delete_document_upload", fail_cleanup)
    url = f"{library.base}/documents/{library.first_id}"
    failed = client.delete(url)
    assert failed.status_code == 503
    assert failed.json()["detail"] == "Document storage cleanup unavailable"
    assert client.get(url).status_code == 200
    assert path.exists()
    assert [chunk.id for chunk in chunks_for(db, library.first_id)] == ids
    assert client.get(f"{library.base}/documents/{library.second_id}/content").status_code == 200
    monkeypatch.setattr(documents, "delete_document_upload", original)
    assert client.delete(url).status_code == 204
    assert not path.exists()
    assert chunks_for(db, library.first_id) == []


def test_failed_ingest_retries_once_without_enabling_document_or_duplicating_sibling(client, db, library):
    class BrokenEmbedder(FakeEmbedder):
        def embed(self, texts):
            raise RuntimeError("synthetic embedding failure")

    sibling_ids = [chunk.id for chunk in chunks_for(db, library.second_id)]
    app.dependency_overrides[get_embedder] = BrokenEmbedder
    response = client.post(
        f"{library.base}/documents", files={"file": ("retry.pdf", make_pdf(TEXT), "application/pdf")},
    )
    assert response.status_code == 201
    document_id = UUID(response.json()["id"])
    url = f"{library.base}/documents/{document_id}"
    assert client.get(url).json()["job_status"] == IngestJobStatus.failed.value
    assert chunks_for(db, document_id) == []
    toggle(client, library, document_id, False)
    app.dependency_overrides[get_embedder] = FakeEmbedder
    response = client.post(f"{url}/retry")
    assert response.status_code == 202
    detail = client.get(url).json()
    assert detail["job_status"] == IngestJobStatus.succeeded.value
    assert detail["retrieval_enabled"] is False
    assert detail["error_message"] is None
    ids = [chunk.id for chunk in chunks_for(db, document_id)]
    assert ids and detail["chunk_count"] == len(ids)
    assert client.post(f"{url}/retry").status_code == 409
    assert [chunk.id for chunk in chunks_for(db, document_id)] == ids
    assert [chunk.id for chunk in chunks_for(db, library.second_id)] == sibling_ids


def test_migration_backfills_existing_documents_and_has_server_default(db, library, monkeypatch):
    path = Path(__file__).parents[1] / "alembic/versions/0012_document_retrieval_enabled.py"
    spec = spec_from_file_location("plan02_migration", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0012" and migration.down_revision == "0011"
    connection = db.connection()
    monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
    migration.downgrade()
    migration.upgrade()
    rows = connection.exec_driver_sql("SELECT retrieval_enabled FROM documents").all()
    assert len(rows) == 3 and all(row[0] == 1 for row in rows)
    columns = connection.exec_driver_sql("PRAGMA table_info(documents)").all()
    column = next(row for row in columns if row[1] == "retrieval_enabled")
    assert column[3] == 1  # NOT NULL
    assert str(column[4]) == "1"
