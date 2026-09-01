from __future__ import annotations


class ParseError(Exception):
    pass


def parse_document(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    """Return (page, text) pairs. Page is 1-based for PDF, 1 for MD/text."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return _parse_pdf(data)
    if name.endswith((".md", ".markdown", ".txt")):
        return _parse_text(data)
    raise ParseError("unsupported file type; first period accepts PDF, Markdown, or plain text")


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
