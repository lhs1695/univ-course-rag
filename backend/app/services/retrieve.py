from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import exists, func, select, type_coerce
from sqlalchemy.orm import Session as DbSession

from app.models.document import EMBEDDING_DIM, Chunk, Document
from app.services.embedder import Embedder
from app.services.fusion import (
    MAX_FUSED_CANDIDATES,
    MAX_RRF_K,
    RRF_K,
    DenseCandidate,
    FusedHit,
    FusionError,
    KeywordCandidate,
    fuse_rrf,
)
from app.services.rerank import (
    MAX_RERANK_CANDIDATES,
    RERANK_PASSAGE_CHARS,
    Reranker,
    RerankError,
    rerank_candidates,
)

SEARCH_TOP_K = 8
# Recall budget per branch, independent of the final context count. This is a
# bounded engineering default, not a calibrated relevance/admission parameter.
HYBRID_CANDIDATE_K = 32
# Fake vectors have their own golden-test calibration. SiliconFlow's 0.45
# default is evidenced in docs/evaluation-results.md#stage49-threshold-results.
SEARCH_MIN_SCORE = 0.15
SILICONFLOW_SEARCH_MIN_SCORE = 0.45
SNIPPET_CHARS = 240
EMBEDDING_MISMATCH = "EMBEDDING_MISMATCH"
EMBEDDING_MISMATCH_MESSAGE = "向量模型已切换，请从原文件重新入库。"
KEYWORD_LIMIT = "KEYWORD_LIMIT"
KEYWORD_LIMIT_MESSAGE = "关键词检索超出资源上限，本次未改用其他检索策略。"
RETRIEVAL_STRATEGY = "RETRIEVAL_STRATEGY"
RETRIEVAL_STRATEGY_MESSAGE = "检索策略无效，本次未执行检索。"
RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
RETRIEVAL_FAILED_MESSAGE = "检索结果无法合并，本次未改为其他策略。"
RETRIEVAL_STRATEGIES = frozenset({"dense", "hybrid"})


class RetrievalStrategyError(ValueError):
    """An unknown strategy must fail before either branch runs."""


@dataclass
class SearchHit:
    chunk_id: UUID
    document_id: UUID
    page: int | None
    snippet: str
    score: float


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _default_min_score(embedder: Embedder) -> float:
    """Keep Fake fixtures on their contract; calibrate the live vector space separately."""
    if embedder.index_identity.startswith("siliconflow|"):
        return SILICONFLOW_SEARCH_MIN_SCORE
    return SEARCH_MIN_SCORE


