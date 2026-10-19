import json
import logging
import time
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import AskRequest, AskResponse, CitationOut
from app.config import get_settings
from app.db import get_db
from app.models.query_log import QueryLog, QueryOutcome
from app.security.deps import CourseAccess, require_course_member
from app.services.embedder import Embedder, get_embedder
from app.services.fusion import FusionError
from app.services.generate import (
    NO_EVIDENCE,
    NO_EVIDENCE_MESSAGE,
    generate_answer_result,
)
from app.services.keyword import KeywordLimitExceeded
from app.services.llm import LLM, get_llm
from app.services.query_expansion import (
    expand_calculation_subqueries,
    expand_subqueries,
    is_broad_procedural,
)
from app.services.question_shape import (
    INVALID_QUESTION,
    INVALID_QUESTION_MESSAGE,
    NEEDS_CONTEXT,
    NEEDS_CONTEXT_MESSAGE,
    definition_term,
    is_calculation_question,
    is_contextual_followup,
    is_meaningless_question,
)
from app.services.rerank import Reranker, get_reranker
from app.services.retrieve import (
    EMBEDDING_MISMATCH,
    EMBEDDING_MISMATCH_MESSAGE,
    KEYWORD_LIMIT,
    KEYWORD_LIMIT_MESSAGE,
    RETRIEVAL_FAILED,
    RETRIEVAL_FAILED_MESSAGE,
    RETRIEVAL_STRATEGY,
    RETRIEVAL_STRATEGY_MESSAGE,
    SEARCH_TOP_K,
    RetrievalStrategyError,
    has_incompatible_chunks,
    merge_definition_hits,
    retrieve_chunks,
    retrieve_expanded_chunks,
)
from app.services.upstream import (
    UPSTREAM_UNAVAILABLE,
    UpstreamUnavailable,
)

router = APIRouter(prefix="/courses", tags=["ask"])
logger = logging.getLogger(__name__)
_QUERY_STORE_CHARS = 2000


def _citations(course_id: UUID, hits, cited_ids, source_texts: dict[UUID, str]) -> list[CitationOut]:
    by_id = {hit.chunk_id: hit for hit in hits}
    out: list[CitationOut] = []
    for chunk_id in cited_ids:
        hit = by_id.get(chunk_id)
        if hit is None:
            continue
        out.append(
            CitationOut(
                chunk_id=str(hit.chunk_id),
                document_id=str(hit.document_id),
                page=hit.page,
                snippet=source_texts[chunk_id],
                content_url=(
                    f"/courses/{course_id}/documents/{hit.document_id}/content"
                ),
            )
        )
    return out


