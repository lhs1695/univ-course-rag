from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from app.api.documents import _document_out
from app.config import ConfigurationUnavailable, Settings, get_settings, provider_status
from app.db import get_db
from app.main import app
from app.models.document import Document, IngestJob
from app.services.embedder import FakeEmbedder, build_embedder
from app.services.ingest import safe_error
from app.services.llm import FakeLLM, build_llm
from app.services.upstream import UpstreamTimeout, UpstreamUnavailable
from fastapi.testclient import TestClient
from openai import APITimeoutError
from sqlalchemy.exc import SQLAlchemyError


def settings_for(**overrides) -> Settings:
    return Settings(_env_file=None, **{
        "embedder_backend": "fake", "llm_backend": "fake",
        "siliconflow_api_key": "", "deepseek_api_key": "", **overrides,
    })


@pytest.mark.parametrize("backend", ["siliconflow", "unknown"])
def test_embedding_configuration_never_silently_falls_back(backend: str) -> None:
    with pytest.raises(ConfigurationUnavailable):
        build_embedder(settings_for(embedder_backend=backend))


@pytest.mark.parametrize("backend", ["deepseek", "unknown"])
def test_generation_configuration_never_silently_falls_back(backend: str) -> None:
    with pytest.raises(ConfigurationUnavailable):
        build_llm(settings_for(llm_backend=backend))


def test_fake_configuration_remains_available_without_keys() -> None:
    settings = settings_for()
    assert isinstance(build_embedder(settings), FakeEmbedder)
    assert isinstance(build_llm(settings), FakeLLM)


@pytest.mark.parametrize("url", ["invalid", "https://user:password@example.org", "https://example.org?key=secret"])
def test_provider_status_rejects_invalid_or_credential_bearing_urls(url: str) -> None:
    settings = settings_for(llm_backend="deepseek", deepseek_api_key="test-only", deepseek_base_url=url)
    assert provider_status(settings, "llm")["status"] == "unavailable"
    with pytest.raises(ConfigurationUnavailable):
        build_llm(settings)


@pytest.mark.parametrize("provider", ["embedding", "llm"])
def test_provider_request_contract_and_timeout_without_network(monkeypatch, provider: str) -> None:
    fake_client = Mock()
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: fake_client)
    settings = settings_for(
        embedder_backend="siliconflow", siliconflow_api_key="test-only",
        llm_backend="deepseek", deepseek_api_key="test-only",
    )
    if provider == "embedding":
        fake_client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=[0.0] * 1024)]
        )
        adapter = build_embedder(settings)
        adapter.embed(["synthetic"])
        call = fake_client.embeddings.create
        assert call.call_args.kwargs == {"model": "BAAI/bge-m3", "input": ["synthetic"]}
        invoke = lambda: adapter.embed(["synthetic"])
    else:
        fake_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="synthetic answer"))]
        )
        adapter = build_llm(settings)
        adapter.generate("synthetic")
        call = fake_client.chat.completions.create
        assert call.call_args.kwargs["model"] == "deepseek-flash"
        assert call.call_args.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
        invoke = lambda: adapter.generate("synthetic")
    call.side_effect = APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))
    with pytest.raises(UpstreamTimeout):
        invoke()
    call.side_effect = RuntimeError("raw-provider-secret")
    with pytest.raises(UpstreamUnavailable) as exc:
        invoke()
    assert "raw-provider-secret" not in str(exc.value)
    assert safe_error(UpstreamTimeout("raw-provider-secret")) == "UPSTREAM_TIMEOUT"


