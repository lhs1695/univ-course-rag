from __future__ import annotations

import re

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

_HEADING = re.compile(r"(?m)^(#{1,6}[ \t].+)$")


def chunk_pages(pages: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
    """Heading-first for markdown-like text; page-first for PDF; then length+overlap."""
    out: list[tuple[int | None, str]] = []
    for page, text in pages:
        for piece in _split_by_headings(text):
            out.extend(_split_length(piece, page))
    return [(page, chunk) for page, chunk in out if chunk.strip()]


def _split_by_headings(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    matches = list(_HEADING.finditer(stripped))
    if len(matches) < 2:
        return [stripped]
    parts: list[str] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(stripped)
        if i == 0 and match.start() > 0:
            lead = stripped[: match.start()].strip()
            if lead:
                parts.append(lead)
        block = stripped[match.start() : end].strip()
        if block:
            parts.append(block)
    return parts or [stripped]


def _split_length(text: str, page: int | None) -> list[tuple[int | None, str]]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [(page, text)]
    chunks: list[tuple[int | None, str]] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append((page, text[start:end].strip()))
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return [(page, body) for page, body in chunks if body]
