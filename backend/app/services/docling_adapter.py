from __future__ import annotations

import hashlib
import io
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from time import perf_counter
from typing import Protocol


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


class PdfConverter(Protocol):
    """Small injection seam; implementations return a Docling-like result."""

    def convert(self, data: bytes) -> object: ...


class DoclingAdapterError(Exception):
    pass


class _DoclingPdfConverter:
    def __init__(self, *, max_pages: int) -> None:
        try:
            from docling.datamodel.base_models import DocumentStream
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise DoclingAdapterError("PDF parser is not installed") from exc
        self._document_stream = DocumentStream
        self._converter = DocumentConverter()
        self._max_pages = max_pages

    def convert(self, data: bytes) -> object:
        source = self._document_stream(name="upload.pdf", stream=io.BytesIO(data))
        return self._converter.convert(
            source,
            raises_on_error=True,
            max_num_pages=self._max_pages,
        )


def parse_pdf_document(
    data: bytes,
    *,
    converter: PdfConverter | None = None,
    max_pages: int,
    max_text_chars: int,
) -> ParsedDocument:
    """Convert PDF bytes into the project model without exposing Docling types."""
    try:
        started = perf_counter()
        result = (converter or _DoclingPdfConverter(max_pages=max_pages)).convert(data)
        conversion_time_ms = (perf_counter() - started) * 1000
    except DoclingAdapterError:
        raise
    except Exception as exc:
        raise DoclingAdapterError("unreadable PDF") from exc

    source = getattr(result, "document", result)
    if source is None:
        raise DoclingAdapterError("unreadable PDF")
    parser_version = _docling_version()
    page_elements: dict[int, list[ParsedElement]] = {
        number: [] for number in _page_numbers(source)
    }
    try:
        for item, _level in source.iterate_items():
            mapped = _map_item(item, source, parser_version)
            if mapped is not None:
                page_elements.setdefault(mapped.page, []).append(mapped)
    except DoclingAdapterError:
        raise
    except Exception as exc:
        raise DoclingAdapterError("unreadable PDF") from exc

    if page_elements and max(page_elements) > max_pages:
        raise DoclingAdapterError("extracted text exceeds resource limit")
    pages = tuple(
        ParsedPage(
            number=number,
            elements=tuple(elements),
            status=ParseStatus.SUCCEEDED,
        )
        for number, elements in sorted(page_elements.items())
    )
    result_status = _result_status(result)
    if result_status is ParseStatus.FAILED:
        raise DoclingAdapterError("unreadable PDF")
    document = ParsedDocument(
        pages=pages,
        parser_version=parser_version,
        status=result_status,
        conversion_time_ms=conversion_time_ms,
    )
    text_size = sum(
        len(element.text or "")
        for page in document.pages
        for element in page.elements
    )
    if text_size > max_text_chars:
        raise DoclingAdapterError("extracted text exceeds resource limit")
    if text_size == 0:
        raise DoclingAdapterError("no extractable text")
    return document


def flatten_pages(document: ParsedDocument) -> list[tuple[int, str]]:
    """Flatten element text in reading order, retaining physical page numbers."""
    units: list[tuple[int, str]] = []
    for page in document.pages:
        text = "\n\n".join(
            element.text.strip()
            for element in page.elements
            if element.text and element.text.strip()
        )
        if text:
            units.append((page.number, text))
    return units


def _map_item(
    item: object,
    document: object,
    parser_version: str,
) -> ParsedElement | None:
    label = _label(item)
    kind = _element_type(label)
    if kind is None:
        return None
    provenance = list(getattr(item, "prov", ()) or ())
    page = int(getattr(provenance[0], "page_no", 0) or 0) if provenance else 0
    if page < 1:
        return None
    method = _extraction_method(item, kind)
    text = _item_text(item, kind, document)
    return ParsedElement(
        kind=kind,
        text=text,
        page=page,
        bbox=_bbox(provenance[0]) if provenance else None,
        extraction_method=method,
        parser_version=parser_version,
        model=_optional_string(item, "model"),
        status=ParseStatus.SUCCEEDED,
        asset_ref=_optional_string(item, "asset_ref", "self_ref"),
    )


def _page_numbers(document: object) -> list[int]:
    pages = getattr(document, "pages", {}) or {}
    if hasattr(pages, "keys"):
        return [int(number) for number in pages]
    return list(range(1, len(pages) + 1))


def _label(item: object) -> str:
    value = getattr(item, "label", "")
    return str(getattr(value, "value", value)).lower()


def _element_type(label: str) -> ElementType | None:
    if label == "formula":
        return ElementType.FORMULA
    if label == "table":
        return ElementType.TABLE
    if label == "chart":
        return ElementType.CHART
    if label in {"picture", "image"}:
        return ElementType.IMAGE
    if label in {
        "text",
        "title",
        "section_header",
        "page_header",
        "page_footer",
        "list_item",
        "caption",
        "footnote",
        "code",
        "document_index",
    }:
        return ElementType.TEXT
    return None


def _extraction_method(item: object, kind: ElementType) -> ExtractionMethod:
    explicit = _optional_string(item, "extraction_method")
    if explicit:
        try:
            return ExtractionMethod(explicit.lower())
        except ValueError:
            pass
    if kind is ElementType.FORMULA:
        return ExtractionMethod.FORMULA_RECOGNITION
    if kind is ElementType.IMAGE:
        return ExtractionMethod.IMAGE_DESCRIPTION
    if kind in {ElementType.TABLE, ElementType.CHART}:
        return ExtractionMethod.CHART_TABLE_EXTRACTION
    return ExtractionMethod.NATIVE_TEXT


def _item_text(item: object, kind: ElementType, document: object) -> str | None:
    if kind is ElementType.TABLE:
        exporter = getattr(item, "export_to_markdown", None)
        if callable(exporter):
            return _clean_text(exporter(doc=document))
    direct = _clean_text(getattr(item, "text", None))
    if direct:
        return direct
    if kind in {ElementType.IMAGE, ElementType.CHART}:
        annotations = getattr(item, "annotations", ()) or ()
        descriptions = [
            text for annotation in annotations
            if (text := _clean_text(getattr(annotation, "text", None)))
        ]
        return "\n".join(descriptions) or None
    return None


def _bbox(provenance: object) -> BoundingBox | None:
    box = getattr(provenance, "bbox", None)
    if box is None:
        return None
    values = [getattr(box, name, None) for name in ("l", "t", "r", "b")]
    if any(value is None for value in values):
        values = [
            getattr(box, name, None)
            for name in ("left", "top", "right", "bottom")
        ]
    if any(value is None for value in values):
        return None
    return BoundingBox(*(float(value) for value in values))


def _optional_string(item: object, *names: str) -> str | None:
    for name in names:
        value = getattr(item, name, None)
        if value is not None:
            return str(getattr(value, "value", value))
    return None


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.replace("\r\n", "\n").strip()
    return text or None


def _result_status(result: object) -> ParseStatus:
    raw_status = getattr(result, "status", "")
    status = str(getattr(raw_status, "value", raw_status)).lower()
    if "partial" in status:
        return ParseStatus.PARTIAL
    if "fail" in status:
        return ParseStatus.FAILED
    return ParseStatus.SUCCEEDED


def _docling_version() -> str:
    try:
        return version("docling")
    except PackageNotFoundError:
        return "unknown"
