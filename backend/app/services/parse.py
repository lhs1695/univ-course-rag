from __future__ import annotations

import io


class ParseError(Exception):
    pass


_UNSUPPORTED = "unsupported file type; accepted: PDF, PPTX, DOCX, Markdown, or plain text"


def parse_document(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    """Return (page, text) pairs. Page is 1-based for PDF/PPTX, 1 otherwise."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return _parse_pdf(data)
    if name.endswith(".pptx"):
        return _parse_ppt(data)
    if name.endswith(".docx"):
        return _parse_word(data)
    if name.endswith((".md", ".markdown", ".txt")):
        return _parse_text(data)
    raise ParseError(_UNSUPPORTED)


def _parse_text(data: bytes) -> list[tuple[int | None, str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParseError("text file is not valid UTF-8") from exc
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ParseError("no extractable text")
    return [(1, text)]


def _parse_pdf(data: bytes) -> list[tuple[int | None, str]]:
    try:
        import fitz
    except ImportError as exc:
        raise ParseError("PDF parser is not installed") from exc
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ParseError("unreadable PDF") from exc
    pages: list[tuple[int | None, str]] = []
    try:
        for index, page in enumerate(doc):
            page_text = page.get_text("text").replace("\r\n", "\n").strip()
            if page_text:
                pages.append((index + 1, page_text))
    finally:
        doc.close()
    if not pages:
        raise ParseError("no extractable text")
    return pages


def _parse_ppt(data: bytes) -> list[tuple[int | None, str]]:
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError as exc:
        raise ParseError("PPT parser is not installed") from exc
    try:
        presentation = Presentation(io.BytesIO(data))
    except Exception as exc:
        raise ParseError("unreadable PPT") from exc

    pages: list[tuple[int | None, str]] = []
    for index, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            parts.extend(_ppt_shape_text(shape, MSO_SHAPE_TYPE))
        page_text = "\n".join(parts).replace("\r\n", "\n").strip()
        if page_text:
            pages.append((index, page_text))
    if not pages:
        raise ParseError("no extractable text")
    return pages


def _ppt_shape_text(shape: object, mso_shape_type: object) -> list[str]:
    parts: list[str] = []
    shape_type = getattr(shape, "shape_type", None)
    if shape_type == mso_shape_type.GROUP:
        for inner in shape.shapes:
            parts.extend(_ppt_shape_text(inner, mso_shape_type))
        return parts
    if getattr(shape, "has_text_frame", False):
        text = shape.text_frame.text.replace("\r\n", "\n").strip()
        if text:
            parts.append(text)
    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            cells = [cell.text.replace("\r\n", "\n").strip() for cell in row.cells]
            line = "\t".join(cell for cell in cells if cell)
            if line:
                parts.append(line)
    return parts


def _parse_word(data: bytes) -> list[tuple[int | None, str]]:
    try:
        from docx import Document
    except ImportError as exc:
        raise ParseError("Word parser is not installed") from exc
    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise ParseError("unreadable Word") from exc

    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.replace("\r\n", "\n").strip()
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.replace("\r\n", "\n").strip() for cell in row.cells]
            line = "\t".join(cell for cell in cells if cell)
            if line:
                parts.append(line)
    page_text = "\n".join(parts).strip()
    if not page_text:
        raise ParseError("no extractable text")
    return [(1, page_text)]
