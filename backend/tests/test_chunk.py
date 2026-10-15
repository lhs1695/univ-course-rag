"""Direct splitter adapter contracts on synthetic text; no model semantics."""

import pytest
from app.services.chunk import CHUNK_SIZE, chunk_pages


def _assert_spans(pieces, source: str) -> None:
    covered = set()
    for piece in pieces:
        meta = piece.source_metadata
        start, end = meta["char_start"], meta["char_end"]
        assert source[start:end] == piece.text
        assert 0 < len(piece.text) <= CHUNK_SIZE
        covered.update(range(start, end))
    assert all(index in covered for index, char in enumerate(source) if not char.isspace())


@pytest.mark.parametrize("filename", ["note.md", "note.markdown", "note.txt"])
def test_unicode_repeated_text_keeps_exact_character_offsets(filename) -> None:
    source = "\n\t" + ("中文🙂e\u0301重复内容。" * 220) + "\n "
    pieces = chunk_pages([(1, source)], filename=filename)
    assert len(pieces) > 1
    _assert_spans(pieces, source)
    assert [piece.source_metadata["chunk_index"] for piece in pieces] == list(range(len(pieces)))
    assert all(piece.page is None for piece in pieces)
    starts = [piece.source_metadata["char_start"] for piece in pieces]
    assert starts == sorted(set(starts))


def test_plain_paragraphs_are_not_cut_when_they_fit() -> None:
    first, second = "alpha " * 100, "beta " * 120
    source = first + "\n\n" + second
    pieces = chunk_pages([(1, source)], filename="note.txt")
    assert [piece.text for piece in pieces] == [first.strip(), second.strip()]
    _assert_spans(pieces, source)


def test_markdown_heading_sections_respect_their_boundaries() -> None:
    source = "# One\n\n" + "one " * 150 + "\n\n# Two\n\n" + "two " * 150
    pieces = chunk_pages([(1, source)], filename="course.md")
    assert len(pieces) == 2
    assert pieces[0].text.startswith("# One")
    assert pieces[1].text.startswith("# Two")
    assert "# Two" not in pieces[0].text
    _assert_spans(pieces, source)


@pytest.mark.parametrize("block", [
    "```python\n# this is code, not a heading\nvalue = 1\n```",
    "- first item\n- second item\n- third item",
    "| key | value |\n| --- | --- |\n| A | B |",
])
def test_fitting_markdown_blocks_remain_intact(block) -> None:
    source = "# Course\n\n" + "intro " * 90 + "\n\n" + block + "\n\n" + "tail " * 90
    pieces = chunk_pages([(1, source)], filename="course.md")
    assert len(pieces) > 1
    assert any(block in piece.text for piece in pieces)
    _assert_spans(pieces, source)


@pytest.mark.parametrize("filename", ["course.md", "course.txt"])
def test_oversize_unbroken_block_obeys_capacity_without_losing_text(filename) -> None:
    source = "无分隔符" * 601
    pieces = chunk_pages([(1, source)], filename=filename)
    assert len(pieces) > 1
    _assert_spans(pieces, source)


@pytest.mark.parametrize("filename, kind", [("course.pdf", "pdf_page"), ("course.pptx", "pptx_slide")])
def test_actual_page_or_slide_numbers_are_retained_without_cross_unit_merging(filename, kind) -> None:
    pieces = chunk_pages([(1, "first unit"), (3, "third unit")], filename=filename)
    assert [piece.page for piece in pieces] == [1, 3]
    assert [piece.source_metadata["unit_index"] for piece in pieces] == [1, 3]
    assert all(piece.source_metadata["kind"] == kind for piece in pieces)
    assert all(piece.source_metadata["char_start"] == 0 for piece in pieces)


def test_nonpaginated_word_does_not_invent_a_physical_page() -> None:
    piece = chunk_pages([(1, "Word text")], filename="course.docx")[0]
    assert piece.page is None
    assert piece.source_metadata["kind"] == "docx_text"
    assert piece.source_metadata["unit_index"] == 1


def test_empty_units_produce_no_sources() -> None:
    assert chunk_pages([(1, " \n\t"), (2, "")], filename="note.pdf") == []
