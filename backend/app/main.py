import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from app.api.admin_courses import router as admin_courses_router
from app.api.agent_task_retention import router as agent_task_retention_router
from app.api.agent_tasks import router as agent_tasks_router
from app.api.ask import router as ask_router
from app.api.auth import router as auth_router
from app.api.course_business import router as course_business_router
from app.api.courses import router as courses_router
from app.api.documents import router as documents_router
from app.api.folders import router as folders_router
from app.api.insight_reviews import router as insight_reviews_router
from app.api.insights import router as insights_router
from app.api.query_log_retention import router as query_log_retention_router
from app.api.search import router as search_router
from app.api.users import router as admin_users_router
from app.config import ConfigurationUnavailable, Settings, get_settings, provider_status
from app.db import get_db
from app.observability import (
    configure_log_records,
    normalize_request_id,
    reset_request_id,
    set_request_id,
)
from app.services.fusion import FusionError
from app.services.keyword import KeywordLimitExceeded
from app.services.retrieve import (
    KEYWORD_LIMIT,
    KEYWORD_LIMIT_MESSAGE,
    RETRIEVAL_FAILED,
    RETRIEVAL_FAILED_MESSAGE,
    RETRIEVAL_STRATEGY,
    RETRIEVAL_STRATEGY_MESSAGE,
    RetrievalStrategyError,
)
from app.services.upstream import UpstreamUnavailable

app = FastAPI()
configure_log_records()
logger = logging.getLogger(__name__)


def _service_error(code: str, message: str, status_code: int) -> JSONResponse:
    logger.warning("service_unavailable error_code=%s", code)
    return JSONResponse(
        status_code=status_code,
        content={"error_code": code, "message": message, "answer": None, "citations": []},
    )


@app.exception_handler(ConfigurationUnavailable)
async def configuration_unavailable(request: Request, exc: ConfigurationUnavailable):
    return _service_error("MODEL_NOT_CONFIGURED", "AI 服务配置不可用，请联系管理员核对配置。", 503)


@app.exception_handler(UpstreamUnavailable)
async def upstream_unavailable(request: Request, exc: UpstreamUnavailable):
    return _service_error(exc.error_code, exc.message, exc.status_code)


@app.exception_handler(KeywordLimitExceeded)
async def keyword_limit_exceeded(request: Request, exc: KeywordLimitExceeded):
    logger.warning("keyword_limit resource=%s", exc.resource)
    return _service_error(KEYWORD_LIMIT, KEYWORD_LIMIT_MESSAGE, 503)


@app.exception_handler(RetrievalStrategyError)
async def retrieval_strategy_rejected(request: Request, exc: RetrievalStrategyError):
    logger.warning("retrieval_strategy_rejected")
    return _service_error(RETRIEVAL_STRATEGY, RETRIEVAL_STRATEGY_MESSAGE, 503)


@app.exception_handler(FusionError)
async def fusion_rejected(request: Request, exc: FusionError):
    logger.warning("fusion_rejected kind=%s", exc.kind)
    return _service_error(RETRIEVAL_FAILED, RETRIEVAL_FAILED_MESSAGE, 503)


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request: Request, exc: SQLAlchemyError):
    return _service_error("DATABASE_UNAVAILABLE", "数据库暂时不可用，请稍后重试。", 503)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    correlation_id = normalize_request_id(request.headers.get("X-Request-ID"))
    token = set_request_id(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        logger.info(
            "request_completed method=%s status_code=%s request_id=%s",
            request.method,
            response.status_code,
            correlation_id,
        )
        return response
    finally:
        reset_request_id(token)
app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(admin_courses_router)
app.include_router(courses_router)
app.include_router(course_business_router)
app.include_router(documents_router)
app.include_router(folders_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(insights_router)
app.include_router(insight_reviews_router)
app.include_router(agent_tasks_router)
app.include_router(agent_task_retention_router)
app.include_router(query_log_retention_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("database_not_ready")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ok"}


@app.get("/runtime")
def runtime_status(
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Local checks only; no provider requests, credentials, URLs, or course data."""
    database = "available"
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database = "unavailable"
    return {
        "process": "ok",
        "database": database,
        "embedding": provider_status(settings, "embedding"),
        "generation": provider_status(settings, "llm"),
        "reranking": provider_status(settings, "reranking"),
        "migration": "not_checked",
        "index": "not_checked",
    }
