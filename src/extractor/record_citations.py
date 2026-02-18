"""Extract record citation numbers from appellate brief text.

Parses references like (R45), R45:12, R. 123, Rec 123, Idx 123
and returns deduplicated record index numbers for selective fetching.
"""

# TODO: Multi-case-number citations (e.g. "54-2020-CV-00012 R19:2") —
# currently we extract only the record index number, ignoring any
# preceding docket number. Future work should associate citations
# with their originating case.

import re
from datetime import date

# ---------------------------------------------------------------------------
# Regex building blocks
# ---------------------------------------------------------------------------

# Prefixes that introduce a record citation
_PAREN_PREFIX = r"[Rr](?:ec)?\.?\s*:?\s*|[Ii]dx\.?\s*"

# A single record number (captured)
_NUM = r"(\d+)"

# Interior of a parenthesized group: numbers, colons, paragraph marks, commas,
# hyphens, R-prefixes, and whitespace
_PAREN_INTERIOR = r"[^)]*"

# ---------------------------------------------------------------------------
# Phase 1 — Parenthesized groups  e.g. (R45), (R45:12), (R45-R52), (R12, R14)
# ---------------------------------------------------------------------------

_RE_PAREN_GROUP = re.compile(
    r"\(\s*(?:R|Rec\.?|Idx\.?)\s*:?\s*" + _PAREN_INTERIOR + r"\)",
    re.IGNORECASE,
)

# Inside a paren group, pull out individual numbers and ranges
_RE_INNER_RANGE = re.compile(
    r"(\d+)\s*[-–—]\s*(?:[Rr](?:ec)?\.?\s*:?\s*|[Ii]dx\.?\s*)?(\d+)"
)
_RE_INNER_NUM = re.compile(r"(\d+)")

# ---------------------------------------------------------------------------
# Phase 2 — Bare references  e.g. R45, R. 123, Rec 123, Idx. 45
# ---------------------------------------------------------------------------

# Negative lookbehind prevents matching the R in things like "N.D.R.Civ.P."
_RE_BARE = re.compile(
    r"(?<![A-Za-z.])(?:R|Rec|Idx)\.?\s*:?\s*(\d+)"
    r"(?:\s*[-–—]\s*(?:R(?:ec)?\.?\s*:?\s*|Idx\.?\s*)?(\d+))?",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Case number detection
# ---------------------------------------------------------------------------

_RE_CASE_NUMBER = re.compile(
    r"(?:Case\s+(?:No\.?|Number)\s*:?\s*|No\.\s*)"
    r"(\d{8}|\d{2}-\d{4}-[A-Z]{2,4}-\d+)",
    re.IGNORECASE,
)

_RE_DOCKET_NUMBER = re.compile(r"\b(20\d{6})\b")

# Range expansion cap to guard against OCR errors
_MAX_RANGE_SIZE = 1000


def _expand_range(start: int, end: int) -> set[int]:
    """Expand a numeric range, returning individual items if end < start."""
    if end < start:
        return {start, end}
    if end - start + 1 > _MAX_RANGE_SIZE:
        return {start, end}
    return set(range(start, end + 1))


_RE_STRIP_PREFIX = re.compile(
    r"^\s*(?:R|Rec\.?|Idx\.?)\s*:?\s*", re.IGNORECASE
)


def _extract_from_paren_group(group_text: str) -> set[int]:
    """Extract all record numbers from the interior of a parenthesized group.

    Handles colon-separated sub-references: in (R45:12:¶3) only 45 is the
    record index — 12 and ¶3 are page/paragraph sub-references.
    """
    numbers: set[int] = set()

    # Strip outer parens
    interior = group_text.strip()
    if interior.startswith("("):
        interior = interior[1:]
    if interior.endswith(")"):
        interior = interior[:-1]

    # Split on commas to handle lists like "R12, R14, R16" or "R12, 14, 16"
    segments = interior.split(",")

    for segment in segments:
        segment = segment.strip()
        # Strip any leading prefix (R, Rec, Idx, etc.)
        segment = _RE_STRIP_PREFIX.sub("", segment)

        # Check for range pattern: num - [optional prefix] num
        range_match = _RE_INNER_RANGE.match(segment)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            numbers |= _expand_range(start, end)
            continue

        # Otherwise, take only the first number (before any colon)
        # This ensures (R45:12:¶3) yields only 45
        first_part = segment.split(":")[0].strip()
        num_match = _RE_INNER_NUM.search(first_part)
        if num_match:
            numbers.add(int(num_match.group(1)))

    return numbers


def extract_record_numbers(text: str) -> set[int]:
    """Return a deduplicated set of record index numbers from brief text."""
    numbers: set[int] = set()

    # Track spans consumed by Phase 1 so Phase 2 doesn't double-count
    consumed_spans: list[tuple[int, int]] = []

    # Phase 1: parenthesized groups
    for m in _RE_PAREN_GROUP.finditer(text):
        numbers |= _extract_from_paren_group(m.group(0))
        consumed_spans.append((m.start(), m.end()))

    # Phase 2: bare references
    for m in _RE_BARE.finditer(text):
        pos = m.start()
        if any(s <= pos < e for s, e in consumed_spans):
            continue
        start_num = int(m.group(1))
        end_num = m.group(2)
        if end_num is not None:
            numbers |= _expand_range(start_num, int(end_num))
        else:
            numbers.add(start_num)

    return numbers


def detect_case_number(text: str) -> str:
    """Best-effort extraction of docket number from brief text."""
    m = _RE_CASE_NUMBER.search(text)
    if m:
        return m.group(1)
    m = _RE_DOCKET_NUMBER.search(text)
    if m:
        return m.group(1)
    return ""


def format_items_file(
    record_numbers: set[int],
    source_files: list[str],
    case_number: str = "",
) -> str:
    """Produce items file content with a comment header and sorted R-numbers."""
    lines = [
        "# Record citations extracted from briefs",
    ]
    if case_number:
        lines.append(f"# Case: {case_number}")
    lines.append(f"# Source: {', '.join(source_files)}")
    lines.append(f"# Date: {date.today().isoformat()}")
    lines.append(f"# Total unique items: {len(record_numbers)}")

    for num in sorted(record_numbers):
        lines.append(f"R{num}")

    return "\n".join(lines) + "\n"
