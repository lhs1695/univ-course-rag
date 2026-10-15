"""Bounded, on-demand candidate question groups; no learned semantics in Fake code."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Real
from typing import Annotated, cast
from uuid import UUID

import numpy as np
from fastapi import Depends
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import ConfigurationUnavailable, Settings, get_settings
from app.models.query_log import QueryLog, QueryOutcome
from app.services.embedder import Embedder, SiliconFlowEmbedder, build_embedder
from app.services.upstream import UpstreamUnavailable

MAX_QUESTIONS = 200
MAX_QUERY_CHARS = 2000
MAX_TOTAL_CHARS = 200_000
GROUPING_CONTRACT = "p5-complete-cosine-v1"


class QuestionGroupingError(UpstreamUnavailable):
    error_code = "QUESTION_GROUPING_FAILED"
    message = "问题分组未能完成，请稍后重试。"


class QuestionGroupingLimit(QuestionGroupingError):
    error_code = "QUESTION_GROUPING_LIMIT"
    message = "本次问题数量或文本超出分组上限，请缩小时间范围。"
    status_code = 413


class QuestionGroupingDisabled(QuestionGroupingError):
    error_code = "QUESTION_GROUPING_DISABLED"
    message = "问题语义分组尚未启用，基础统计仍可使用。"


def build_question_embedder(settings: Settings) -> SiliconFlowEmbedder | None:
    if settings.question_grouping_backend == "disabled":
        return None
    if settings.question_grouping_backend != "embedding" or settings.embedder_backend != "siliconflow":
        raise ConfigurationUnavailable()
    # Reuse the existing configured provider. Never promote token-hash Fake vectors
    # to semantic results, and never issue a request from GET /insights.
    return cast(SiliconFlowEmbedder, build_embedder(settings))


def get_question_embedder(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[Embedder | None]:
    provider = build_question_embedder(settings)
    try:
        yield provider
    finally:
        if provider is not None:
            provider.close()


@dataclass
class QuestionSample:
    query: str
    outcomes: dict[str, int]
    last_asked_at: datetime

    @property
    def count(self) -> int:
        return sum(self.outcomes.values())


def _load_samples(db: Session, course_id: UUID, start: datetime, end: datetime):
    valid_outcomes = [QueryOutcome.cited_answer.value, QueryOutcome.no_evidence.value]
    question = case((QueryLog.outcome.in_(valid_outcomes), QueryLog.query), else_=None)
    row_limit = 2 * MAX_QUESTIONS + 5
    rows = db.execute(
        select(question, QueryLog.outcome, func.count(), func.max(QueryLog.created_at))
        .where(
            QueryLog.course_id == course_id,
            QueryLog.member_role_at_ask == "student",
            QueryLog.created_at >= start,
            QueryLog.created_at < end,
        )
        .group_by(question, QueryLog.outcome)
        .limit(row_limit)
    ).all()
    if len(rows) == row_limit:
        raise QuestionGroupingLimit()
    samples: dict[str, QuestionSample] = {}
    excluded = 0
    for query, outcome, count, last_at in rows:
        query = " ".join((query or "").split())
        if not query:
            excluded += count
            continue
        if len(query) > MAX_QUERY_CHARS:
            raise QuestionGroupingLimit()
        last_at = last_at.replace(tzinfo=UTC) if last_at.tzinfo is None else last_at.astimezone(UTC)
        sample = samples.setdefault(query, QuestionSample(query, {}, last_at))
        sample.outcomes[outcome] = sample.outcomes.get(outcome, 0) + count
        sample.last_asked_at = max(sample.last_asked_at, last_at)
    if len(samples) > MAX_QUESTIONS or sum(map(len, samples)) > MAX_TOTAL_CHARS:
        raise QuestionGroupingLimit()
    return [samples[key] for key in sorted(samples)], excluded


def _distances(texts: list[str], embedder: Embedder) -> np.ndarray:
    vectors = embedder.embed(texts)
    try:
        if len(vectors) != len(texts) or any(
            not row or len(row) > 4096 or any(not isinstance(x, Real) or isinstance(x, bool) for x in row)
            for row in vectors
        ):
            raise ValueError()
        matrix = np.asarray(vectors, dtype=np.float64)
        if matrix.ndim != 2 or not np.isfinite(matrix).all():
            raise ValueError()
        scale = np.max(np.abs(matrix), axis=1)
        if (scale == 0).any():
            raise ValueError()
        matrix = matrix / scale[:, None]
        matrix /= np.linalg.norm(matrix, axis=1)[:, None]
        return np.clip(pdist(matrix, metric="cosine"), 0.0, 2.0)
    except (ValueError, TypeError, OverflowError):
        raise QuestionGroupingError() from None


def group_course_questions(
    db: Session, course_id: UUID, *, window_start: datetime, window_end: datetime,
    embedder: Embedder, min_similarity: float,
) -> dict:
    if not np.isfinite(min_similarity) or not 0 < min_similarity <= 1:
        raise QuestionGroupingError()
    samples, excluded = _load_samples(db, course_id, window_start, window_end)
    size = len(samples)
    labels = np.ones(size, dtype=int)
    distances = np.zeros((size, size))
    if size > 1:
        condensed = _distances([sample.query for sample in samples], embedder)
        labels = fcluster(linkage(condensed, method="complete"), 1 - min_similarity, criterion="distance")
        distances = squareform(condensed)
    groups = []
    for label in sorted(set(labels)):
        indices = np.flatnonzero(labels == label)
        within = distances[np.ix_(indices, indices)]
        # Unweighted medoid among actual questions; repeat counts do not pick the exemplar.
        representative = int(indices[np.argmin(within.sum(axis=1))])
        members = [
            {
                "query": samples[i].query, "count": samples[i].count,
                "cited_answer": samples[i].outcomes.get("cited_answer", 0),
                "no_evidence": samples[i].outcomes.get("no_evidence", 0),
                "similarity_to_representative": float(1 - distances[i, representative]),
                "last_asked_at": samples[i].last_asked_at,
            }
            for i in indices
        ]
        groups.append({
            "kind": "candidate" if len(indices) > 1 else "singleton",
            "representative": samples[representative].query,
            "count": sum(member["count"] for member in members),
            "distinct_questions": len(indices),
            "min_pair_similarity": float(1 - within.max()) if len(indices) > 1 else None,
            "members": members,
        })
    groups.sort(key=lambda group: (-group["count"], group["representative"]))
    singletons = [group for group in groups if group["kind"] == "singleton"]
    return {
        "window_start": window_start, "window_end": window_end,
        "grouping_contract": GROUPING_CONTRACT, "min_similarity": min_similarity,
        "threshold_calibrated": False, "embedding_called": size > 1,
        "embedding_model": embedder.model_name, "embedding_identity": embedder.index_identity,
        "eligible_attempts": sum(sample.count for sample in samples),
        "excluded_attempts": excluded, "distinct_questions": size,
        "grouped_questions": size - len(singletons), "singleton_questions": len(singletons),
        "singleton_attempts": sum(group["count"] for group in singletons), "groups": groups,
    }
