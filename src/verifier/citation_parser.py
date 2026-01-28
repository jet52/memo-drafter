"""Extract and normalize citations from generated memo text."""

import re
from dataclasses import dataclass


@dataclass
class Citation:
    raw_text: str
    citation_type: str  # 'nd_case', 'nw2d', 'ndcc', 'nd_rule', 'us_case', 'record', 'paragraph'
    normalized: str
    context: str  # surrounding text
    line_number: int


# Patterns ordered for extraction (non-overlapping)
PATTERNS: dict[str, re.Pattern] = {
    "nd_case": re.compile(r"(\d{4})\s+ND\s+(\d+)"),
    "nw2d": re.compile(r"(\d+)\s+N\.W\.2d\s+(\d+)"),
    "us_case": re.compile(r"(\d+)\s+U\.S\.\s+(\d+)"),
    "ndcc": re.compile(r"N\.D\.C\.C\.\s*§\s*([\d\-\.]+(?:\([^)]*\))*)"),
    "nd_rule_app": re.compile(r"N\.D\.R\.App\.P\.\s*([\d.]+)"),
    "nd_rule_civ": re.compile(r"N\.D\.R\.Civ\.P\.\s*([\d.]+(?:\([^)]*\))*)"),
    "nd_rule_ev": re.compile(r"N\.D\.R\.Ev\.\s*([\d.]+)"),
    "record": re.compile(r"\(R(\d+)(?::(\d+))?(?::¶(\d+))?\)"),
}


def parse_citations(text: str) -> list[Citation]:
    """Extract all citations from memo text."""
    citations = []
    lines = text.split("\n")

    for line_num, line in enumerate(lines, start=1):
        for ctype, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                # Get surrounding context (up to 80 chars each side)
                start = max(0, match.start() - 80)
                end = min(len(line), match.end() + 80)
                context = line[start:end]

                citations.append(Citation(
                    raw_text=match.group(0),
                    citation_type=ctype,
                    normalized=_normalize(ctype, match),
                    context=context,
                    line_number=line_num,
                ))
    return citations


def _normalize(ctype: str, match: re.Match) -> str:
    """Normalize a citation for lookup."""
    if ctype == "nd_case":
        return f"{match.group(1)} ND {match.group(2)}"
    elif ctype == "nw2d":
        return f"{match.group(1)} N.W.2d {match.group(2)}"
    elif ctype == "us_case":
        return f"{match.group(1)} U.S. {match.group(2)}"
    elif ctype == "ndcc":
        return match.group(1)
    elif ctype.startswith("nd_rule"):
        return match.group(0).strip()
    elif ctype == "record":
        parts = [match.group(1)]
        if match.group(2):
            parts.append(match.group(2))
        if match.group(3):
            parts.append(f"¶{match.group(3)}")
        return ":".join(parts)
    return match.group(0).strip()


def extract_unique_case_citations(text: str) -> list[Citation]:
    """Extract unique case citations (nd_case, nw2d, us_case) for verification."""
    all_cites = parse_citations(text)
    seen = set()
    unique = []
    for cite in all_cites:
        if cite.citation_type in ("nd_case", "nw2d", "us_case"):
            if cite.normalized not in seen:
                seen.add(cite.normalized)
                unique.append(cite)
    return unique


def extract_unique_statute_citations(text: str) -> list[Citation]:
    """Extract unique statute citations for verification."""
    all_cites = parse_citations(text)
    seen = set()
    unique = []
    for cite in all_cites:
        if cite.citation_type == "ndcc":
            if cite.normalized not in seen:
                seen.add(cite.normalized)
                unique.append(cite)
    return unique
