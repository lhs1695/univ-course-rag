"""Reciprocal rank fusion for one dense branch and one keyword branch.

The score is the published RRF sum, 1/(k+rank), with the usual constant k=60
(Cormack, Clarke, Buettcher, SIGIR 2009). This file is a local adapter: Haystack's
DocumentJoiner is only a behavior reference, and no upstream source is copied.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

RRF_K = 60
MAX_RRF_K = 10_000
MAX_FUSED_CANDIDATES = 200


class FusionError(ValueError):
    """Branches cannot be merged without hiding a broken candidate."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__("Retrieval fusion rejected")


@dataclass(frozen=True)
class DenseCandidate:
    chunk_id: UUID
    document_id: UUID
    page: int | None
    snippet: str
    cosine_score: float


@dataclass(frozen=True)
class KeywordCandidate:
    chunk_id: UUID
    document_id: UUID
    page: int | None
    snippet: str
    bm25_score: float


@dataclass(frozen=True)
class FusedHit:
    chunk_id: UUID
    document_id: UUID
    page: int | None
    snippet: str
    cosine_score: float | None
    bm25_score: float | None
    dense_rank: int | None
    keyword_rank: int | None
    rrf_score: float


def _finite_score(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FusionError("score")
    score = float(value)
    if not math.isfinite(score):
        raise FusionError("score")
    return score


def _competition_ranks(scores: list[tuple[float, UUID]]) -> dict[UUID, int]:
    """1-based competition ranks. Equal scores share a rank; later ranks skip."""
    ordered = sorted(scores, key=lambda item: (-item[0], item[1]))
    ranks: dict[UUID, int] = {}
    index = 0
    while index < len(ordered):
        score = ordered[index][0]
        end = index + 1
        while end < len(ordered) and ordered[end][0] == score:
            end += 1
        rank = index + 1
        for cursor in range(index, end):
            ranks[ordered[cursor][1]] = rank
        index = end
    return ranks


def _index_branch(
    items: Sequence[DenseCandidate] | Sequence[KeywordCandidate], score_name: str
) -> tuple[dict[UUID, DenseCandidate | KeywordCandidate], dict[UUID, float], dict[UUID, int]]:
    prepared: dict[UUID, DenseCandidate | KeywordCandidate] = {}
    scores: dict[UUID, float] = {}
    for item in items:
        score = _finite_score(getattr(item, score_name))
        if item.chunk_id in prepared:
            raise FusionError("duplicate")
        prepared[item.chunk_id] = item
        scores[item.chunk_id] = score
    ranks = _competition_ranks([(score, chunk_id) for chunk_id, score in scores.items()])
    return prepared, scores, ranks


def fuse_rrf(
    dense: Sequence[DenseCandidate],
    keyword: Sequence[KeywordCandidate],
    *,
    rrf_k: int = RRF_K,
    limit: int,
) -> list[FusedHit]:
    """Rank the candidate union; neither branch nor RRF admits evidence."""
    if type(rrf_k) is not int or not 1 <= rrf_k <= MAX_RRF_K:
        raise FusionError("rank_constant")
    if type(limit) is not int or not 0 <= limit <= MAX_FUSED_CANDIDATES:
        raise FusionError("limit")
    dense_by_id, dense_scores, dense_ranks = _index_branch(dense, "cosine_score")
    keyword_by_id, keyword_scores, keyword_ranks = _index_branch(keyword, "bm25_score")
    fused: list[FusedHit] = []
    for chunk_id in dense_by_id.keys() | keyword_by_id.keys():
        dense_hit = dense_by_id.get(chunk_id)
        keyword_hit = keyword_by_id.get(chunk_id)
        if (
            dense_hit is not None
            and keyword_hit is not None
            and (
                dense_hit.document_id != keyword_hit.document_id
                or dense_hit.page != keyword_hit.page
            )
        ):
            raise FusionError("identity")
        source = dense_hit if dense_hit is not None else keyword_hit
        assert source is not None
        dense_rank = dense_ranks.get(chunk_id)
        keyword_rank = keyword_ranks.get(chunk_id)
        rrf_score = 0.0
        if dense_rank is not None:
            rrf_score += 1.0 / (rrf_k + dense_rank)
        if keyword_rank is not None:
            rrf_score += 1.0 / (rrf_k + keyword_rank)
        fused.append(
            FusedHit(
                chunk_id=chunk_id,
                document_id=source.document_id,
                page=source.page,
                snippet=source.snippet,
                cosine_score=None if dense_hit is None else dense_scores[chunk_id],
                bm25_score=None if keyword_hit is None else keyword_scores[chunk_id],
                dense_rank=dense_rank,
                keyword_rank=keyword_rank,
                rrf_score=rrf_score,
            )
        )
    fused.sort(key=lambda hit: (-hit.rrf_score, hit.chunk_id))
    return fused[:limit]
