from __future__ import annotations

import json
from typing import Any

from sqlalchemy.engine import Dialect
from sqlalchemy.types import Text, TypeDecorator


class EmbeddingVector(TypeDecorator):
    """Postgres pgvector(1024); SQLite stores JSON for pytest."""

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1024) -> None:
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[float] | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> list[float] | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        if isinstance(value, str):
            return json.loads(value)
        return list(value)
