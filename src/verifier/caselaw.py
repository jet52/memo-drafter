"""Harvard Case.law API client — backup case verification."""

import logging
from dataclasses import dataclass

import httpx

from src.utils.cache import get_cache
from src.verifier.courtlistener import VerificationResult

logger = logging.getLogger(__name__)

BASE_URL = "https://api.case.law/v1"


class CaseLawClient:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache = get_cache("caselaw", cache_dir)

    async def verify_citation(self, citation: str) -> VerificationResult:
        """Verify via Case.law API (backup to CourtListener)."""
        cached = self.cache.get(citation)
        if cached is not None:
            logger.debug("Cache hit (caselaw) for %s", citation)
            return cached

        try:
            result = await self._search(citation)
            expire = None if result.exists else 86400
            self.cache.set(citation, result, expire=expire)
            return result
        except Exception as e:
            logger.warning("Case.law error for %s: %s", citation, e)
            return VerificationResult(exists=False, error=str(e), source="caselaw")

    async def _search(self, citation: str) -> VerificationResult:
        """Search Case.law for a citation."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{BASE_URL}/cases/",
                params={
                    "cite": citation,
                    "jurisdiction": "nd",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                hit = results[0]
                return VerificationResult(
                    exists=True,
                    case_name=hit.get("name_abbreviation", ""),
                    full_citation=hit.get("citations", [{}])[0].get("cite", citation) if hit.get("citations") else citation,
                    url=hit.get("frontend_url", ""),
                    source="caselaw",
                )

            return VerificationResult(exists=False, source="caselaw")
