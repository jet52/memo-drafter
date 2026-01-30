"""CourtListener API client for case law verification.

Requires an API key — get one free at https://www.courtlistener.com/sign-in/
Uses the citation-lookup endpoint for fast, accurate lookups.
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
            result = await self._lookup_citation(citation)
            expire = None if result.exists else 86400
            self.cache.set(citation, result, expire=expire)
            return result
        except httpx.HTTPStatusError as e:
            logger.warning("CourtListener HTTP %s for %s: %s", e.response.status_code, citation, e.response.text[:200])
            return VerificationResult(exists=False, error=f"HTTP {e.response.status_code}", source="courtlistener")
        except Exception as e:
            logger.warning("CourtListener error for %s: %s (%s)", citation, e, type(e).__name__)
            return VerificationResult(exists=False, error=str(e), source="courtlistener")

    async def _lookup_citation(self, citation: str) -> VerificationResult:
        """Look up a citation using the citation-lookup endpoint."""
        headers = {"Authorization": f"Token {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{BASE_URL}/citation-lookup/",
                json={"text": citation},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            # Response is a list of citation match objects
            for match in data:
                if match.get("citation") == citation and match.get("clusters"):
                    cluster = match["clusters"][0]
                    return VerificationResult(
                        exists=True,
                        case_name=cluster.get("case_name", ""),
                        full_citation=citation,
                        url=f"https://www.courtlistener.com{cluster.get('absolute_url', '')}",
                        source="courtlistener",
                    )

            return VerificationResult(exists=False, source="courtlistener")
