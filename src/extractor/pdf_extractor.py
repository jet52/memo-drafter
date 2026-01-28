"""PDF text extraction for appellate briefs and court documents."""

import logging
from pathlib import Path

from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LAParams, LTTextContainer

logger = logging.getLogger(__name__)


def extract(pdf_path: Path) -> str:
    """Extract all text from a PDF using pdfminer.six."""
    laparams = LAParams(
        line_margin=0.3,  # Tighter for legal documents
        word_margin=0.1,
        char_margin=2.0,
        boxes_flow=0.5,
    )
    text = extract_text(str(pdf_path), laparams=laparams)
    if len(text.strip()) < 100:
        logger.warning("Low text extraction from %s — may be a scanned PDF", pdf_path.name)
    return text


def extract_with_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text with page numbers for record citation mapping."""
    laparams = LAParams(
        line_margin=0.3,
        word_margin=0.1,
        char_margin=2.0,
        boxes_flow=0.5,
    )
    pages = []
    for page_num, page_layout in enumerate(extract_pages(str(pdf_path), laparams=laparams), start=1):
        page_text = ""
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                page_text += element.get_text()
        pages.append((page_num, page_text))
    return pages


def extract_metadata(pdf_path: Path) -> dict:
    """Extract PDF metadata (title, author, creation date)."""
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdfdocument import PDFDocument

    metadata = {"filename": pdf_path.name}
    try:
        with open(pdf_path, "rb") as f:
            parser = PDFParser(f)
            doc = PDFDocument(parser)
            if doc.info:
                info = doc.info[0]
                for key in ("Title", "Author", "CreationDate"):
                    val = info.get(key)
                    if val:
                        metadata[key.lower()] = (
                            val.decode("utf-8", errors="replace") if isinstance(val, bytes) else str(val)
                        )
    except Exception as e:
        logger.debug("Could not extract metadata from %s: %s", pdf_path.name, e)
    return metadata
