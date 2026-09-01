from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from app.config import Settings, get_settings
from app.models.document import EMBEDDING_DIM

# Token / CJK-bigram hashing so shared terms sit closer than unrelated text.
# Exact-string SHA was too jumpy for retrieval tests. Same model for ingest and query.


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbedder:
    """Deterministic 1024-d vectors. No network. Overlapping tokens → higher cosine."""

    def __init__(self, model_name: str = "fake-bge-m3") -> None:
        self.model_name = model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_token_vector(text) for text in texts]


def _tokens(text: str) -> list[str]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9]+", lowered)
    grams: list[str] = []
    for run in re.findall(r"[\u4e00-\u9fff]+", lowered):
        if len(run) == 1:
            grams.append(run)
        else:
            grams.extend(run[i : i + 2] for i in range(len(run) - 1))
    return words + grams or [lowered or "empty"]


def _token_unit(token: str) -> list[float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    raw = digest
    while len(raw) < EMBEDDING_DIM:
        raw += hashlib.sha256(raw).digest()
    return [(raw[i] / 127.5) - 1.0 for i in range(EMBEDDING_DIM)]


def _token_vector(text: str) -> list[float]:
    acc = [0.0] * EMBEDDING_DIM
    for token in _tokens(text):
        unit = _token_unit(token)
        for i, value in enumerate(unit):
            acc[i] += value
    norm = math.sqrt(sum(x * x for x in acc)) or 1.0
    return [x / norm for x in acc]


class SiliconFlowEmbedder:
    def __init__(self, api_key: str, base_url: str, model_name: str) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self.model_name, input=texts)
        by_index = {item.index: item.embedding for item in response.data}
        return [list(by_index[i]) for i in range(len(texts))]


def build_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    if settings.embedder_backend == "siliconflow" and settings.siliconflow_api_key:
        return SiliconFlowEmbedder(
            api_key=settings.siliconflow_api_key,
            base_url=settings.embedding_base_url,
            model_name=settings.embedding_model,
        )
    return FakeEmbedder(model_name=settings.embedding_model)


def get_embedder() -> Embedder:
    return build_embedder()
