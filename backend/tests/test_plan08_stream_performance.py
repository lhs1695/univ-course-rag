"""Fake only. Loopback HTTP measures actual SSE arrival (TestClient buffers)."""

from __future__ import annotations

import asyncio
import json
import math
import os
import platform
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest
import uvicorn
from app.api import ask as ask_api
from app.api.ask import stream_ask_events
from app.api.schemas import AskRequest
from app.config import Settings, get_settings
from app.db import Base, get_db
from app.main import app
from app.models.course import CourseMember, CourseMemberRole
from app.models.query_log import QueryLog
from app.models.user import UserRole
from app.security.deps import CourseAccess
from app.services.embedder import FakeEmbedder, get_embedder
from app.services.llm import FakeLLM, get_llm
from app.services.rerank import get_reranker
from app.services.upstream import UpstreamTimeout, UpstreamUnavailable
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from tests.conftest import add_user
from tests.test_retrieve import _scaled_chunk, add_course, add_member, login_as

QUERY = "请说明本课的事务隔离级别"


def parse_events(text):
    events = []
    for frame in text.strip().split("\n\n"):
        lines = frame.splitlines()
        name = next(line[7:] for line in lines if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        events.append((name, data))
    return events


def assert_terminal(events, name="final"):
    terminals = [event for event in events if event[0] in {"final", "error"}]
    assert len(terminals) == 1
    assert terminals[0] == events[-1]
    assert terminals[0][0] == name
    return terminals[0][1]


@pytest.fixture
def ask_setup(client, db, monkeypatch):
    monkeypatch.setattr("app.api.ask.get_settings", lambda: Settings(_env_file=None))
    user = add_user(db, "stream-user", "pass", UserRole.student)
    course = add_course(db, "Fake stream")
    add_member(db, course, user, CourseMemberRole.student)
    chunk = _scaled_chunk(db, course, FakeEmbedder(), QUERY, "事务隔离：读已提交。", 1.0)
    login_as(client, "stream-user", "pass")
    member = db.scalar(select(CourseMember).where(CourseMember.course_id == course.id))
    return course, chunk, CourseAccess(course, member, user)


def test_fake_stream_concatenation():
    llm = FakeLLM(scripted="逐块输出的回答" * 12)
    chunks = list(llm.generate_stream("fake"))
    assert len(chunks) > 1
    assert "".join(chunks) == llm.generate("fake")


def test_generate_only_provider_fallback(client, ask_setup):
    course, _, _ = ask_setup

    class GenerateOnly:
        def generate(self, prompt):
            return FakeLLM().generate(prompt)

    app.dependency_overrides[get_llm] = GenerateOnly
    events = parse_events(client.post(
        f"/courses/{course.id}/ask/stream", json={"query": QUERY},
    ).text)
    result = assert_terminal(events)
    assert result["error_code"] is None
    assert "".join(data["text"] for name, data in events if name == "delta") == result["answer"]


def test_stream_event_order_and_json_compatibility(client, db, ask_setup):
    course, chunk, _ = ask_setup
    response = client.post(f"/courses/{course.id}/ask/stream", json={"query": QUERY})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    events = parse_events(response.text)
    assert events[:2] == [("phase", {"phase": "retrieve"}), ("phase", {"phase": "generate"})]
    assert len(events[2:-1]) > 1
    assert all(name == "delta" for name, _ in events[2:-1])
    final = assert_terminal(events)
    assert "".join(data["text"] for name, data in events if name == "delta") == final["answer"]
    assert final["citations"][0]["chunk_id"] == str(chunk.id)
    assert final == client.post(f"/courses/{course.id}/ask", json={"query": QUERY}).json()
    logs = list(db.scalars(select(QueryLog)))
    assert len(logs) == 2
    assert all(log.outcome == "cited_answer" for log in logs)


@pytest.mark.parametrize("no_hits", [False, True])
def test_no_evidence_unique_final_without_provisional_text(client, ask_setup, monkeypatch, no_hits):
    course, _, _ = ask_setup
    if no_hits:
        monkeypatch.setattr("app.api.ask.retrieve_chunks", lambda *a, **kw: [])
    app.dependency_overrides[get_llm] = lambda: FakeLLM(scripted="NO_EVIDENCE")
    events = parse_events(client.post(
        f"/courses/{course.id}/ask/stream", json={"query": QUERY},
    ).text)
    final = assert_terminal(events)
    assert final["error_code"] == "NO_EVIDENCE"
    assert final["answer"] is None and final["citations"] == []
    assert not any(name == "delta" for name, _ in events)


@pytest.mark.parametrize("failure", [UpstreamTimeout, UpstreamUnavailable, RuntimeError])
def test_error_and_slow_timeout_unique_terminal(client, db, ask_setup, failure):
    course, _, _ = ask_setup

    class FailingLLM(FakeLLM):
        def generate_stream(self, prompt):
            yield "未完成且不应泄漏"
            time.sleep(0.01)  # Fake upstream timeout mapping; no network.
            raise failure("private-provider-detail")

    app.dependency_overrides[get_llm] = FailingLLM
    response = client.post(f"/courses/{course.id}/ask/stream", json={"query": QUERY})
    events = parse_events(response.text)
    terminal = assert_terminal(events, "error")
    expected = "ASK_STREAM_FAILED" if failure is RuntimeError else failure.error_code
    assert terminal["error_code"] == expected
    assert "private-provider-detail" not in response.text
    assert not any(name == "delta" for name, _ in events)
    if failure is not RuntimeError:
        assert db.scalar(select(QueryLog)).error_code == expected


@pytest.mark.parametrize("disconnect", [False, True])
def test_cancel_closes_provider_and_rolls_back(client, db, ask_setup, disconnect):
    _, _, access = ask_setup
    provider_closed = threading.Event()

    class PausedLLM(FakeLLM):
        def generate_stream(self, prompt):
            try:
                yield "尚未验证的文本"
                pytest.fail("cancel must not advance provider again")
            finally:
                provider_closed.set()

    class Request:
        disconnected = False

        async def is_disconnected(self):
            return self.disconnected

    async def exercise():
        request = Request()
        events = stream_ask_events(
            request, AskRequest(query=QUERY), access, db, FakeEmbedder(), PausedLLM(), None,
        )
        assert "retrieve" in await anext(events)
        assert "generate" in await anext(events)
        # Observe disconnect at the checkpoint after the first provider chunk.
        original_next = ask_api._next_event

        def next_and_disconnect(iterator):
            result = original_next(iterator)
            request.disconnected = True
            return result

        if disconnect:
            from unittest.mock import patch

            with patch("app.api.ask._next_event", next_and_disconnect):
                assert [event async for event in events] == []
        else:
            # Close at a provider checkpoint through the shared core, then close
            # the response generator (TestClient cannot reliably expose chunks).
            from app.api.ask import _ask_events
            from fastapi import Response

            core = _ask_events(
                AskRequest(query=QUERY), access, db, FakeEmbedder(), PausedLLM(), None,
                Response(), stream=True,
            )
            next(core)
            next(core)
            assert next(core) is None
            core.close()
            await events.aclose()

    asyncio.run(exercise())
    assert provider_closed.is_set()
    assert not db.in_transaction()
    assert db.scalar(select(QueryLog)) is None


@pytest.fixture
def live_fake(tmp_path, monkeypatch):
    """Independent sessions on temporary SQLite; real loopback HTTP, no real DB."""
    engine = create_engine(f"sqlite:///{(tmp_path / 'stream.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    settings = Settings(_env_file=None, llm_backend="fake", embedder_backend="fake",
                        query_expansion_backend="disabled", retrieval_strategy="dense")
    monkeypatch.setattr("app.api.ask.get_settings", lambda: settings)
    with maker() as db:
        courses = []
        for index in range(2):
            user = add_user(db, f"fake-{index}", "pass", UserRole.student)
            course = add_course(db, f"Fake course {index}")
            add_member(db, course, user, CourseMemberRole.student)
            chunk = _scaled_chunk(db, course, FakeEmbedder(), QUERY,
                                  f"仅课程{index}：事务隔离采用读已提交。", 1.0)
            courses.append((str(course.id), str(chunk.id), str(user.id)))

    def get_test_db():
        with maker() as db:
            yield db

    class CourseLLM(FakeLLM):
        def generate(self, prompt):
            if "故障请求" in prompt:
                raise UpstreamTimeout()
            label = "课程0" if "仅课程0" in prompt else "课程1"
            return label + "的回答：" + super().generate(prompt)

    saved = app.dependency_overrides.copy()
    app.dependency_overrides.update({
        get_db: get_test_db, get_settings: lambda: settings,
        get_embedder: FakeEmbedder, get_llm: lambda: CourseLLM(), get_reranker: lambda: None,
    })
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    clients = []
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        for index in range(2):
            client = httpx.Client(base_url=url, timeout=10, trust_env=False)
            clients.append(client)
            assert client.post("/auth/login", json={
                "username": f"fake-{index}", "password": "pass",
            }).status_code == 200
        yield clients, courses, maker
    finally:
        for client in clients:
            client.close()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)
        engine.dispose()
        assert not thread.is_alive()


