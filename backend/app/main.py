import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from app.api.admin_courses import router as admin_courses_router
from app.api.ask import router as ask_router
from app.api.auth import router as auth_router
from app.api.courses import router as courses_router
from app.api.documents import router as documents_router
from app.api.insights import router as insights_router
from app.api.search import router as search_router
from app.api.users import router as admin_users_router
from app.db import get_db
from app.observability import (
    configure_log_records,
    normalize_request_id,
    reset_request_id,
    set_request_id,
)

app = FastAPI()
configure_log_records()
logger = logging.getLogger(__name__)


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
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(insights_router)


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
