from pathlib import Path

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
    llm_backend: str = "fake"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"


def get_settings() -> Settings:
    return Settings()
