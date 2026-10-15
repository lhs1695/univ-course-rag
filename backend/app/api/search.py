from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import SearchHitOut, SearchRequest, SearchResponse
from app.config import get_settings
from app.db import get_db
from app.security.deps import CourseAccess, require_course_member
from app.services.embedder import Embedder, get_embedder
from app.services.rerank import Reranker, get_reranker
from app.services.retrieve import retrieve_chunks

router = APIRouter(prefix="/courses", tags=["search"])


@router.post("/{course_id}/search", response_model=SearchResponse)
def search_course(
    body: SearchRequest,
    access: Annotated[CourseAccess, Depends(require_course_member)],
    db: Annotated[DbSession, Depends(get_db)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    reranker: Annotated[Reranker | None, Depends(get_reranker)],
) -> SearchResponse:
    settings = get_settings()
    hits = retrieve_chunks(
        db,
        access.course.id,
        body.query,
        embedder,
        strategy=settings.retrieval_strategy,
        rrf_k=settings.rrf_k,
        reranker=reranker,
    )
    return SearchResponse(
        hits=[
            SearchHitOut(
                chunk_id=str(hit.chunk_id),
                document_id=str(hit.document_id),
                page=hit.page,
                snippet=hit.snippet,
                score=hit.score,
            )
            for hit in hits
        ]
    )
