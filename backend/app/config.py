from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://univ:univ@localhost:5432/univ_course_rag"
    session_cookie_name: str = "session_id"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
    session_cleanup_batch_size: int = Field(default=100, ge=1, le=1_000)
    query_log_retention_days: int = Field(default=90, ge=1, le=3_650)
    query_log_cleanup_batch_size: int = Field(default=100, ge=1, le=1_000)
    upstream_timeout_seconds: float = Field(default=20.0, ge=1.0, le=60.0)
    upstream_max_retries: int = Field(default=2, ge=0, le=3)
    ooxml_max_zip_entries: int = Field(default=2_000, ge=10, le=20_000)
    ooxml_max_uncompressed_bytes: int = Field(
        default=50 * 1024 * 1024, ge=1024 * 1024, le=200 * 1024 * 1024
    )
    ooxml_max_entry_bytes: int = Field(
        default=10 * 1024 * 1024, ge=1024 * 1024, le=50 * 1024 * 1024
    )
    ooxml_max_compression_ratio: float = Field(default=100.0, ge=2.0, le=1_000.0)
    parse_max_pages: int = Field(default=500, ge=1, le=5_000)
    parse_max_text_chars: int = Field(default=2_000_000, ge=10_000, le=10_000_000)

    seed_admin_username: str = "admin"
    seed_teacher_username: str = "teacher"
    seed_student_username: str = "student"
    seed_admin_password: str = "change-me-admin"
    seed_teacher_password: str = "change-me-teacher"
    seed_student_password: str = "change-me-student"

    upload_dir: Path = _BACKEND_ROOT / "data" / "uploads"
    embedder_backend: str = "fake"
    embedding_model: str = "BAAI/bge-m3"
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_api_key: str = ""
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    ingest_stale_seconds: int = Field(default=15 * 60, ge=60)
    ingest_low_text_chars: int = Field(default=200, ge=1, le=5_000)
    llm_backend: str = "fake"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    retrieval_strategy: Literal["dense", "hybrid"] = "dense"
    rrf_k: int = Field(default=60, ge=1, le=10_000)
    reranker_backend: str = "disabled"
    query_expansion_backend: str = "disabled"
    question_grouping_backend: str = "disabled"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_base_url: str = "https://api.siliconflow.cn/v1"


class ConfigurationUnavailable(Exception):
    """Only a stable category may leave the configuration boundary."""


def provider_status(settings: Settings, kind: str) -> dict:
    if kind == "embedding":
        backend, expected = settings.embedder_backend, "siliconflow"
        key, model, url = (
            settings.siliconflow_api_key, settings.embedding_model, settings.embedding_base_url
        )
    elif kind == "reranking":
        backend, expected = settings.reranker_backend, "siliconflow"
        key, model, url = settings.siliconflow_api_key, settings.reranker_model, settings.reranker_base_url
        if backend == "disabled":
            return {
                "backend": "disabled", "status": "disabled", "key_present": False,
                "model_present": bool(model.strip()), "connectivity": "not_checked",
            }
    else:
        backend, expected = settings.llm_backend, "deepseek"
        key, model, url = settings.deepseek_api_key, settings.deepseek_model, settings.deepseek_base_url
    try:
        parsed = urlsplit(url)
        valid_url = (
            parsed.scheme in {"http", "https"} and bool(parsed.hostname)
            and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
        )
    except ValueError:
        valid_url = False
    valid = backend == "fake" or (
        backend == expected and bool(key.strip()) and bool(model.strip()) and valid_url
    )
    if kind == "reranking":
        valid = backend == expected and valid and settings.retrieval_strategy == "hybrid"
    fake = backend == "fake" and kind != "reranking"
    return {
        "backend": backend if backend == expected or fake else "unsupported",
        "status": "fake" if fake else "configured" if valid else "unavailable",
        "key_present": bool(key.strip()),
        "model_present": bool(model.strip()),
        "connectivity": "not_checked",
    }


def require_provider_configuration(settings: Settings, kind: str) -> None:
    if provider_status(settings, kind)["status"] == "unavailable":
        raise ConfigurationUnavailable()


def get_settings() -> Settings:
    return Settings()