def timed_request(client, course_id, query=QUERY):
    started = time.perf_counter()
    first = None
    frames = []
    frame = []
    with client.stream("POST", f"/courses/{course_id}/ask/stream", json={"query": query}) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line:
                frame.append(line)
            elif frame:
                if first is None:
                    first = time.perf_counter() - started
                frames.extend(parse_events("\n".join(frame)))
                frame = []
    elapsed = time.perf_counter() - started
    assert first is not None
    return frames, first * 1000, elapsed * 1000


def test_two_users_courses_and_failure_context_do_not_cross(live_fake):
    clients, courses, maker = live_fake
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(timed_request, clients[i], courses[i][0]) for i in range(2)]
        results = [future.result() for future in futures]
        for index, (events, _, _) in enumerate(results):
            final = assert_terminal(events)
            assert f"课程{index}" in final["answer"]
            assert f"课程{1 - index}" not in final["answer"]
            assert [citation["chunk_id"] for citation in final["citations"]] == [courses[index][1]]
        futures = [pool.submit(timed_request, clients[i], courses[i][0],
                               QUERY + ("故障请求" if i == 0 else "")) for i in range(2)]
        assert assert_terminal(futures[0].result()[0], "error")["error_code"] == "UPSTREAM_TIMEOUT"
        assert assert_terminal(futures[1].result()[0])["error_code"] is None
    assert clients[0].post(f"/courses/{courses[1][0]}/ask/stream", json={"query": QUERY}).status_code == 403
    with maker() as db:
        logs = list(db.scalars(select(QueryLog)))
        assert len(logs) == 4
        for log in logs:
            index = next(i for i, course in enumerate(courses) if course[0] == str(log.course_id))
            assert str(log.user_id) == courses[index][2]
            assert courses[1 - index][1] not in log.chunk_ids
            assert (log.error_code == "UPSTREAM_TIMEOUT") == ("故障请求" in log.query)


