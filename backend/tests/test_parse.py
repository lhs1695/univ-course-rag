"""Synthetic parser/order regressions for the R5 splitter inputs."""

import io
from types import SimpleNamespace

from app.services.parse import parse_document
from docx import Document
from pptx import Presentation


def test_word_interleaves_tables_and_paragraphs_in_document_order() -> None:
    document = Document()
    document.add_paragraph("First heading", style="Heading 1")
    first = document.add_table(rows=1, cols=3)
    first.cell(0, 0).text = "First table left"
    first.cell(0, 2).text = "First table right"
    document.add_paragraph("Between the tables")
    second = document.add_table(rows=1, cols=1)
    second.cell(0, 0).text = "Second table"
    document.add_paragraph("Final paragraph")
    output = io.BytesIO()
    document.save(output)

    units = parse_document("synthetic.docx", output.getvalue())

    body = units[0][1]
    assert body == (
        "First heading\n\nFirst table left\t\tFirst table right\n\n"
        "Between the tables\n\nSecond table\n\nFinal paragraph"
    )


def test_pdf_skips_empty_page_without_renumbering_later_sources() -> None:
    first = SimpleNamespace(
        label="text",
        text="First page",
        prov=[SimpleNamespace(page_no=1)],
    )
    third = SimpleNamespace(
        label="text",
        text="Third page",
        prov=[SimpleNamespace(page_no=3)],
    )
    document = SimpleNamespace(
        pages={1: object(), 2: object(), 3: object()},
        iterate_items=lambda: iter([(first, 0), (third, 0)]),
    )
    converter = SimpleNamespace(convert=lambda _data: SimpleNamespace(document=document))
    units = parse_document("synthetic.pdf", b"fake", pdf_converter=converter)
    assert [page for page, _text in units] == [1, 3]
    assert [text for _page, text in units] == ["First page", "Third page"]


def test_slides_skip_empty_slide_without_renumbering_later_sources() -> None:
    presentation = Presentation()
    blank = presentation.slide_layouts[6]
    presentation.slides.add_slide(blank).shapes.add_textbox(0, 0, 100, 100).text = "First slide"
    presentation.slides.add_slide(blank)
    presentation.slides.add_slide(blank).shapes.add_textbox(0, 0, 100, 100).text = "Third slide"
    output = io.BytesIO()
    presentation.save(output)
    units = parse_document("synthetic.pptx", output.getvalue())
    assert [page for page, _text in units] == [1, 3]
    assert [text for _page, text in units] == ["First slide", "Third slide"]
