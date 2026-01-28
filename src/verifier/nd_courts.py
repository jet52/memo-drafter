"""ND Courts scraper for recent Supreme Court opinions."""

import asyncio
import logging
import re

import httpx

from src.utils.cache import get_cache
from src.verifier.courtlistener import VerificationResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ndcourts.gov"


class NDCourtsScraper:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache = get_cache("nd_courts", cache_dir)

    async def verify_citation(self, citation: str) -> VerificationResult:
        """Find an ND Supreme Court opinion by citation (e.g., '2024 ND 156')."""
        cached = self.cache.get(citation)
        if cached is not None:
            logger.debug("Cache hit (nd_courts) for %s", citation)
            return cached

        try:
            result = await self._search(citation)
            expire = None if result.exists else 86400
            self.cache.set(citation, result, expire=expire)
            return result
        except Exception as e:
            logger.warning("ND Courts error for %s: %s", citation, e)
            return VerificationResult(exists=False, error=str(e), source="nd_courts")

    async def _search(self, citation: str) -> VerificationResult:
        """Search ndcourts.gov for an opinion."""
        # Parse citation: "2024 ND 156" -> year=2024, num=156
        match = re.match(r"(\d{4})\s+ND\s+(\d+)", citation)
        if not match:
            return VerificationResult(exists=False, source="nd_courts")

        year = match.group(1)
        num = match.group(2)

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Try the opinions search page
            await asyncio.sleep(1)  # Rate limit: 1 req/sec
            response = await client.get(
                f"{BASE_URL}/supreme-court/opinions",
                params={"search": citation},
            )
            response.raise_for_status()
            html = response.text

            # Look for the citation in the results
            if citation in html:
                # Try to extract case name from surrounding context
                # Pattern: case name typically appears near the citation
                name_match = re.search(
                    rf'([A-Z][a-zA-Z\s.]+v\.\s+[A-Z][a-zA-Z\s.]+).*?{re.escape(citation)}',
                    html,
                )
                case_name = name_match.group(1).strip() if name_match else ""

                return VerificationResult(
                    exists=True,
                    case_name=case_name,
                    full_citation=citation,
                    url=f"{BASE_URL}/supreme-court/opinions?search={citation}",
                    source="nd_courts",
                )

            return VerificationResult(exists=False, source="nd_courts")
