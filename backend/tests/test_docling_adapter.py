import builtins
from types import SimpleNamespace

import pytest
from app.services.docling_adapter import (
    DoclingAdapterError,
    ElementType,
    ExtractionMethod,
    flatten_pages,
    parse_pdf_document,
)
from app.services.parse import ParseError, parse_document


class FakeItem(SimpleNamespace):
    def export_to_markdown(self, *, doc: object) -> str:
        assert doc is not None
        return self.markdown


class FakeConverter:
    def __init__(
        self,
        document: object | None = None,
        error: Exception | None = None,
        status: str = "success",
    ) -> None:
        self.document = document
        self.error = error
        self.status = status

    def convert(self, data: bytes) -> object:
        assert data == b"pdf"
        if self.error:
            raise self.error
        return SimpleNamespace(document=self.document, status=self.status)


def _prov(page: int) -> SimpleNamespace:
    return SimpleNamespace(
        page_no=page,
        bbox=SimpleNamespace(l=1, t=2, r=3, b=4),
    )


def _document(*items: object, pages: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        pages={number: object() for number in range(1, pages + 1)},
        iterate_items=lambda: iter((item, 0) for item in items),
    )


def _parse(document: object):
    return parse_pdf_document(
        b"pdf",
        converter=FakeConverter(document),
        max_pages=10,
        max_text_chars=10_000,
    )


def test_maps_normal_and_ocr_text_without_claiming_ocr_is_native() -> None:
    native = FakeItem(label="text", text="Native", prov=[_prov(1)])
    ocr = FakeItem(
        label="text",
        text="Scanned",
        prov=[_prov(2)],
        extraction_method="ocr",
        model="rapidocr",
    )

    parsed = _parse(_document(native, ocr, pages=2))

    assert parsed.pages[0].elements[0].extraction_method is ExtractionMethod.NATIVE_TEXT
    assert parsed.pages[1].elements[0].extraction_method is ExtractionMethod.OCR
    assert parsed.pages[1].elements[0].model == "rapidocr"
    assert parsed.pages[0].elements[0].bbox is not None
    assert flatten_pages(parsed) == [(1, "Native"), (2, "Scanned")]


def test_preserves_formula_table_image_and_chart_in_project_model() -> None:
    items = [
        FakeItem(label="formula", text="x^2", prov=[_prov(1)]),
        FakeItem(label="table", markdown="|a|b|", prov=[_prov(1)]),
        FakeItem(
            label="picture",
            annotations=[SimpleNamespace(text="A labelled diagram")],
            prov=[_prov(1)],
            self_ref="#/pictures/0",
        ),
        FakeItem(label="chart", text="Values rise", prov=[_prov(1)]),
    ]

    elements = _parse(_document(*items)).pages[0].elements

    assert [element.kind for element in elements] == [
        ElementType.FORMULA,
        ElementType.TABLE,
        ElementType.IMAGE,
        ElementType.CHART,
    ]
    assert [element.extraction_method for element in elements] == [
        ExtractionMethod.FORMULA_RECOGNITION,
        ExtractionMethod.CHART_TABLE_EXTRACTION,
        ExtractionMethod.IMAGE_DESCRIPTION,
        ExtractionMethod.CHART_TABLE_EXTRACTION,
    ]
    assert elements[2].asset_ref == "#/pictures/0"


@pytest.mark.parametrize(
    ("converter", "message"),
    [
        (FakeConverter(error=ValueError("broken")), "unreadable PDF"),
        (FakeConverter(_document()), "no extractable text"),
    ],
)
def test_safe_failure_messages(converter: FakeConverter, message: str) -> None:
    with pytest.raises(DoclingAdapterError, match=message):
        parse_pdf_document(
            b"pdf", converter=converter, max_pages=10, max_text_chars=10_000
        )


def test_failed_conversion_status_is_unreadable() -> None:
    item = FakeItem(label="text", text="Incomplete", prov=[_prov(1)])
    with pytest.raises(DoclingAdapterError, match="unreadable PDF"):
        parse_pdf_document(
            b"pdf",
            converter=FakeConverter(_document(item), status="failure"),
            max_pages=10,
            max_text_chars=10_000,
        )


def test_missing_docling_becomes_existing_safe_parse_error(monkeypatch) -> None:
    real_import = builtins.__import__

    def missing_docling(name, *args, **kwargs):
        if name.startswith("docling"):
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_docling)

    with pytest.raises(ParseError, match="PDF parser is not installed"):
        parse_document("missing.pdf", b"pdf")


def test_resource_limits_for_page_count_and_text_size() -> None:
    item = FakeItem(label="text", text="hello world", prov=[_prov(3)])
    document = _document(item, pages=3)
    with pytest.raises(DoclingAdapterError, match="extracted text exceeds resource limit"):
        parse_pdf_document(
            b"pdf",
            converter=FakeConverter(document),
            max_pages=2,
            max_text_chars=10_000,
        )

    short = FakeItem(label="text", text="abcdefghij", prov=[_prov(1)])
    with pytest.raises(DoclingAdapterError, match="extracted text exceeds resource limit"):
        parse_pdf_document(
            b"pdf",
            converter=FakeConverter(_document(short)),
            max_pages=10,
            max_text_chars=5,
        )


def test_partial_status_is_preserved_when_text_exists() -> None:
    item = FakeItem(label="text", text="Partial page", prov=[_prov(1)])
    parsed = parse_pdf_document(
        b"pdf",
        converter=FakeConverter(_document(item), status="partial_success"),
        max_pages=10,
        max_text_chars=10_000,
    )
    assert parsed.status.value == "partial"
    assert flatten_pages(parsed) == [(1, "Partial page")]
