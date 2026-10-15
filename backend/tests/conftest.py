# dotenv must be disabled before app.db constructs its engine during import.

import pytest
from app.config import Settings

Settings.model_config["env_file"] = None

from app.db import Base, get_db, get_session_maker
from app.main import app
from app.models import (  # noqa: F401
    Chunk,
    Course,
    CourseMember,
    Document,
    IngestJob,
    QueryLog,
)
from app.models.user import User, UserRole
from app.security.passwords import hash_password
from app.services.embedder import FakeEmbedder, get_embedder
from app.services.llm import FakeLLM, get_llm
from app.services.question_groups import get_question_embedder
from app.services.rerank import get_reranker
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    def override_get_db():
        yield db

    def override_maker():
        return TestingSessionLocal

    def override_embedder():
        return FakeEmbedder()

    def override_llm():
        return FakeLLM()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_maker] = override_maker
    app.dependency_overrides[get_embedder] = override_embedder
    app.dependency_overrides[get_llm] = override_llm
    app.dependency_overrides[get_reranker] = lambda: None
    app.dependency_overrides[get_question_embedder] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add_user(db: Session, username: str, password: str, role: UserRole) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