def test_runtime_is_local_and_does_not_echo_credentials(client: TestClient, monkeypatch) -> None:
    settings = settings_for(llm_backend="deepseek", deepseek_api_key="synthetic-secret-value")
    monkeypatch.setitem(app.dependency_overrides, get_settings, lambda: settings)
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: pytest.fail("runtime must not call a provider"))
    response = client.get("/runtime")
    assert response.status_code == 200
    body = response.json()
    assert body["process"] == "ok"
    assert body["database"] == "available"
    assert body["embedding"]["status"] == "fake"
    assert body["generation"]["status"] == "configured"
    assert body["generation"]["connectivity"] == "not_checked"
    assert body["reranking"]["status"] == "disabled"
    assert body["index"] == body["migration"] == "not_checked"
    assert "synthetic-secret-value" not in response.text
    assert "api.deepseek.com" not in response.text


def test_runtime_reports_reranker_configuration_without_contact_or_secrets(client, monkeypatch) -> None:
    settings = settings_for(
        retrieval_strategy="hybrid", reranker_backend="siliconflow", siliconflow_api_key="private-test-key",
    )
    monkeypatch.setitem(app.dependency_overrides, get_settings, lambda: settings)
    monkeypatch.setattr("app.services.rerank.httpx.Client", lambda **_kwargs: pytest.fail("local status only"))
    response = client.get("/runtime")
    assert response.status_code == 200
    assert response.json()["reranking"]["status"] == "configured"
    assert response.json()["reranking"]["connectivity"] == "not_checked"
    assert "private-test-key" not in response.text
    assert "siliconflow.cn" not in response.text


def test_configuration_dependency_failure_is_safe_503(client: TestClient, db, monkeypatch) -> None:
    from app.models.course import CourseMemberRole
    from app.models.user import UserRole
    from app.services.llm import get_llm

    from tests.conftest import add_user
    from tests.test_courses import add_course, add_member, login_as

    user = add_user(db, "student", "pass", UserRole.student)
    course = add_course(db, "Configuration failure")
    add_member(db, course, user, CourseMemberRole.student)
    login_as(client, "student", "pass")

    def unavailable():
        raise ConfigurationUnavailable("must-not-escape")

    monkeypatch.setitem(app.dependency_overrides, get_llm, unavailable)
    response = client.post(f"/courses/{course.id}/ask", json={"query": "synthetic"})
    assert response.status_code == 503
    assert response.json()["error_code"] == "MODEL_NOT_CONFIGURED"
    assert "must-not-escape" not in response.text


def test_ingest_errors_and_legacy_job_details_do_not_expose_raw_text() -> None:
    assert safe_error(RuntimeError("private-path-and-provider-secret")) == "INGEST_FAILED"
    document = Document(id=uuid4(), filename="synthetic.txt", retrieval_enabled=True)
    job = IngestJob(status="failed", error_message="private-path-and-provider-secret")
    assert _document_out(document, job).error_message == "INGEST_FAILED"


def test_database_errors_are_safe_and_distinct(client: TestClient, monkeypatch) -> None:
    unavailable = Mock()
    unavailable.get.side_effect = SQLAlchemyError("database-password-and-host")

    def override_db():
        yield unavailable

    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    client.cookies.set("session_id", str(uuid4()))
    response = client.get("/courses")
    assert response.status_code == 503
    assert response.json()["error_code"] == "DATABASE_UNAVAILABLE"
    assert "database-password-and-host" not in response.text


def test_upload_storage_failure_is_explicit_and_safe(client: TestClient, db, monkeypatch) -> None:
    from app.models.course import CourseMemberRole
    from app.models.user import UserRole

    from tests.conftest import add_user
    from tests.test_courses import add_course, add_member, login_as

    user = add_user(db, "teacher", "pass", UserRole.teacher)
    course = add_course(db, "Upload failure")
    add_member(db, course, user, CourseMemberRole.teacher)
    login_as(client, "teacher", "pass")

    def fail_storage(*args):
        raise OSError("private-storage-path")

    monkeypatch.setattr("app.api.documents.store_upload", fail_storage)
    response = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("synthetic.txt", b"synthetic evidence", "text/plain")},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Upload storage unavailable"
    assert "private-storage-path" not in response.text
