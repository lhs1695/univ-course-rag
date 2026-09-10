import logging
import re

import pytest
from app.db import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError


def test_health_does_not_access_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable_db():
        raise AssertionError("liveness must not access the database")
        yield

    monkeypatch.setitem(app.dependency_overrides, get_db, unavailable_db)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_stable_503_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableDatabase:
        def execute(self, statement: object) -> None:
            raise SQLAlchemyError("connection details must not escape")

    def unavailable_db():
        yield UnavailableDatabase()

    monkeypatch.setitem(app.dependency_overrides, get_db, unavailable_db)
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_request_id_is_generated_or_echoed_and_logged_safely(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.main"):
        generated = client.get("/health")
        echoed = client.get("/health", headers={"X-Request-ID": "trace-42"})
    generated_id = generated.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated_id)
    assert echoed.headers["X-Request-ID"] == "trace-42"
    assert "request_id=trace-42" in caplog.text
    assert any(record.request_id == "trace-42" for record in caplog.records)


@pytest.mark.parametrize("value", ["", "bad value", "a" * 65])
def test_invalid_external_request_id_is_replaced(client: TestClient, value: str) -> None:
    response = client.get("/health", headers={"X-Request-ID": value})
    replacement = response.headers["X-Request-ID"]
    assert replacement != value
    assert re.fullmatch(r"[0-9a-f]{32}", replacement)