def percentile(samples, quantile):
    return sorted(samples)[math.ceil(len(samples) * quantile) - 1]


def test_fake_concurrency_baseline(live_fake):
    clients, courses, _ = live_fake
    summary = []
    raw = []
    for concurrency in (1, 5, 10):
        # Warm-up (not timed); 20 measured requests, even split across two users/courses.
        assert_terminal(timed_request(clients[0], courses[0][0])[0])
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(timed_request, clients[i % 2], courses[i % 2][0]) for i in range(20)]
            samples = []
            for index, future in enumerate(futures):
                try:
                    events, first, end = future.result()
                    final = assert_terminal(events)
                    assert final["error_code"] is None
                    assert final["citations"][0]["chunk_id"] == courses[index % 2][1]
                    samples.append({"request": index, "course": index % 2, "ok": True,
                                    "first_ms": first, "e2e_ms": end})
                except Exception as exc:  # noqa: BLE001 - retain every failed sample.
                    samples.append({"request": index, "course": index % 2, "ok": False,
                                    "error": type(exc).__name__})
        wall = time.perf_counter() - started
        good = [sample for sample in samples if sample["ok"]]
        firsts = [sample["first_ms"] for sample in good]
        ends = [sample["e2e_ms"] for sample in good]
        row = {"concurrency": concurrency, "success": len(good), "fail": 20 - len(good),
               "wall_s": wall, "throughput_rps": len(good) / wall,
               "first_p50_ms": percentile(firsts, .5) if good else None,
               "first_p95_ms": percentile(firsts, .95) if good else None,
               "e2e_p50_ms": percentile(ends, .5) if good else None,
               "e2e_p95_ms": percentile(ends, .95) if good else None,
               "error_rate": (20 - len(good)) / 20}
        summary.append(row)
        raw.append({"concurrency": concurrency, "samples": samples})
        print("PLAN08_BASELINE " + json.dumps(row))
    report = {"at_utc": datetime.now(UTC).isoformat(), "os": platform.platform(),
              "python": platform.python_version(), "cpu_count": os.cpu_count(),
              "versions": {name: version(name) for name in ("fastapi", "starlette", "uvicorn", "httpx", "sqlalchemy")},
              "model": "FakeEmbedder + request-local CourseLLM(FakeLLM)",
              "summary": summary, "raw": raw}
    # Opt-in report write: the -s acceptance run produces the committed evidence.
    output = os.environ.get("PLAN08_BASELINE_OUTPUT")
    if output:
        path = Path(output).resolve()
        assert path.parent == Path(__file__).resolve().parents[2] / "docs"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert all(row["success"] == 20 and row["fail"] == 0 for row in summary)
