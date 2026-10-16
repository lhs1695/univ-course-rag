from __future__ import annotations

import io
from dataclasses import dataclass
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
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
        result = (converter or _DoclingPdfConverter(max_pages=max_pages)).convert(data)
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
