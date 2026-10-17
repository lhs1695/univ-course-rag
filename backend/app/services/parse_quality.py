from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass, replace
from enum import StrEnum


class ElementType(StrEnum):
    TEXT = "text"
    FORMULA = "formula"
    TABLE = "table"
    IMAGE = "image"
    CHART = "chart"


class ExtractionMethod(StrEnum):
    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    FORMULA_RECOGNITION = "formula_recognition"
    IMAGE_DESCRIPTION = "image_description"
    CHART_TABLE_EXTRACTION = "chart_table_extraction"


class ParseStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class ParsedElement:
    kind: ElementType
    text: str | None
    page: int
    bbox: BoundingBox | None
    extraction_method: ExtractionMethod
    parser_version: str
    model: str | None
    status: ParseStatus
    asset_ref: str | None


@dataclass(frozen=True)
class ParsedPage:
    number: int
    elements: tuple[ParsedElement, ...]
    status: ParseStatus


@dataclass(frozen=True)
class ParsedDocument:
    pages: tuple[ParsedPage, ...]
    parser_version: str
    status: ParseStatus
    conversion_time_ms: float | None = None


@dataclass(frozen=True)
class PageQualityEntry:
    number: int
    status: ParseStatus
    empty: bool
    timing_ms: float | None
    element_counts: dict[str, int]
    method_counts: dict[str, int]
    notes: tuple[str, ...]
    char_length: int = 0
    sparse: bool = False
    abnormal_chars: bool = False


@dataclass(frozen=True)
class ParseQualityReport:
    status: ParseStatus
    total_pages: int
    pages: tuple[PageQualityEntry, ...]
    success_pages: tuple[int, ...]
    abnormal_pages: tuple[int, ...]
    empty_pages: tuple[int, ...]
    success_count: int
    abnormal_count: int
    empty_count: int
    page_numbers_continuous: bool
    missing_pages: tuple[int, ...]
    element_counts: dict[str, int]
    method_counts: dict[str, int]
    parse_method_summary: tuple[str, ...]
    parser_version: str
    models: tuple[str, ...]
    structured_hash: str
    conversion_time_ms: float | None
    notes: tuple[str, ...]
    input_sha256: str | None = None


