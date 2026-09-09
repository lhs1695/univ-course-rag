import json
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import AskRequest, AskResponse, CitationOut
from app.db import get_db
from app.models.query_log import QueryLog
from app.security.deps import CourseAccess, require_course_member
from app.services.embedder import Embedder, get_embedder
from app.services.generate import NO_EVIDENCE, NO_EVIDENCE_MESSAGE, generate_answer
from app.services.llm import LLM, get_llm
from app.services.retrieve import (
    EMBEDDING_MISMATCH,
    EMBEDDING_MISMATCH_MESSAGE,
    has_incompatible_chunks,
    retrieve_chunks,
)

router = APIRouter(prefix="/courses", tags=["ask"])
logger = logging.getLogger(__name__)
_QUERY_STORE_CHARS = 2000


def _citations(hits, cited_ids) -> list[CitationOut]:
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
                snippet=hit.snippet,
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
) -> AskResponse:
    started = time.perf_counter()
    index_mismatch = has_incompatible_chunks(db, access.course.id, embedder)
    hits = [] if index_mismatch else retrieve_chunks(db, access.course.id, body.query, embedder)
    cited_ids: list = []
    error_code = None
    answer = None
    if index_mismatch:
        error_code = EMBEDDING_MISMATCH
        llm_called = False
    elif not hits:
        error_code = NO_EVIDENCE
        llm_called = False
    else:
        llm_called = True
        answer, cited_ids = generate_answer(db, body.query, hits, llm)
        if not cited_ids:
            answer = None
            error_code = NO_EVIDENCE
    duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        QueryLog(
            course_id=access.course.id,
            user_id=access.user.id,
            query=body.query.strip()[:_QUERY_STORE_CHARS],
            hit=bool(hits),
            error_code=error_code,
            chunk_ids=json.dumps([str(hit.chunk_id) for hit in hits]),
            duration_ms=duration_ms,
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
    return AskResponse(
        error_code=error_code,
        message=(
            EMBEDDING_MISMATCH_MESSAGE
            if error_code == EMBEDDING_MISMATCH
            else NO_EVIDENCE_MESSAGE if error_code == NO_EVIDENCE else None
        ),
        answer=answer,
        citations=_citations(hits, cited_ids),
    )
