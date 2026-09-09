from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.document import Chunk
from app.services.embedder import Embedder

SEARCH_TOP_K = 8
SEARCH_MIN_SCORE = 0.15
SNIPPET_CHARS = 240
EMBEDDING_MISMATCH = "EMBEDDING_MISMATCH"
EMBEDDING_MISMATCH_MESSAGE = "向量模型已切换，请从原文件重新入库。"


@dataclass
class SearchHit:
    chunk_id: UUID
    document_id: UUID
    page: int | None
    snippet: str
    score: float


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def retrieve_chunks(
    db: DbSession,
    course_id: UUID,
    query: str,
    embedder: Embedder,
    *,
    top_k: int = SEARCH_TOP_K,
    min_score: float = SEARCH_MIN_SCORE,
) -> list[SearchHit]:
    """Course-scoped vector top-k. Below min_score → empty, never a guess."""
    query = query.strip()
    if not query:
        return []
    chunks = db.execute(
        select(Chunk).where(
            Chunk.course_id == course_id,
            Chunk.embedding_model == embedder.index_identity,
        )
    ).scalars().all()
    if not chunks:
        return []
    query_vec = embedder.embed([query])[0]
    ranked: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        ranked.append((cosine_similarity(query_vec, chunk.embedding), chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    hits: list[SearchHit] = []
    for score, chunk in ranked[:top_k]:
        if score < min_score:
            break
        snippet = chunk.text.strip()
        if len(snippet) > SNIPPET_CHARS:
            snippet = snippet[:SNIPPET_CHARS]
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                page=chunk.page,
                snippet=snippet,
                score=score,
            )
        )
    return hits


def has_incompatible_chunks(
    db: DbSession, course_id: UUID, embedder: Embedder
) -> bool:
    identities = db.execute(
        select(Chunk.embedding_model).where(Chunk.course_id == course_id)
    ).scalars().all()
    return any(identity != embedder.index_identity for identity in identities)