def build_parse_quality_report(
    document: ParsedDocument,
    *,
    page_timings_ms: dict[int, float] | None = None,
) -> ParseQualityReport:
    """Conservatively require usable text and valid provenance on every page."""
    entries = []
    element_counts = dict.fromkeys(ElementType, 0)
    method_counts = dict.fromkeys(ExtractionMethod, 0)
    models = set()
    numbers = [page.number for page in document.pages]
    missing = tuple(sorted(set(range(1, max(numbers, default=0) + 1)) - set(numbers)))
    continuous = bool(numbers) and sorted(numbers) == list(range(1, len(numbers) + 1))
    notes = []
    if document.status is not ParseStatus.SUCCEEDED:
        notes.append(f"converter_status:{document.status}")
    if not continuous:
        notes.append("invalid_page_sequence")
    for page in document.pages:
        counts = dict.fromkeys(ElementType, 0)
        methods = dict.fromkeys(ExtractionMethod, 0)
        page_notes = []
        empty = not any(e.text and e.text.strip() for e in page.elements)
        if empty:
            page_notes.append("no_usable_text")
        if page.number < 1 or numbers.count(page.number) > 1:
            page_notes.append("invalid_page_number")
        for element in page.elements:
            counts[element.kind] += 1
            methods[element.extraction_method] += 1
            if element.model:
                models.add(element.model)
            if element.page != page.number:
                page_notes.append("element_page_mismatch")
            if element.status is not ParseStatus.SUCCEEDED:
                page_notes.append(f"element_status:{element.status}")
        if page.status is not ParseStatus.SUCCEEDED:
            page_notes.append(f"page_status:{page.status}")
        status = page.status
        if page_notes and status is ParseStatus.SUCCEEDED:
            status = ParseStatus.PARTIAL
        entries.append(PageQualityEntry(
            page.number, status, empty, (page_timings_ms or {}).get(page.number),
            counts, methods, tuple(sorted(set(page_notes))),
        ))
        notes.extend(f"page:{page.number}:{note}" for note in sorted(set(page_notes)))
        for kind, count in counts.items():
            element_counts[kind] += count
        for method, count in methods.items():
            method_counts[method] += count
    success = tuple(e.number for e in entries if e.status is ParseStatus.SUCCEEDED)
    abnormal = tuple(e.number for e in entries if e.status is not ParseStatus.SUCCEEDED)
    empty_pages = tuple(e.number for e in entries if e.empty)
    status = document.status
    if status is ParseStatus.SUCCEEDED and (abnormal or not continuous):
        status = ParseStatus.PARTIAL
    if not entries or all(e.empty for e in entries):
        status = ParseStatus.FAILED
    # v1 canonical UTF-8 JSON: sorted keys, compact separators, literal Unicode;
    # preserve page/element reading order and all structural fields, exclude timing.
    canonical = json.dumps(
        {"schema": 1, "parser_version": document.parser_version,
         "status": document.status, "pages": [asdict(p) for p in document.pages]},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return ParseQualityReport(
        status=status,
        total_pages=len(entries),
        pages=tuple(entries),
        success_pages=success,
        abnormal_pages=abnormal,
        empty_pages=empty_pages,
        success_count=len(success),
        abnormal_count=len(abnormal),
        empty_count=len(empty_pages),
        page_numbers_continuous=continuous,
        missing_pages=missing,
        element_counts=element_counts,
        method_counts=method_counts,
        parse_method_summary=tuple(sorted(m for m, count in method_counts.items() if count)),
        parser_version=document.parser_version,
        models=tuple(sorted(models)),
        structured_hash=hashlib.sha256(canonical).hexdigest(),
        conversion_time_ms=document.conversion_time_ms,
        notes=tuple(notes),
    )


def has_abnormal_characters(text: str) -> bool:
    return any(unicodedata.category(c) == "Cc" and c not in "\t\n\r" for c in text)


def build_native_pdf_quality_report(
    pages: list[tuple[int, str]], *, parser_version: str, input_sha256: str,
    raw_abnormal_pages: set[int] | None = None,
    conversion_time_ms: float | None = None,
) -> ParseQualityReport:
    """Report every physical page; coverage warnings do not imply execution failure."""
    document = ParsedDocument(
        pages=tuple(ParsedPage(number, (ParsedElement(
            ElementType.TEXT, text, number, None, ExtractionMethod.NATIVE_TEXT,
            parser_version, None, ParseStatus.SUCCEEDED, None,
        ),), ParseStatus.SUCCEEDED) for number, text in pages),
        parser_version=parser_version, status=ParseStatus.SUCCEEDED,
        conversion_time_ms=conversion_time_ms,
    )
    report = build_parse_quality_report(document)
    entries = []
    for entry, (_, text) in zip(report.pages, pages, strict=True):
        stripped = text.strip()
        # Empty pages are not also labeled sparse; sparse is for short non-empty text.
        sparse = bool(stripped) and len(stripped) < 50
        abnormal = entry.number in (raw_abnormal_pages or set()) or has_abnormal_characters(text)
        notes = list(entry.notes)
        if sparse:
            notes.append("sparse_text")
        if abnormal:
            notes.append("abnormal_characters")
        entries.append(replace(
            entry, char_length=len(text), sparse=sparse, abnormal_chars=abnormal,
            status=ParseStatus.PARTIAL if notes else ParseStatus.SUCCEEDED,
            notes=tuple(notes),
        ))
    success = tuple(e.number for e in entries if e.status is ParseStatus.SUCCEEDED)
    abnormal_pages = tuple(e.number for e in entries if e.status is not ParseStatus.SUCCEEDED)
    status = ParseStatus.PARTIAL if abnormal_pages else ParseStatus.SUCCEEDED
    if not report.page_numbers_continuous or all(e.empty for e in entries):
        status = ParseStatus.FAILED
    return replace(
        report, pages=tuple(entries), status=status, input_sha256=input_sha256,
        success_pages=success, success_count=len(success), abnormal_pages=abnormal_pages,
        abnormal_count=len(abnormal_pages),
        conversion_time_ms=conversion_time_ms,
        notes=tuple(f"page:{e.number}:{note}" for e in entries for note in e.notes),
    )