def _chunk_filters(
    course_id: UUID,
    embedder: Embedder,
    excluded_document_ids: Collection[UUID],
) -> list:
    filters = [
        Chunk.course_id == course_id,
        Chunk.embedding_model == embedder.index_identity,
        Chunk.document_id.in_(
            select(Document.id).where(
                Document.course_id == course_id, Document.retrieval_enabled.is_(True),
            )
        ),
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
    min_score: float | None,
    excluded_document_ids: Collection[UUID],
):
    vector = type_coerce(Chunk.embedding, Vector(EMBEDDING_DIM))
    distance = vector.cosine_distance(query_vec).label("distance")
    filters = _chunk_filters(course_id, embedder, excluded_document_ids)
    if min_score is not None:
        filters.append(distance <= 1.0 - min_score)
    return (
        select(Chunk.id, Chunk.document_id, Chunk.page, Chunk.text, distance)
        .where(*filters)
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


def _retrieve_dense(
    db: DbSession,
    course_id: UUID,
    query: str,
    embedder: Embedder,
    *,
    top_k: int = SEARCH_TOP_K,
    min_score: float | None = None,
    excluded_document_ids: Collection[UUID] = (),
) -> list[SearchHit]:
    """Course-scoped vector recall; None leaves admission to a later selector."""
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
        if min_score is not None and score < min_score:
            break
        hits.append(
            _search_hit(chunk.id, chunk.document_id, chunk.page, chunk.text, score)
        )
    return hits


def merge_definition_hits(
    db: DbSession, course_id: UUID, term: str, embedder: Embedder,
    hits: Sequence[SearchHit],
) -> list[SearchHit]:
    """Prepend up to four literal matches, scoped to the active course/index.

    Reuse SQLAlchemy's escaped ILIKE rather than interpreting term as a pattern.
    Lexical additions have no measured cosine score; zero does not imply admission
    through the dense threshold. This exception is only for definition evidence.
    """
    if not term.strip():
        return list(hits)
    rows = db.scalars(
        select(Chunk)
        .where(*_chunk_filters(course_id, embedder, ()),
               Chunk.text.icontains(term.strip(), autoescape=True))
        .order_by(Chunk.page, Chunk.id)
        .limit(4)
    ).all()
    by_id = {hit.chunk_id: hit for hit in hits}
    merged = [
        by_id.get(chunk.id) or _search_hit(
            chunk.id, chunk.document_id, chunk.page, chunk.text, 0.0,
        )
        for chunk in rows
    ]
    seen = {hit.chunk_id for hit in merged}
    return (merged + [hit for hit in hits if hit.chunk_id not in seen])[:SEARCH_TOP_K]


def retrieve_expanded_chunks(
    db: DbSession,
    course_id: UUID,
    query: str,
    embedder: Embedder,
    subqueries: Sequence[str],
    *,
    top_k: int = SEARCH_TOP_K,
    min_score: float | None = None,
    excluded_document_ids: Collection[UUID] = (),
) -> list[SearchHit]:
    """Subquery-first quota union, admitted only by original-query cosine."""
    if not subqueries or top_k <= 0:
        return []
    branches = [
        _retrieve_dense(
            db, course_id, branch_query, embedder, top_k=20, min_score=None,
            excluded_document_ids=excluded_document_ids,
        )
        for branch_query in [*subqueries, query]
    ]
    query_vec = embedder.embed([query.strip()])[0]
    threshold = _default_min_score(embedder) if min_score is None else min_score
    seen: set[UUID] = set()
    hits = []
    for depth in range(20):
        for branch in branches:
            if depth >= len(branch):
                continue
            hit = branch[depth]
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            chunk = db.get(Chunk, hit.chunk_id)
            if chunk is None or chunk.embedding is None or len(chunk.embedding) == 0:
                continue
            score = float(cosine_similarity(query_vec, chunk.embedding))
            if score >= threshold:
                hits.append(replace(hit, score=score))
                if len(hits) == top_k:
                    return hits
    return hits


def retrieve_hybrid_candidates(
    db: DbSession,
    course_id: UUID,
    query: str,
    embedder: Embedder,
    *,
    candidate_k: int = HYBRID_CANDIDATE_K,
    excluded_document_ids: Collection[UUID] = (),
    rrf_k: int = RRF_K,
) -> list[FusedHit]:
    """Return the entire bounded union, including unadmitted lexical-only rows.

    Callers own course authorization. Both branches scope before recall. No
    final top-k or relevance threshold applies here; R4 can consume this list
    before any evidence selection. Branch failures abort without fallback.
    """
    from app.services.keyword import retrieve_keyword_candidates

    if type(candidate_k) is not int or not 0 <= candidate_k <= MAX_FUSED_CANDIDATES // 2:
        raise FusionError("candidate_limit")
    if type(rrf_k) is not int or not 1 <= rrf_k <= MAX_RRF_K:
        raise FusionError("rank_constant")
    query = query.strip()
    if not query or candidate_k == 0:
        return []
    filters = _chunk_filters(course_id, embedder, excluded_document_ids)
    if not db.scalar(select(exists().where(*filters))):
        return []
    dense_hits = _retrieve_dense(
        db,
        course_id,
        query,
        embedder,
        top_k=candidate_k,
        excluded_document_ids=excluded_document_ids,
    )
    keyword_hits = retrieve_keyword_candidates(
        db,
        course_id,
        query,
        index_identity=embedder.index_identity,
        top_k=candidate_k,
        excluded_document_ids=excluded_document_ids,
    )
    return fuse_rrf(
        [
            DenseCandidate(hit.chunk_id, hit.document_id, hit.page, hit.snippet, hit.score)
            for hit in dense_hits
        ],
        [
            KeywordCandidate(
                hit.chunk_id, hit.document_id, hit.page, hit.snippet, hit.bm25_score
            )
            for hit in keyword_hits
        ],
        rrf_k=rrf_k,
        limit=candidate_k * 2,
    )


def _select_conservative_evidence(
    candidates: Sequence[FusedHit], *, top_k: int, min_score: float
) -> list[SearchHit]:
    """Temporary dense-score gate, not a semantic answer-support selector.

    Lexical-only and low-cosine candidates remain available from the candidate
    service, but cannot authorize generation until a validated selector exists.
    Never threshold BM25/RRF or encode either as SearchHit.score.
    """
    return [
        SearchHit(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            page=hit.page,
            snippet=hit.snippet,
            score=hit.cosine_score,
        )
        for hit in candidates
        if hit.cosine_score is not None and hit.cosine_score >= min_score
    ][:top_k]


def _rerank_hybrid_candidates(
    db: DbSession, course_id: UUID, query: str, embedder: Embedder,
    candidates: Sequence[FusedHit], reranker: Reranker,
    excluded_document_ids: Collection[UUID],
) -> list[FusedHit]:
    if len(candidates) > MAX_RERANK_CANDIDATES:
        raise RerankError() from None
    if not candidates:
        return []
    # Re-check scope and current existence before sending any text upstream.
    rows = db.execute(
        select(
            Chunk.id, Chunk.document_id, Chunk.page,
            func.substr(Chunk.text, 1, RERANK_PASSAGE_CHARS).label("text"),
        ).where(
            *_chunk_filters(course_id, embedder, excluded_document_ids),
            Chunk.id.in_([hit.chunk_id for hit in candidates]),
        )
    ).all()
    by_id = {row.id: row for row in rows}
    current = []
    passages = []
    for hit in candidates:
        row = by_id.get(hit.chunk_id)
        if row is None:
            continue
        if (row.document_id, row.page) != (hit.document_id, hit.page):
            raise RerankError() from None
        body = row.text.strip()
        if not body:
            continue
        current.append(replace(hit, snippet=body[:SNIPPET_CHARS]))
        passages.append(body)
    return [hit.candidate for hit in rerank_candidates(query, current, passages, reranker)]


def retrieve_chunks(
    db: DbSession,
    course_id: UUID,
    query: str,
    embedder: Embedder,
    *,
    top_k: int = SEARCH_TOP_K,
    min_score: float | None = None,
    excluded_document_ids: Collection[UUID] = (),
    strategy: str = "dense",
    rrf_k: int = RRF_K,
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    """Return final evidence. hybrid is a candidate union with a conservative gate."""
    if type(strategy) is not str or strategy not in RETRIEVAL_STRATEGIES:
        raise RetrievalStrategyError()
    if strategy == "dense":
        if reranker is not None:
            raise RetrievalStrategyError()
        return _retrieve_dense(
            db,
            course_id,
            query,
            embedder,
            top_k=top_k,
            min_score=_default_min_score(embedder) if min_score is None else min_score,
            excluded_document_ids=excluded_document_ids,
        )
    if type(top_k) is not int or not 0 <= top_k <= MAX_FUSED_CANDIDATES // 2:
        raise FusionError("candidate_limit")
    candidates = retrieve_hybrid_candidates(
        db,
        course_id,
        query,
        embedder,
        candidate_k=max(HYBRID_CANDIDATE_K, top_k) if top_k else 0,
        excluded_document_ids=excluded_document_ids,
        rrf_k=rrf_k,
    )
    if reranker is not None:
        candidates = _rerank_hybrid_candidates(
            db, course_id, query.strip(), embedder, candidates, reranker, excluded_document_ids,
        )
    return _select_conservative_evidence(
        candidates,
        top_k=top_k,
        min_score=_default_min_score(embedder) if min_score is None else min_score,
    )


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
        Chunk.document_id.in_(
            select(Document.id).where(
                Document.course_id == course_id, Document.retrieval_enabled.is_(True),
            )
        ),
    ]
    if excluded_document_ids:
        filters.append(Chunk.document_id.not_in(excluded_document_ids))
    return bool(db.scalar(select(exists().where(*filters))))
