from __future__ import annotations

import logging
import re
from contextvars import ContextVar, Token
from uuid import uuid4

_REQUEST_ID = ContextVar("request_id", default="-")
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def normalize_request_id(value: str | None) -> str:
    if value is not None and _VALID_REQUEST_ID.fullmatch(value):
        return value
    return uuid4().hex


def set_request_id(value: str) -> Token[str]:
    return _REQUEST_ID.set(value)


def reset_request_id(token: Token[str]) -> None:
    _REQUEST_ID.reset(token)


def request_id() -> str:
    return _REQUEST_ID.get()


def configure_log_records() -> None:
    """Expose the request id on application LogRecords without logging request data."""
    factory = logging.getLogRecordFactory()
    if getattr(factory, "_adds_request_id", False):
        return

    def record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = factory(*args, **kwargs)
        record.request_id = request_id()
        return record

    record_factory._adds_request_id = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(record_factory)
