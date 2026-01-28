"""Identify document type from filename and content."""

import re
from enum import Enum
from pathlib import Path


class DocumentType(Enum):
    APPELLANT_BRIEF = "appellant_brief"
    APPELLEE_BRIEF = "appellee_brief"
    REPLY_BRIEF = "reply_brief"
    DISTRICT_COURT_ORDER = "order"
    JUDGMENT = "judgment"
    FINDINGS_CONCLUSIONS = "findings"
    NOTICE_OF_APPEAL = "notice"
    TRANSCRIPT = "transcript"
    EXHIBIT = "exhibit"
    OTHER = "other"


# Filename patterns (case-insensitive)
FILENAME_PATTERNS: list[tuple[re.Pattern, DocumentType]] = [
    (re.compile(r"(?:Apt|Appellant).*Reply", re.IGNORECASE), DocumentType.REPLY_BRIEF),
    (re.compile(r"(?:Apt|Appellant).*Br", re.IGNORECASE), DocumentType.APPELLANT_BRIEF),
    (re.compile(r"(?:Ape|Appellee).*Br", re.IGNORECASE), DocumentType.APPELLEE_BRIEF),
    (re.compile(r"Reply.*Br", re.IGNORECASE), DocumentType.REPLY_BRIEF),
    (re.compile(r"Order", re.IGNORECASE), DocumentType.DISTRICT_COURT_ORDER),
    (re.compile(r"Judgment", re.IGNORECASE), DocumentType.JUDGMENT),
    (re.compile(r"Finding", re.IGNORECASE), DocumentType.FINDINGS_CONCLUSIONS),
    (re.compile(r"Notice.*Appeal", re.IGNORECASE), DocumentType.NOTICE_OF_APPEAL),
    (re.compile(r"Transcript", re.IGNORECASE), DocumentType.TRANSCRIPT),
    (re.compile(r"Exhibit", re.IGNORECASE), DocumentType.EXHIBIT),
]

# Content patterns for fallback classification
CONTENT_PATTERNS: list[tuple[re.Pattern, DocumentType]] = [
    (re.compile(r"REPLY\s+BRIEF", re.IGNORECASE), DocumentType.REPLY_BRIEF),
    (re.compile(r"APPELLANT['']?S\s+BRIEF", re.IGNORECASE), DocumentType.APPELLANT_BRIEF),
    (re.compile(r"APPELLEE['']?S\s+BRIEF", re.IGNORECASE), DocumentType.APPELLEE_BRIEF),
    (re.compile(r"BRIEF\s+OF\s+(?:THE\s+)?APPELLANT", re.IGNORECASE), DocumentType.APPELLANT_BRIEF),
    (re.compile(r"BRIEF\s+OF\s+(?:THE\s+)?APPELLEE", re.IGNORECASE), DocumentType.APPELLEE_BRIEF),
    (re.compile(r"ORDER\s+(?:FOR\s+)?JUDGMENT", re.IGNORECASE), DocumentType.JUDGMENT),
    (re.compile(r"(?:IT\s+IS\s+(?:HEREBY\s+)?ORDERED|ORDER\s+OF\s+THE\s+COURT)", re.IGNORECASE), DocumentType.DISTRICT_COURT_ORDER),
    (re.compile(r"FINDINGS?\s+OF\s+FACT", re.IGNORECASE), DocumentType.FINDINGS_CONCLUSIONS),
    (re.compile(r"NOTICE\s+OF\s+APPEAL", re.IGNORECASE), DocumentType.NOTICE_OF_APPEAL),
]


def classify(filename: str, text: str = "") -> DocumentType:
    """Classify a document by filename first, then content."""
    stem = Path(filename).stem

    # Try filename patterns
    for pattern, doc_type in FILENAME_PATTERNS:
        if pattern.search(stem):
            return doc_type

    # Try content patterns (first 3000 chars)
    header_text = text[:3000]
    for pattern, doc_type in CONTENT_PATTERNS:
        if pattern.search(header_text):
            return doc_type

    return DocumentType.OTHER
