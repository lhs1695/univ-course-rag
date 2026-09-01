from pathlib import Path

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
    llm_backend: str = "fake"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"


def get_settings() -> Settings:
    return Settings()
