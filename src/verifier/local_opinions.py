"""Local opinion lookup from downloaded ND Supreme Court opinions.

Searches markdown files in COURT_DATA/markdown/{year}/{year}ND{number}.md
"""

import logging
import re
from pathlib import Path

from src.verifier.courtlistener import VerificationResult

logger = logging.getLogger(__name__)


class LocalOpinionLookup:
    def __init__(self, court_data_dir: str):
        self.data_dir = Path(court_data_dir) if court_data_dir else None
        self.markdown_dir = self.data_dir / "markdown" if self.data_dir else None
        self.available = bool(
            self.markdown_dir and self.markdown_dir.is_dir()
        )
        if not self.available:
            logger.info("Local opinions not available (COURT_DATA not set or markdown/ not found)")

    async def verify_citation(self, citation: str) -> VerificationResult:
        """Look up an ND case citation in local markdown files."""
        if not self.available:
            return VerificationResult(exists=False, error="Local data not configured", source="local")

        # Parse "2024 ND 156" -> year=2024, num=156
        match = re.match(r"(\d{4})\s+ND\s+(\d+)", citation)
        if not match:
            return VerificationResult(exists=False, error="Not an ND citation", source="local")

        year = match.group(1)
        num = match.group(2)
        filename = f"{year}ND{num}.md"
        filepath = self.markdown_dir / year / filename

        if filepath.is_file():
            # Extract case name from the first ~20 lines
            case_name = self._extract_case_name(filepath)
            return VerificationResult(
                exists=True,
                case_name=case_name,
                full_citation=citation,
                url=str(filepath),
                source="local",
            )

        return VerificationResult(exists=False, error="Not found in local data", source="local")

    def _extract_case_name(self, filepath: Path) -> str:
        """Extract case name (Party v. Party) from opinion markdown."""
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")[:2000]
            # Look for "X v. Y" pattern
            match = re.search(
                r"([A-Z][A-Za-z.\-\s]+?)\s*(?:,\s*\n)?\s*v\.\s*\n?\s*([A-Z][A-Za-z.\-\s]+?)(?:\s*\n|,)",
                text,
            )
            if match:
                plaintiff = match.group(1).strip().split("\n")[-1].strip()
                defendant = match.group(2).strip().split("\n")[0].strip()
                return f"{plaintiff} v. {defendant}"
        except Exception as e:
            logger.debug("Could not extract case name from %s: %s", filepath.name, e)
        return ""

    def get_opinion_text(self, citation: str) -> str | None:
        """Get full opinion text for a verified citation."""
        match = re.match(r"(\d{4})\s+ND\s+(\d+)", citation)
        if not match or not self.available:
            return None

        year = match.group(1)
        num = match.group(2)
        filepath = self.markdown_dir / year / f"{year}ND{num}.md"

        if filepath.is_file():
            return filepath.read_text(encoding="utf-8", errors="replace")
        return None
