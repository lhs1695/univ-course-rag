"""Bounded SiliconFlow v1 rerank API adapter; scores order, never admit evidence.

Uses HTTPX 0.28.1 (BSD-3-Clause), not copied model/inference code. The public
OpenAPI contract and model attribution are recorded in docs/engineering.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings, get_settings, require_provider_configuration
from app.services.fusion import FusedHit
from app.services.upstream import UpstreamTimeout, UpstreamUnavailable

MAX_RERANK_CANDIDATES = 64
RERANK_PASSAGE_CHARS = 1200
MAX_RERANK_QUERY_CHARS = 2000


class RerankError(UpstreamUnavailable):
    error_code = "RERANK_FAILED"
    message = "候选重排失败，本次未改用其他排序。"


class RerankTimeout(UpstreamTimeout):
    error_code = "RERANK_TIMEOUT"
    message = "候选重排超时，请稍后显式重试。"


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


def _check_input(query: str, passages: list[str]) -> None:
    if (
        not query.strip() or len(query) > MAX_RERANK_QUERY_CHARS
        or len(passages) > MAX_RERANK_CANDIDATES
        or any(not passage.strip() or len(passage) > RERANK_PASSAGE_CHARS for passage in passages)
    ):
        raise RerankError() from None


def _check_scores(scores: Sequence[float], count: int) -> None:
    if len(scores) != count or any(
        isinstance(score, bool) or not isinstance(score, (int, float))
        or not math.isfinite(score) for score in scores
    ):
        raise RerankError() from None


class FakeReranker:
    """Scripted scores only. No term overlap or pretend semantic inference."""

    def __init__(self, scores: Sequence[float] | None = None) -> None:
        self.scores = None if scores is None else list(scores)
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: list[str]) -> list[float]:
        _check_input(query, passages)
        self.calls.append((query, list(passages)))
        scores = [0.0] * len(passages) if self.scores is None else list(self.scores)
        _check_scores(scores, len(passages))
        return scores


class _Result(BaseModel):
    index: int = Field(strict=True, ge=0)
    relevance_score: float = Field(strict=True, allow_inf_nan=False)


class _Response(BaseModel):
    results: list[_Result]


class SiliconFlowReranker:
    def __init__(self, api_key: str, base_url: str, model_name: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/rerank"
        self.model_name = model_name
        self._timeout_seconds = timeout_seconds

    def score(self, query: str, passages: list[str]) -> list[float]:
        _check_input(query, passages)
        if not passages:
            return []
        try:
            # Per-call context closes connections on success and every failure.
            # No redirects, environment proxy injection or automatic retries.
            with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False, trust_env=False) as client:
                response = client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self.model_name, "query": query, "documents": passages,
                        "top_n": len(passages), "return_documents": False,
                    },
                )
                response.raise_for_status()
                result = _Response.model_validate(response.json())
        except httpx.TimeoutException:
            raise RerankTimeout() from None
        except (httpx.HTTPError, ValueError, ValidationError):
            raise RerankError() from None
        by_index = {row.index: row.relevance_score for row in result.results}
        if len(result.results) != len(passages) or set(by_index) != set(range(len(passages))):
            raise RerankError() from None
        return [by_index[index] for index in range(len(passages))]


@dataclass(frozen=True)
class RerankedHit:
    candidate: FusedHit
    rerank_score: float


def rerank_candidates(
    query: str, candidates: Sequence[FusedHit], passages: list[str], reranker: Reranker,
) -> list[RerankedHit]:
    """Retain every supplied candidate; tied scores retain the RRF input order."""
    _check_input(query, passages)
    if len(candidates) != len(passages):
        raise RerankError() from None
    if not candidates:
        return []
    scores = reranker.score(query, passages)
    _check_scores(scores, len(candidates))
    hits = [RerankedHit(hit, float(score)) for hit, score in zip(candidates, scores, strict=True)]
    return sorted(hits, key=lambda hit: -hit.rerank_score)


def build_reranker(settings: Settings | None = None) -> Reranker | None:
    settings = settings or get_settings()
    require_provider_configuration(settings, "reranking")
    if settings.reranker_backend == "disabled":
        return None
    return SiliconFlowReranker(
        settings.siliconflow_api_key, settings.reranker_base_url,
        settings.reranker_model, settings.upstream_timeout_seconds,
    )


def get_reranker() -> Reranker | None:
    return build_reranker()
