"""ND Legislature scraper for Century Code verification."""

import asyncio
import logging
import re

import httpx

from src.utils.cache import get_cache
from src.verifier.courtlistener import VerificationResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ndlegis.gov/cencode"


class NDStatutesScraper:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache = get_cache("nd_statutes", cache_dir)

    async def verify_statute(self, section: str) -> VerificationResult:
        """
        Verify N.D.C.C. section exists.

        Args:
            section: e.g., "14-09-06.2" or "14-09-06.2(1)(a)"
        """
        cached = self.cache.get(section)
        if cached is not None:
            logger.debug("Cache hit (nd_statutes) for %s", section)
            return cached

        try:
            result = await self._lookup(section)
            expire = None if result.exists else 86400
            self.cache.set(section, result, expire=expire)
            return result
        except Exception as e:
            logger.warning("ND Statutes error for %s: %s", section, e)
            return VerificationResult(exists=False, error=str(e), source="nd_statutes")

    async def _lookup(self, section: str) -> VerificationResult:
        """Look up a statute section on ndlegis.gov."""
        # Strip subsection for URL lookup: "14-09-06.2(1)(a)" -> "14-09-06.2"
        base_section = re.sub(r"\(.*\)", "", section).strip()

        # Parse title and chapter: "14-09-06.2" -> title=14, chapter=09
        parts = base_section.split("-")
        if len(parts) < 2:
            return VerificationResult(exists=False, source="nd_statutes")

        title = parts[0]
        chapter = parts[1] if len(parts) > 1 else ""

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            await asyncio.sleep(1)  # Rate limit
            # Try direct URL pattern
            url = f"{BASE_URL}/t{title.zfill(2)}c{chapter.zfill(2)}.html"
            response = await client.get(url)

            if response.status_code == 200:
                html = response.text
                # Check if the specific section appears in the chapter page
                if base_section in html:
                    return VerificationResult(
                        exists=True,
                        case_name=f"N.D.C.C. § {section}",
                        full_citation=f"N.D.C.C. § {section}",
                        url=url,
                        source="nd_statutes",
                    )

            # Fallback: search the site
            await asyncio.sleep(1)
            response = await client.get(
                "https://www.ndlegis.gov/search",
                params={"q": f"N.D.C.C. {base_section}"},
            )
            if response.status_code == 200 and base_section in response.text:
                return VerificationResult(
                    exists=True,
                    case_name=f"N.D.C.C. § {section}",
                    full_citation=f"N.D.C.C. § {section}",
                    url=f"https://www.ndlegis.gov/search?q=N.D.C.C.+{base_section}",
                    source="nd_statutes",
                )

            return VerificationResult(exists=False, source="nd_statutes")
