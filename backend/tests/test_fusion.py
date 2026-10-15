"""RRF contracts. Scores are synthetic; nothing here is a relevance claim."""

import math
from uuid import UUID

import pytest
from app.services.fusion import (
    RRF_K,
    DenseCandidate,
    FusedHit,
    FusionError,
    KeywordCandidate,
    fuse_rrf,
)

DOC = UUID("00000000-0000-0000-0000-000000000010")


def _dense(chunk: int, score: float, *, document: UUID = DOC, page: int | None = 3, snippet: str = "dense"):
    return DenseCandidate(UUID(int=chunk), document, page, snippet, score)


def _keyword(
    chunk: int, score: float, *, document: UUID = DOC, page: int | None = 3, snippet: str = "keyword"
):
    return KeywordCandidate(UUID(int=chunk), document, page, snippet, score)


def test_rrf_constant_is_the_rank_offset_not_a_similarity_threshold() -> None:
    assert RRF_K == 60


def test_empty_branches_return_empty() -> None:
    assert fuse_rrf([], [], rrf_k=60, limit=8) == []


def test_single_branch_keeps_scores_without_claiming_evidence_admission() -> None:
    lexical = fuse_rrf([], [_keyword(1, 0.0), _keyword(2, -0.2)], rrf_k=60, limit=8)
    assert [hit.chunk_id for hit in lexical] == [UUID(int=1), UUID(int=2)]
    assert lexical[0].bm25_score == 0.0
    assert lexical[0].cosine_score is None
    assert lexical[0].rrf_score == pytest.approx(1 / 61)

    dense = fuse_rrf([_dense(2, 0.2), _dense(1, 0.9)], [], rrf_k=60, limit=8)
    assert [hit.chunk_id for hit in dense] == [UUID(int=1), UUID(int=2)]
    assert dense[0].cosine_score == pytest.approx(0.9)
    assert dense[0].bm25_score is None
    assert dense[0].rrf_score != dense[0].cosine_score


def test_duplicate_chunk_ids_sum_ranks_and_keep_dense_snippet() -> None:
    fused = fuse_rrf(
        [_dense(7, 0.4, snippet="cosine-snippet")],
        [_keyword(7, 3.5, snippet="bm25-snippet")],
        rrf_k=60,
        limit=8,
    )
    assert len(fused) == 1
    hit = fused[0]
    assert hit == FusedHit(UUID(int=7), DOC, 3, "cosine-snippet", 0.4, 3.5, 1, 1, hit.rrf_score)
    assert hit.rrf_score == pytest.approx(2 / 61)
    assert hit.snippet == "cosine-snippet"


def test_competition_ties_share_a_rank_and_uuid_orders_equal_rrf() -> None:
    left, right = UUID(int=1), UUID(int=2)
    fused = fuse_rrf(
        [
            DenseCandidate(right, DOC, None, "right", 0.2),
            DenseCandidate(left, DOC, None, "left", 0.2),
            _dense(3, 0.9),
        ],
        [],
        rrf_k=60,
        limit=8,
    )
    tied = [hit for hit in fused if hit.cosine_score == pytest.approx(0.2)]
    assert [hit.dense_rank for hit in tied] == [2, 2]
    assert [hit.chunk_id for hit in tied] == [left, right]
    assert fused[-1].dense_rank == 2
    assert fused[0].dense_rank == 1


def test_keyword_rank_can_place_a_lower_cosine_first_without_replacing_it() -> None:
    fused = fuse_rrf(
        [_dense(1, 0.9), _dense(2, 0.5)],
        [_keyword(2, 1.25)],
        rrf_k=60,
        limit=8,
    )
    assert [hit.chunk_id for hit in fused] == [UUID(int=2), UUID(int=1)]
    assert fused[0].cosine_score == pytest.approx(0.5)
    assert fused[0].bm25_score == pytest.approx(1.25)
    assert fused[0].rrf_score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[1].bm25_score is None
    assert fused[0].rrf_score != fused[0].cosine_score


def test_candidate_limit_is_applied_after_stable_ordering() -> None:
    fused = fuse_rrf([_dense(1, 0.2), _dense(2, 0.9), _dense(3, 0.4)], [], rrf_k=60, limit=1)
    assert [hit.chunk_id for hit in fused] == [UUID(int=2)]
    assert fuse_rrf([_dense(1, 0.9)], [], rrf_k=60, limit=0) == []


@pytest.mark.parametrize(
    ("kwargs", "kind"),
    [
        ({"rrf_k": True, "limit": 1}, "rank_constant"),
        ({"rrf_k": 0, "limit": 1}, "rank_constant"),
        ({"rrf_k": 60, "limit": -1}, "limit"),
        ({"rrf_k": 60, "limit": True}, "limit"),
    ],
)
def test_fusion_rejects_invalid_controls_without_a_partial_result(kwargs, kind) -> None:
    with pytest.raises(FusionError) as exc:
        fuse_rrf([_dense(1, 0.5)], [], **kwargs)
    assert exc.value.kind == kind
    assert "0.5" not in str(exc.value)


def test_duplicate_within_a_branch_is_rejected() -> None:
    item = _dense(1, 0.5, snippet="private-snippet")
    with pytest.raises(FusionError) as exc:
        fuse_rrf([item, item], [], rrf_k=60, limit=2)
    assert exc.value.kind == "duplicate"
    assert "private-snippet" not in str(exc.value)


def test_conflicting_chunk_identity_is_rejected() -> None:
    with pytest.raises(FusionError) as exc:
        fuse_rrf(
            [_dense(1, 0.5, document=DOC, page=1)],
            [_keyword(1, 1.0, document=UUID(int=99), page=1)],
            rrf_k=60,
            limit=2,
        )
    assert exc.value.kind == "identity"


@pytest.mark.parametrize("score", [math.nan, math.inf, True, "0.2"])
def test_non_finite_branch_scores_are_rejected(score) -> None:
    with pytest.raises(FusionError) as exc:
        fuse_rrf([_dense(1, score)], [], rrf_k=60, limit=1)
    assert exc.value.kind == "score"
