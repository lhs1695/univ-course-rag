from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import exists, select, type_coerce
from sqlalchemy.orm import Session as DbSession

from app.models.document import EMBEDDING_DIM, Chunk
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


def _chunk_filters(
    course_id: UUID,
    embedder: Embedder,
    excluded_document_ids: Collection[UUID],
) -> list:
    filters = [
        Chunk.course_id == course_id,
        Chunk.embedding_model == embedder.index_identity,
    ]
    if excluded_document_ids:
        filters.append(Chunk.document_id.not_in(excluded_document_ids))
    return filters


def _postgres_retrieval_statement(
    course_id: UUID,
    embedder: Embedder,
    query_vec: list[float],
    *,
    top_k: int,
    min_score: float,
    excluded_document_ids: Collection[UUID],
):
    vector = type_coerce(Chunk.embedding, Vector(EMBEDDING_DIM))
    distance = vector.cosine_distance(query_vec).label("distance")
    return (
        select(Chunk.id, Chunk.document_id, Chunk.page, Chunk.text, distance)
        .where(
            *_chunk_filters(course_id, embedder, excluded_document_ids),
            distance <= 1.0 - min_score,
        )
        .order_by(distance)
        .limit(top_k)
    )


def _search_hit(
    chunk_id: UUID,
    document_id: UUID,
    page: int | None,
    text: str,
    score: float,
) -> SearchHit:
    snippet = text.strip()
    if len(snippet) > SNIPPET_CHARS:
        snippet = snippet[:SNIPPET_CHARS]
    return SearchHit(
        chunk_id=chunk_id,
        document_id=document_id,
        page=page,
        snippet=snippet,
        score=score,
    )


def retrieve_chunks(
    db: DbSession,
    course_id: UUID,
    query: str,
    embedder: Embedder,
    *,
    top_k: int = SEARCH_TOP_K,
    min_score: float = SEARCH_MIN_SCORE,
    excluded_document_ids: Collection[UUID] = (),
) -> list[SearchHit]:
    """Course-scoped vector top-k. Below min_score → empty, never a guess."""
    query = query.strip()
    if not query:
        return []
    filters = _chunk_filters(course_id, embedder, excluded_document_ids)
    if not db.scalar(select(exists().where(*filters))):
        return []
    query_vec = embedder.embed([query])[0]
    if db.get_bind().dialect.name == "postgresql":
        statement = _postgres_retrieval_statement(
            course_id,
            embedder,
            query_vec,
            top_k=top_k,
            min_score=min_score,
            excluded_document_ids=excluded_document_ids,
        )
        rows = db.execute(statement).all()
        return [
            _search_hit(chunk_id, document_id, page, text, 1.0 - float(distance))
            for chunk_id, document_id, page, text, distance in rows
        ]

    chunks = db.execute(select(Chunk).where(*filters)).scalars().all()
    ranked: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        ranked.append((cosine_similarity(query_vec, chunk.embedding), chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    hits: list[SearchHit] = []
    for score, chunk in ranked[:top_k]:
        if score < min_score:
            break
        hits.append(
            _search_hit(chunk.id, chunk.document_id, chunk.page, chunk.text, score)
        )
    return hits


def has_incompatible_chunks(
    db: DbSession,
    course_id: UUID,
    embedder: Embedder,
    *,
    excluded_document_ids: Collection[UUID] = (),
) -> bool:
    filters = [
        Chunk.course_id == course_id,
        Chunk.embedding_model != embedder.index_identity,
    ]
    if excluded_document_ids:
        filters.append(Chunk.document_id.not_in(excluded_document_ids))
    return bool(db.scalar(select(exists().where(*filters))))
