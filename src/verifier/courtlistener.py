"""CourtListener API client for case law verification.

Requires an API key — get one free at https://www.courtlistener.com/sign-in/
"""

import logging
from dataclasses import dataclass

import httpx

from src.utils.cache import get_cache

logger = logging.getLogger(__name__)

BASE_URL = "https://www.courtlistener.com/api/rest/v4"


@dataclass
class VerificationResult:
    exists: bool
    case_name: str = ""
    full_citation: str = ""
    url: str = ""
    source: str = "courtlistener"
    error: str = ""


class CourtListenerClient:
    def __init__(self, api_key: str = "", cache_dir: str = "./cache"):
        # Strip comments and whitespace from key value
        self.api_key = api_key.split("#")[0].strip() if api_key else ""
        self.cache = get_cache("courtlistener", cache_dir)
        self.available = bool(self.api_key)
        if not self.api_key:
            logger.info("No CourtListener API key — skipping CourtListener verification")

    async def verify_citation(self, citation: str) -> VerificationResult:
        """Verify a case citation exists and return details."""
        if not self.available:
            return VerificationResult(exists=False, error="No API key", source="courtlistener")

        cached = self.cache.get(citation)
        if cached is not None:
            logger.debug("Cache hit for %s", citation)
            return cached

        try:
            result = await self._search_citation(citation)
            expire = None if result.exists else 86400
            self.cache.set(citation, result, expire=expire)
            return result
        except Exception as e:
            logger.warning("CourtListener error for %s: %s", citation, e)
            return VerificationResult(exists=False, error=str(e), source="courtlistener")

    async def _search_citation(self, citation: str) -> VerificationResult:
        """Search CourtListener for a citation."""
        headers = {"Authorization": f"Token {self.api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{BASE_URL}/search/",
                params={"q": f'"{citation}"', "type": "o"},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                hit = results[0]
                return VerificationResult(
                    exists=True,
                    case_name=hit.get("caseName", ""),
                    full_citation=citation,
                    url=f"https://www.courtlistener.com{hit.get('absolute_url', '')}",
                    source="courtlistener",
                )

            return VerificationResult(exists=False, source="courtlistener")
