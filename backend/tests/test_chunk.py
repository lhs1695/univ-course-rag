"""Direct splitter adapter contracts on synthetic text; no model semantics."""

import pytest
from app.services.chunk import CHUNK_SIZE, SHORT_PAGE_CHARS, chunk_pages


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
def test_substantive_page_or_slide_numbers_are_retained_without_merging(filename, kind) -> None:
    first, third = "first unit " * 12, "third unit " * 12
    assert min(len(first.strip()), len(third.strip())) >= SHORT_PAGE_CHARS
    pieces = chunk_pages([(1, first), (3, third)], filename=filename)
    assert [piece.page for piece in pieces] == [1, 3]
    assert [piece.source_metadata["unit_index"] for piece in pieces] == [1, 3]
    assert all(piece.source_metadata["kind"] == kind for piece in pieces)
    assert all(piece.source_metadata["char_start"] == 0 for piece in pieces)
    for piece, source in zip(pieces, (first, third), strict=True):
        _assert_spans([piece], source)
        assert "merged_unit_count" not in piece.source_metadata


@pytest.mark.parametrize("filename", ["course.pdf", "course.pptx"])
def test_short_title_merges_forward_and_attributes_body_page(filename) -> None:
    title, body = "课程概论：标题页", "课程正文与论证。" * 30
    pieces = chunk_pages([(2, title), (5, body)], filename=filename)
    assert len(pieces) == 1
    assert title in pieces[0].text and body in pieces[0].text
    assert all(piece.text.strip() != title for piece in pieces)
    assert pieces[0].page == pieces[0].source_metadata["unit_index"] == 5
    assert pieces[0].source_metadata == {
        "kind": "pdf_page" if filename.endswith(".pdf") else "pptx_slide",
        "unit_index": 5, "char_start": 0, "char_end": len(title + "\n\n" + body),
        "chunk_index": 0, "splitter": "text",
        "unit_index_start": 2, "unit_index_end": 5, "merged_unit_count": 2,
    }
    _assert_spans(pieces, title + "\n\n" + body)


@pytest.mark.parametrize("filename", ["course.pdf", "course.pptx"])
def test_consecutive_short_pages_merge_until_first_substantive_page(filename) -> None:
    short_units = [(1, "标题"), (3, "目录"), (4, "引言")]
    body, next_body = "正文。" * 60, "后续论证。" * 40
    pieces = chunk_pages(short_units + [(6, body), (7, next_body)], filename=filename)
    assert len(pieces) == 2
    _assert_spans(pieces[:1], "\n\n".join(text for _, text in short_units) + "\n\n" + body)
    _assert_spans(pieces[1:], next_body)
    assert [piece.page for piece in pieces] == [6, 7]
    meta = pieces[0].source_metadata
    assert (meta["unit_index_start"], meta["unit_index_end"], meta["merged_unit_count"]) == (1, 6, 4)
    assert "merged_unit_count" not in pieces[1].source_metadata
    assert [piece.source_metadata["chunk_index"] for piece in pieces] == [0, 1]


@pytest.mark.parametrize("filename", ["course.pdf", "course.pptx"])
@pytest.mark.parametrize("with_body", [False, True], ids=["only-short", "trailing-short"])
def test_pending_short_pages_close_as_final_group(filename, with_body) -> None:
    body = "完整正文。" * 30
    units = ([(1, body)] if with_body else []) + [(3, "附录标题"), (5, "补充说明更多内容")]
    pieces = chunk_pages(units, filename=filename)
    assert len(pieces) == 1 + int(with_body)
    if with_body:
        _assert_spans(pieces[:1], body)
    _assert_spans(pieces[-1:], "附录标题\n\n补充说明更多内容")
    meta = pieces[-1].source_metadata
    assert pieces[-1].page == meta["unit_index"] == 5
    assert (meta["unit_index_start"], meta["unit_index_end"], meta["merged_unit_count"]) == (3, 5, 2)
    assert all(isinstance(value, (str, int)) for piece in pieces for value in piece.source_metadata.values())


@pytest.mark.parametrize("filename", ["course.pdf", "course.pptx"])
def test_short_title_with_oversize_body_splits_and_attributes_each_span(filename) -> None:
    title, body = "课程标题", "正文内容。" * 500
    combined = title + "\n\n" + body
    pieces = chunk_pages([(1, title), (4, body)], filename=filename)
    assert len(pieces) > 1
    assert title in pieces[0].text
    assert all(piece.page == piece.source_metadata["unit_index"] == 4 for piece in pieces[1:])
    # The unchanged splitter can keep the title paragraph separate from an oversize body.
    for piece in pieces:
        start, end = piece.source_metadata["char_start"], piece.source_metadata["char_end"]
        title_chars = max(0, min(end, len(title)) - start)
        body_chars = max(0, min(end, len(combined)) - max(start, len(title) + 2))
        assert piece.page == (1 if title_chars >= body_chars else 4)
    assert all(piece.source_metadata["merged_unit_count"] == 2 for piece in pieces)
    assert [piece.source_metadata["chunk_index"] for piece in pieces] == list(range(len(pieces)))
    _assert_spans(pieces, combined)


@pytest.mark.parametrize("filename", ["course.pdf", "course.pptx"])
def test_short_threshold_uses_stripped_length_and_closes_at_exact_boundary(filename) -> None:
    short = " \n" + "甲" * (SHORT_PAGE_CHARS - 1)
    substantive = "乙" * SHORT_PAGE_CHARS
    pieces = chunk_pages([(2, short), (3, " \n\t"), (4, substantive), (6, "尾页")], filename=filename)
    assert len(pieces) == 2
    _assert_spans(pieces[:1], short + "\n\n" + substantive)
    _assert_spans(pieces[1:], "尾页")
    assert [piece.page for piece in pieces] == [4, 6]
    assert pieces[0].source_metadata["merged_unit_count"] == 2
    assert "merged_unit_count" not in pieces[1].source_metadata


@pytest.mark.parametrize("filename", ["course.pdf", "course.pptx"])
def test_equal_character_contributions_attribute_earliest_unit(filename) -> None:
    pieces = chunk_pages([(8, "甲" * 20), (3, "乙" * 20)], filename=filename)
    assert len(pieces) == 1
    assert pieces[0].page == pieces[0].source_metadata["unit_index"] == 8
    _assert_spans(pieces, "甲" * 20 + "\n\n" + "乙" * 20)


@pytest.mark.parametrize("filename", ["course.txt", "course.md", "course.markdown", "course.docx"])
def test_nonpaginated_short_units_remain_separate(filename) -> None:
    pieces = chunk_pages([(5, "first unit"), (8, " \n"), (12, "third unit")], filename=filename)
    assert [piece.text for piece in pieces] == ["first unit", "third unit"]
    assert all(piece.page is None for piece in pieces)
    assert [piece.source_metadata["unit_index"] for piece in pieces] == [1, 3]
    for piece in pieces:
        _assert_spans([piece], piece.text)
        assert {"unit_index_start", "unit_index_end", "merged_unit_count"}.isdisjoint(piece.source_metadata)


def test_nonpaginated_word_does_not_invent_a_physical_page() -> None:
    piece = chunk_pages([(1, "Word text")], filename="course.docx")[0]
    assert piece.page is None
    assert piece.source_metadata["kind"] == "docx_text"
    assert piece.source_metadata["unit_index"] == 1


def test_empty_units_produce_no_sources() -> None:
    assert chunk_pages([(1, " \n\t"), (2, "")], filename="note.pdf") == []
