from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from semantic_text_splitter import MarkdownSplitter, TextSplitter

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
CHUNKING_VERSION = "sts-0.33.0-char800-overlap120-r5-v1"


@dataclass(frozen=True)
class ChunkPiece:
    page: int | None
    text: str
    source_metadata: dict[str, str | int]


def chunk_pages(
    pages: list[tuple[int | None, str]], *, filename: str,
) -> list[ChunkPiece]:
    """Adapt semantic-text-splitter 0.33.0 (MIT), without copying its algorithms.

    Offsets are Python character positions into each sanitized extracted unit,
    not bytes/positions in the original binary document. Never merge pages or
    slides; nonpaginated documents have no invented physical page number.
    """
    suffix = Path(filename).suffix.lower()
    source_kind = {
        ".pdf": "pdf_page", ".pptx": "pptx_slide", ".docx": "docx_text",
        ".md": "markdown", ".markdown": "markdown", ".txt": "plain_text",
    }[suffix]
    markdown = source_kind == "markdown"
    splitter = (MarkdownSplitter if markdown else TextSplitter)(CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    out = []
    for unit_index, (page, text) in enumerate(pages, start=1):
        for start, body in splitter.chunk_indices(text):
            end = start + len(body)
            if not body.strip():
                continue
            if not (0 <= start < end <= len(text) and len(body) <= CHUNK_SIZE and text[start:end] == body):
                raise ValueError("splitter returned an invalid source span")
            physical_page = page if source_kind in {"pdf_page", "pptx_slide"} else None
            out.append(ChunkPiece(
                page=physical_page, text=body,
                source_metadata={
                    "kind": source_kind,
                    "unit_index": page if physical_page is not None else unit_index,
                    "char_start": start, "char_end": end, "chunk_index": len(out),
                    "splitter": "markdown" if markdown else "text",
                },
            ))
    return out