@router.post("/{course_id}/ask", response_model=AskResponse)
def ask_course(
    body: AskRequest,
    access: Annotated[CourseAccess, Depends(require_course_member)],
    db: Annotated[DbSession, Depends(get_db)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    llm: Annotated[LLM, Depends(get_llm)],
    reranker: Annotated[Reranker | None, Depends(get_reranker)],
    response: Response,
) -> AskResponse:
    started = time.perf_counter()
    asked_at = datetime.now(UTC)
    member_role_at_ask = access.member.role
    hits = []
    cited_ids: list = []
    error_code = None
    answer = None
    source_texts: dict[UUID, str] = {}
    llm_called = False
    upstream_failure = None
    failure_status = None
    followup = is_contextual_followup(body.query)
    previous_question = (body.previous_question or "").strip() if followup else ""
    retrieval_query = (
        f"{previous_question}\n追问：{body.query.strip()}"
        if previous_question else body.query
    )
    # Reuse the existing retrieval/generation adapters. These small rules need no new dependency.
    term = definition_term(body.query) if not followup else ""
    if is_meaningless_question(body.query):
        error_code = INVALID_QUESTION
    elif followup and not previous_question:
        error_code = NEEDS_CONTEXT
    try:
        if error_code is None:
            settings = get_settings()
            index_mismatch = has_incompatible_chunks(db, access.course.id, embedder)

            def retry_retrieval(operation):
                try:
                    return operation()
                except UpstreamUnavailable as exc:
                    if exc.error_code != UPSTREAM_UNAVAILABLE:
                        raise
                    # One extra attempt only; generation and timeouts are not retried.
                    logger.warning("ask_retrieval_upstream_retry")
                    return operation()

            def retrieve(query):
                return retry_retrieval(lambda: retrieve_chunks(
                    db, access.course.id, query, embedder,
                    strategy=settings.retrieval_strategy,
                    rrf_k=settings.rrf_k,
                    reranker=reranker,
                ))

            def supplement(hits):
                if settings.retrieval_strategy == "dense" and term:
                    hits = merge_definition_hits(db, access.course.id, term, embedder, hits)
                    # Compound "…的几何意义" rarely appears literally; also merge the head noun.
                    if term.endswith("的几何意义") and len(term) > 5:
                        head = term[: -len("的几何意义")].strip()
                        if head:
                            hits = merge_definition_hits(
                                db, access.course.id, head, embedder, hits,
                            )
                if "矩阵" in retrieval_query and "几何意义" in retrieval_query:
                    extra = []
                    for keyword in ("列视角", "行视角", "四种理解"):
                        try:
                            extra.extend(retrieve(keyword)[:2])
                        except Exception:  # noqa: BLE001 - optional recall must degrade.
                            logger.warning("ask_geometry_retrieval_fallback")
                    seen = set()
                    merged = []
                    for hit in [*extra, *hits]:
                        if hit.chunk_id not in seen:
                            seen.add(hit.chunk_id)
                            merged.append(hit)
                    hits = merged[:SEARCH_TOP_K]
                return hits

            def generate(hits):
                return generate_answer_result(
                    db, body.query, hits, llm,
                    previous_question=previous_question or None,
                    previous_answer=body.previous_answer if previous_question else None,
                )

            def try_expansion(expand=expand_subqueries):
                try:
                    subs = expand(retrieval_query, llm)
                    return retry_retrieval(lambda: retrieve_expanded_chunks(
                        db, access.course.id, retrieval_query, embedder, subs,
                    )) if subs else []
                except Exception:  # noqa: BLE001 - expansion must degrade.
                    logger.warning("ask_query_expansion_fallback")
                    return []

            hits = [] if index_mismatch else supplement(retrieve(retrieval_query))
            expansion_used = False
            # Definition retry replaces expansion for this question, bounding model calls.
            expansion_enabled = (
                settings.query_expansion_backend == "llm" and not index_mismatch and not term
            )
            calculation = not followup and is_calculation_question(body.query)
            if (
                expansion_enabled and not calculation and hits
                and is_broad_procedural(retrieval_query)
            ):
                expanded = try_expansion()
                if expanded:
                    hits = supplement(expanded)
                    expansion_used = True
            if index_mismatch:
                error_code = EMBEDDING_MISMATCH
            elif not hits:
                error_code = NO_EVIDENCE
            else:
                llm_called = True
                generated = generate(hits)
                answer, cited_ids = generated.answer, generated.cited_ids
                source_texts = generated.source_texts
                if not cited_ids:
                    answer = None
                    error_code = NO_EVIDENCE
            if not cited_ids and not index_mismatch and term and term != body.query.strip():
                hits = supplement(retrieve(term))
                if hits:
                    llm_called = True
                    generated = generate(hits)
                    answer, cited_ids = generated.answer, generated.cited_ids
                    source_texts = generated.source_texts
                error_code = None if cited_ids else NO_EVIDENCE
                if not cited_ids:
                    answer = None
            # Calculation exercises get one method/formula retry before the generic retry.
            # Both reuse the original-query cosine gate; neither changes evidence admission.
            if not cited_ids and expansion_enabled and calculation:
                expanded = try_expansion(expand_calculation_subqueries)
                if expanded:
                    hits = supplement(expanded)
                    llm_called = True
                    generated = generate(hits)
                    answer, cited_ids = generated.answer, generated.cited_ids
                    source_texts = generated.source_texts
                    error_code = None if cited_ids else NO_EVIDENCE
                    if not cited_ids:
                        answer = None
            if not cited_ids and expansion_enabled and not expansion_used:
                expanded = try_expansion()
                if expanded:
                    hits = supplement(expanded)
                    llm_called = True
                    generated = generate(hits)
                    answer, cited_ids = generated.answer, generated.cited_ids
                    source_texts = generated.source_texts
                    error_code = None if cited_ids else NO_EVIDENCE
                    if not cited_ids:
                        answer = None
    except KeywordLimitExceeded as exc:
        logger.warning("ask_keyword_limit resource=%s", exc.resource)
        error_code = KEYWORD_LIMIT
        failure_status = 503
    except RetrievalStrategyError:
        logger.warning("ask_retrieval_strategy_rejected")
        error_code = RETRIEVAL_STRATEGY
        failure_status = 503
    except FusionError as exc:
        logger.warning("ask_fusion_rejected kind=%s", exc.kind)
        error_code = RETRIEVAL_FAILED
        failure_status = 503
    except UpstreamUnavailable as exc:
        upstream_failure = exc
        error_code = exc.error_code
    duration_ms = int((time.perf_counter() - started) * 1000)
    citations = _citations(access.course.id, hits, cited_ids, source_texts)
    outcome = (
        QueryOutcome.no_evidence if error_code in {NO_EVIDENCE, NEEDS_CONTEXT, INVALID_QUESTION}
        else QueryOutcome.failure if error_code is not None
        else QueryOutcome.cited_answer
    )
    db.add(
        QueryLog(
            course_id=access.course.id,
            user_id=access.user.id,
            query=body.query.strip()[:_QUERY_STORE_CHARS],
            hit=bool(hits),
            outcome=outcome.value,
            member_role_at_ask=member_role_at_ask,
            error_code=error_code,
            chunk_ids=json.dumps([str(hit.chunk_id) for hit in hits]),
            duration_ms=duration_ms,
            created_at=asked_at,
        )
    )
    db.commit()
    logger.info(
        "ask course_id=%s hit=%s llm_called=%s duration_ms=%s chunk_count=%s",
        access.course.id,
        bool(hits),
        llm_called,
        duration_ms,
        len(hits),
    )
    if upstream_failure is not None:
        logger.warning("ask_upstream_unavailable error_code=%s", error_code)
        response.status_code = upstream_failure.status_code
    elif failure_status is not None:
        response.status_code = failure_status
    failure_messages = {
        NEEDS_CONTEXT: NEEDS_CONTEXT_MESSAGE,
        INVALID_QUESTION: INVALID_QUESTION_MESSAGE,
        EMBEDDING_MISMATCH: EMBEDDING_MISMATCH_MESSAGE,
        NO_EVIDENCE: NO_EVIDENCE_MESSAGE,
        KEYWORD_LIMIT: KEYWORD_LIMIT_MESSAGE,
        RETRIEVAL_STRATEGY: RETRIEVAL_STRATEGY_MESSAGE,
        RETRIEVAL_FAILED: RETRIEVAL_FAILED_MESSAGE,
    }
    return AskResponse(
        error_code=error_code,
        message=(
            upstream_failure.message
            if upstream_failure is not None
            else failure_messages.get(error_code)
        ),
        answer=answer,
        citations=citations,
    )
