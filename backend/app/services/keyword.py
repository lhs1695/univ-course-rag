"""Bounded lexical candidates; independent of the default dense/ask path.

Uses jieba 0.42.1 (MIT) and rank-bm25 0.2.2 (Apache-2.0) through their
public APIs. No upstream algorithm source is copied. See docs/engineering.md.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Collection
from dataclasses import dataclass, fields
from functools import lru_cache
from uuid import UUID

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.models.document import Chunk, Document
from app.services.retrieve import SNIPPET_CHARS

MAX_KEYWORD_TOP_K = 100
MAX_EXCLUDED_DOCUMENTS = 1000
_TEXT_RUN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\+\+|#)?|[\u3400-\u9fff]+")
_CEILINGS = {
    "max_chunks": 2000,
    "max_chunk_chars": 8000,
    "max_corpus_chars": 2_000_000,
    "max_query_chars": 2000,
    "max_chunk_tokens": 2048,
    "max_corpus_tokens": 200_000,
    "max_query_tokens": 256,
}


class KeywordLimitExceeded(ValueError):
    """No truncated corpus is silently presented as a full-course search."""

    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(f"Keyword resource limit exceeded: {resource}")


@dataclass(frozen=True)
class KeywordLimits:
    max_chunks: int = 2000
    max_chunk_chars: int = 8000
    max_corpus_chars: int = 2_000_000
    max_query_chars: int = 2000
    max_chunk_tokens: int = 2048
    max_corpus_tokens: int = 200_000
    max_query_tokens: int = 256

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or not 1 <= value <= _CEILINGS[field.name]:
                raise ValueError(f"Invalid keyword limit: {field.name}")


@dataclass(frozen=True)
class KeywordHit:
    chunk_id: UUID
    document_id: UUID
    page: int | None
    snippet: str
    bm25_score: float


DEFAULT_KEYWORD_LIMITS = KeywordLimits()


@lru_cache(maxsize=1)
def _segmenter() -> jieba.Tokenizer:
    # Only the packaged dictionary is reused; no course text/tokens/results cached.
    return jieba.Tokenizer()


def preprocess_text(
    text: str, *, max_chars: int = 8000, max_tokens: int = 2048
) -> list[str]:
    """Same NFKC/casefold + Chinese search segmentation for query and corpus.

    ASCII identifiers, numbers, hyphenated terms, C++ and C# remain whole.
    Punctuation/whitespace are separators; no learned model or tokenizer Pool.
    """
    if type(max_chars) is not int or not 1 <= max_chars <= _CEILINGS["max_chunk_chars"]:
        raise ValueError("Invalid preprocessing character limit")
    if type(max_tokens) is not int or not 1 <= max_tokens <= _CEILINGS["max_chunk_tokens"]:
        raise ValueError("Invalid preprocessing token limit")
    if len(text) > max_chars:
        raise KeywordLimitExceeded("text_chars")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    if len(normalized) > max_chars:
        raise KeywordLimitExceeded("normalized_chars")
    tokens: list[str] = []
    for match in _TEXT_RUN.finditer(normalized):
        run = match.group()
        pieces = [run] if run.isascii() else _segmenter().cut_for_search(run, HMM=False)
        for piece in pieces:
            if len(tokens) >= max_tokens:
                raise KeywordLimitExceeded("text_tokens")
            tokens.append(piece)
    return tokens


def retrieve_keyword_candidates(
    db: DbSession,
    course_id: UUID,
    query: str,
    *,
    index_identity: str,
    top_k: int = 8,
    excluded_document_ids: Collection[UUID] = (),
    limits: KeywordLimits = DEFAULT_KEYWORD_LIMITS,
) -> list[KeywordHit]:
    """Callers own authorization; SQL scopes the snapshot before any text is read.

    Resource overflow is explicit, never a partial-corpus ranking. BM25 scores
    may be nonpositive: lexical overlap, not a cosine threshold, admits hits.
    """
    if not isinstance(index_identity, str) or not index_identity.strip() or len(index_identity) > 128:
        raise ValueError("An explicit compatible index identity is required")
    if type(top_k) is not int or not 0 <= top_k <= MAX_KEYWORD_TOP_K:
        raise ValueError("Invalid keyword candidate limit")
    if len(excluded_document_ids) > MAX_EXCLUDED_DOCUMENTS:
        raise KeywordLimitExceeded("excluded_documents")
    if top_k == 0:
        return []
    query_tokens = list(dict.fromkeys(preprocess_text(
        query, max_chars=limits.max_query_chars, max_tokens=limits.max_query_tokens
    )))
    if not query_tokens:
        return []

    filters = [
        Chunk.course_id == course_id,
        Chunk.embedding_model == index_identity,
        Chunk.document_id.in_(
            select(Document.id).where(
                Document.course_id == course_id, Document.retrieval_enabled.is_(True),
            )
        ),
    ]
    if excluded_document_ids:
        filters.append(Chunk.document_id.not_in(excluded_document_ids))
    # Fetch only metadata and a bounded prefix (+1 sentinel), never full embeddings
    # or arbitrarily large text columns. PostgreSQL and SQLite both support substr.
    rows = db.execute(
        select(
            Chunk.id, Chunk.document_id, Chunk.page,
            func.substr(Chunk.text, 1, limits.max_chunk_chars + 1).label("text"),
        )
        .where(*filters)
        .order_by(Chunk.id)
        .limit(limits.max_chunks + 1)
    ).all()
    if len(rows) > limits.max_chunks:
        raise KeywordLimitExceeded("chunks")

    corpus: list[list[str]] = []
    usable = []
    total_chars = total_tokens = 0
    for row in rows:
        if len(row.text) > limits.max_chunk_chars:
            raise KeywordLimitExceeded("chunk_chars")
        total_chars += len(row.text)
        if total_chars > limits.max_corpus_chars:
            raise KeywordLimitExceeded("corpus_chars")
        tokens = preprocess_text(
            row.text, max_chars=limits.max_chunk_chars, max_tokens=limits.max_chunk_tokens
        )
        total_tokens += len(tokens)
        if total_tokens > limits.max_corpus_tokens:
            raise KeywordLimitExceeded("corpus_tokens")
        if tokens:
            corpus.append(tokens)
            usable.append(row)
    if not corpus:
        return []
    query_set = set(query_tokens)
    matched = [index for index, tokens in enumerate(corpus) if query_set.intersection(tokens)]
    if not matched:
        return []
    # Pre-tokenized input avoids rank_bm25's multiprocessing tokenizer callback.
    scores = BM25Okapi(corpus, k1=1.5, b=0.75, epsilon=0.25).get_scores(query_tokens)
    ranked = sorted(matched, key=lambda index: (-float(scores[index]), usable[index].id))
    hits = []
    for index in ranked[:top_k]:
        score = float(scores[index])
        if not math.isfinite(score):
            raise ValueError("Invalid BM25 score")
        row = usable[index]
        hits.append(KeywordHit(
            chunk_id=row.id, document_id=row.document_id, page=row.page,
            snippet=row.text.strip()[:SNIPPET_CHARS], bm25_score=score,
        ))
    return hits
