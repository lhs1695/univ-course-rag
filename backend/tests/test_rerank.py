"""Offline API/ID/resource contracts; scripted scores are not semantic evidence."""

import json
from uuid import UUID

import httpx
import pytest
from app.config import ConfigurationUnavailable, Settings, provider_status
from app.services.fusion import FusedHit
from app.services.rerank import (
    MAX_RERANK_CANDIDATES,
    FakeReranker,
    RerankedHit,
    RerankError,
    RerankTimeout,
    SiliconFlowReranker,
    build_reranker,
    rerank_candidates,
)


def _candidate(index: int) -> FusedHit:
    return FusedHit(UUID(int=index), UUID(int=100), 2, "snippet", 0.4, 1.0, 1, 1, 2 / 61)


def _transport(monkeypatch, handler):
    original = httpx.Client
    clients = []
    options = []

    def factory(**kwargs):
        options.append(kwargs)
        client = original(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr("app.services.rerank.httpx.Client", factory)
    return clients, options


def _adapter() -> SiliconFlowReranker:
    return SiliconFlowReranker("test-only-secret", "https://example.invalid/v1/", "test-model", 7.0)


def test_disabled_is_default_and_does_not_construct_client(monkeypatch) -> None:
    monkeypatch.setattr("app.services.rerank.httpx.Client", lambda **_kwargs: pytest.fail("disabled"))
    settings = Settings(_env_file=None, siliconflow_api_key="")
    assert build_reranker(settings) is None
    assert provider_status(settings, "reranking")["status"] == "disabled"


@pytest.mark.parametrize("overrides", [
    {"siliconflow_api_key": ""},
    {"reranker_model": " "},
    {"reranker_base_url": "invalid"},
    {"reranker_base_url": "https://user:secret@example.invalid"},
    {"reranker_base_url": "https://example.invalid?key=secret"},
    {"reranker_backend": "unknown"},
    {"reranker_backend": "fake"},
    {"retrieval_strategy": "dense"},
])
def test_enabled_configuration_never_falls_back_to_fake(overrides) -> None:
    settings = Settings(_env_file=None, **{
        "retrieval_strategy": "hybrid", "reranker_backend": "siliconflow",
        "siliconflow_api_key": "test-only", **overrides,
    })
    with pytest.raises(ConfigurationUnavailable):
        build_reranker(settings)


def test_api_maps_out_of_order_indices_to_original_candidates_and_closes(monkeypatch) -> None:
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"results": [
            {"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.2},
        ]})

    clients, options = _transport(monkeypatch, handler)
    adapter = _adapter()
    assert adapter.score("synthetic query", ["first body", "second body"]) == [0.2, 0.9]
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://example.invalid/v1/rerank"
    assert request.headers["authorization"] == "Bearer test-only-secret"
    assert json.loads(request.content) == {
        "model": "test-model", "query": "synthetic query",
        "documents": ["first body", "second body"], "top_n": 2, "return_documents": False,
    }
    assert options == [{"timeout": 7.0, "follow_redirects": False, "trust_env": False}]
    assert clients[0].is_closed


@pytest.mark.parametrize("payload", [
    {}, {"results": []},
    {"results": [{"index": 0, "relevance_score": 0.3}] * 2},
    {"results": [{"index": 1, "relevance_score": 0.3}]},
    {"results": [{"index": -1, "relevance_score": 0.3}]},
    {"results": [{"index": True, "relevance_score": 0.3}]},
    {"results": [{"index": "0", "relevance_score": 0.3}]},
    {"results": [{"index": 0, "relevance_score": True}]},
    {"results": [{"index": 0, "relevance_score": "0.3"}]},
    {"results": [{"index": 0, "relevance_score": float("nan")}]},
    {"results": [{"index": 0, "relevance_score": float("inf")}]},
    {"results": [{"index": 0}]},
])
def test_invalid_response_rejects_complete_request_without_partial_order(monkeypatch, payload) -> None:
    clients, _ = _transport(monkeypatch, lambda _request: httpx.Response(200, content=json.dumps(payload)))
    with pytest.raises(RerankError) as exc:
        _adapter().score("query-private", ["body-private"])
    assert "private" not in str(exc.value)
    assert clients[0].is_closed


@pytest.mark.parametrize("failure", ["timeout", "connect", "status", "redirect", "json"])
def test_provider_failures_are_safe_close_and_never_retry(monkeypatch, failure) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("provider-private", request=request)
        if failure == "connect":
            raise httpx.ConnectError("provider-private", request=request)
        if failure == "json":
            return httpx.Response(200, text="provider-private")
        return httpx.Response(503 if failure == "status" else 302, text="provider-private")

    clients, _ = _transport(monkeypatch, handler)
    with pytest.raises(RerankTimeout if failure == "timeout" else RerankError) as exc:
        _adapter().score("query-private", ["body-private"])
    assert "private" not in str(exc.value)
    assert clients[0].is_closed
    assert len(calls) == 1


@pytest.mark.parametrize("query, passages", [
    ("x" * 2001, ["body"]), ("query", ["x" * 1201]), ("query", [" "]),
    ("query", ["body"] * (MAX_RERANK_CANDIDATES + 1)),
])
def test_resource_limits_fail_before_client_construction(monkeypatch, query, passages) -> None:
    monkeypatch.setattr("app.services.rerank.httpx.Client", lambda **_kwargs: pytest.fail("over limit"))
    with pytest.raises(RerankError):
        _adapter().score(query, passages)


def test_empty_candidates_do_not_call_provider(monkeypatch) -> None:
    monkeypatch.setattr("app.services.rerank.httpx.Client", lambda **_kwargs: pytest.fail("empty"))
    assert _adapter().score("query", []) == []
    fake = FakeReranker()
    assert rerank_candidates("query", [], [], fake) == []
    assert fake.calls == []


def test_rerank_retains_all_candidates_scores_and_stable_ties() -> None:
    first, second, third = [_candidate(index) for index in [3, 1, 2]]
    fake = FakeReranker([0.5, 0.9, 0.5])
    hits = rerank_candidates("query", [first, second, third], ["a", "b", "c"], fake)
    assert hits == [RerankedHit(second, 0.9), RerankedHit(first, 0.5), RerankedHit(third, 0.5)]
    assert first.cosine_score == 0.4
    assert first.bm25_score == 1.0
    assert first.rrf_score == 2 / 61


@pytest.mark.parametrize("scores", [[], [True], [float("nan")], [float("inf")]])
def test_bad_fake_scores_cannot_bypass_the_pipeline_contract(scores) -> None:
    with pytest.raises(RerankError):
        rerank_candidates("query", [_candidate(1)], ["body"], FakeReranker(scores))
