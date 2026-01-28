"""Extract structure from raw text (headings, arguments, citations)."""

import re
from dataclasses import dataclass, field


@dataclass
class Citation:
    raw_text: str
    citation_type: str  # 'nd_case', 'nw2d', 'ndcc', 'nd_rule', 'record', 'paragraph'
    normalized: str


@dataclass
class Argument:
    heading: str
    text: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class BriefStructure:
    party: str  # "appellant" or "appellee"
    issues_presented: list[str] = field(default_factory=list)
    statement_of_case: str = ""
    arguments: list[Argument] = field(default_factory=list)
    conclusion: str = ""
    citations: list[Citation] = field(default_factory=list)


@dataclass
class OrderStructure:
    caption: str = ""
    holdings: list[str] = field(default_factory=list)
    findings_of_fact: str = ""
    conclusions_of_law: str = ""


@dataclass
class RecordCitation:
    raw_text: str
    record_number: int
    page: int | None = None
    paragraph: int | None = None


@dataclass
class CaseCitation:
    raw_text: str
    citation_type: str
    normalized: str


# Regex patterns for citation extraction
CITATION_PATTERNS = {
    "nd_case": re.compile(r"(\d{4})\s+ND\s+(\d+)"),
    "nw2d": re.compile(r"(\d+)\s+N\.W\.2d\s+(\d+)"),
    "ndcc": re.compile(r"N\.D\.C\.C\.\s*§\s*([\d\-\.]+(?:\([^)]*\))*)"),
    "nd_rule_app": re.compile(r"N\.D\.R\.App\.P\.\s*([\d.]+)"),
    "nd_rule_civ": re.compile(r"N\.D\.R\.Civ\.P\.\s*([\d.]+(?:\([^)]*\))*)"),
    "nd_rule_ev": re.compile(r"N\.D\.R\.Ev\.\s*([\d.]+)"),
    "record": re.compile(r"\(R(\d+)(?::(\d+))?(?::¶(\d+))?\)"),
    "paragraph": re.compile(r"¶\s*(\d+)"),
}


def extract_case_citations(text: str) -> list[CaseCitation]:
    """Extract all case citations from text."""
    citations = []
    for ctype, pattern in CITATION_PATTERNS.items():
        if ctype in ("record", "paragraph"):
            continue
        for match in pattern.finditer(text):
            citations.append(CaseCitation(
                raw_text=match.group(0),
                citation_type=ctype,
                normalized=match.group(0).strip(),
            ))
    return citations


def extract_record_citations(text: str) -> list[RecordCitation]:
    """Extract all record citations (R##, T##) from text."""
    citations = []
    for match in CITATION_PATTERNS["record"].finditer(text):
        citations.append(RecordCitation(
            raw_text=match.group(0),
            record_number=int(match.group(1)),
            page=int(match.group(2)) if match.group(2) else None,
            paragraph=int(match.group(3)) if match.group(3) else None,
        ))
    return citations


def parse_brief(text: str) -> BriefStructure:
    """Parse an appellate brief into structured components.

    Uses heuristics to find common sections. Actual detailed parsing
    is handled by Claude in the pipeline.
    """
    text_lower = text.lower()

    # Determine party
    party = "appellant"
    if "appellee" in text_lower[:2000] and "appellant" not in text_lower[:2000]:
        party = "appellee"
    elif "reply brief" in text_lower[:2000]:
        party = "appellant"  # reply briefs are from appellant

    # Extract issues presented (heuristic)
    issues = []
    issues_match = re.search(
        r"(?:ISSUES?\s+PRESENTED|STATEMENT\s+OF\s+(?:THE\s+)?ISSUES?)(.*?)(?:STATEMENT\s+OF|ARGUMENT|TABLE)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if issues_match:
        issues_text = issues_match.group(1)
        # Split on numbered items or "Whether"
        for line in re.split(r"\n\s*(?:\d+[\.\)]|[IVX]+[\.\)])\s*", issues_text):
            line = line.strip()
            if len(line) > 20:
                issues.append(line)

    citations = extract_case_citations(text)

    return BriefStructure(
        party=party,
        issues_presented=issues,
        citations=citations,
    )


def parse_order(text: str) -> OrderStructure:
    """Parse a district court order/judgment."""
    caption = ""
    caption_match = re.search(
        r"(.*?(?:ORDER|JUDGMENT|MEMORANDUM))",
        text[:3000],
        re.DOTALL | re.IGNORECASE,
    )
    if caption_match:
        caption = caption_match.group(1).strip()

    return OrderStructure(caption=caption)
