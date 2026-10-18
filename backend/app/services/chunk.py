from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from semantic_text_splitter import MarkdownSplitter, TextSplitter

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
SHORT_PAGE_CHARS = 120
CHUNKING_VERSION = "sts-0.33.0-char800-overlap120-shortmerge120-r6-v2"


@dataclass(frozen=True)
class ChunkPiece:
    page: int | None
    text: str
    source_metadata: dict[str, str | int]


def chunk_pages(
    pages: list[tuple[int | None, str]], *, filename: str,
) -> list[ChunkPiece]:
    """Adapt semantic-text-splitter 0.33.0 (MIT), without copying its algorithms.

    Offsets are Python character positions into a group of sanitized units,
    not bytes/positions in the original binary document. Short pages/slides
    merge forward; nonpaginated documents remain per-unit without physical pages.
    """
    suffix = Path(filename).suffix.lower()
    source_kind = {
        ".pdf": "pdf_page", ".pptx": "pptx_slide", ".docx": "docx_text",
        ".md": "markdown", ".markdown": "markdown", ".txt": "plain_text",
    }[suffix]
    markdown = source_kind == "markdown"
    paginated = source_kind in {"pdf_page", "pptx_slide"}
    splitter = (MarkdownSplitter if markdown else TextSplitter)(CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    groups = []
    pending = []
    for unit_index, (page, text) in enumerate(pages, start=1):
        if not text.strip():
            continue
        pending.append((unit_index, page, text))
        if not paginated or len(text.strip()) >= SHORT_PAGE_CHARS:
            groups.append(pending)
            pending = []
    if pending:
        groups.append(pending)

    out = []
    for group in groups:
        text = "\n\n".join(unit_text for _, _, unit_text in group)
        unit_spans = []
        offset = 0
        for unit_index, page, unit_text in group:
            unit_spans.append((unit_index, page, offset, offset + len(unit_text)))
            offset += len(unit_text) + 2
        for start, body in splitter.chunk_indices(text):
            end = start + len(body)
            if not body.strip():
                continue
            if not (0 <= start < end <= len(text) and len(body) <= CHUNK_SIZE and text[start:end] == body):
                raise ValueError("splitter returned an invalid source span")
            # max retains the earliest unit on ties; separators belong to no unit.
            unit_index, page, _, _ = max(
                unit_spans,
                key=lambda unit: max(0, min(end, unit[3]) - max(start, unit[2])),
            )
            physical_page = page if paginated else None
            metadata = {
                "kind": source_kind,
                "unit_index": page if physical_page is not None else unit_index,
                "char_start": start, "char_end": end, "chunk_index": len(out),
                "splitter": "markdown" if markdown else "text",
            }
            if len(group) > 1:
                metadata.update({
                    "unit_index_start": group[0][1],
                    "unit_index_end": group[-1][1],
                    "merged_unit_count": len(group),
                })
            out.append(ChunkPiece(
                page=physical_page, text=body,
                source_metadata=metadata,
            ))
    return out
