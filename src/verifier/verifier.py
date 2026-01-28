"""Verification orchestrator — coordinate all verification sources."""

import logging
from dataclasses import dataclass, field

from src.verifier.citation_parser import (
    Citation,
    extract_unique_case_citations,
    extract_unique_statute_citations,
    parse_citations,
)
from src.verifier.courtlistener import CourtListenerClient, VerificationResult
from src.verifier.local_opinions import LocalOpinionLookup
from src.verifier.nd_courts import NDCourtsScraper
from src.verifier.nd_statutes import NDStatutesScraper

logger = logging.getLogger(__name__)


@dataclass
class VerificationReport:
    verified: list[tuple[Citation, VerificationResult]] = field(default_factory=list)
    unverified: list[tuple[Citation, VerificationResult]] = field(default_factory=list)
    skipped: list[Citation] = field(default_factory=list)  # record cites, rules — not verifiable online
    total_checked: int = 0

    @property
    def summary(self) -> str:
        v = len(self.verified)
        u = len(self.unverified)
        s = len(self.skipped)
        return (
            f"Verified: {v} | Unverified: {u} | Skipped: {s} | Total: {self.total_checked}"
        )


class CitationVerifier:
    def __init__(
        self,
        courtlistener_api_key: str = "",
        court_data_dir: str = "",
        cache_dir: str = "./cache",
        progress_callback=None,
    ):
        self.local = LocalOpinionLookup(court_data_dir)
        self.cl = CourtListenerClient(api_key=courtlistener_api_key, cache_dir=cache_dir)
        self.nd_courts = NDCourtsScraper(cache_dir=cache_dir)
        self.nd_statutes = NDStatutesScraper(cache_dir=cache_dir)
        self._progress = progress_callback or (lambda msg: None)

    async def verify_memo(self, memo_text: str) -> VerificationReport:
        """Verify all citations in a memo."""
        report = VerificationReport()

        # 1. Case citations
        case_cites = extract_unique_case_citations(memo_text)
        self._progress(f"Verifying {len(case_cites)} case citations...")
        for i, cite in enumerate(case_cites, 1):
            self._progress(f"Verifying case {i}/{len(case_cites)}: {cite.normalized}")
            report.total_checked += 1
            result = await self._verify_case(cite)
            if result.exists:
                report.verified.append((cite, result))
            else:
                report.unverified.append((cite, result))

        # 2. Statute citations
        statute_cites = extract_unique_statute_citations(memo_text)
        if statute_cites:
            self._progress(f"Verifying {len(statute_cites)} statute citations...")
            for cite in statute_cites:
                report.total_checked += 1
                result = await self.nd_statutes.verify_statute(cite.normalized)
                if result.exists:
                    report.verified.append((cite, result))
                else:
                    report.unverified.append((cite, result))

        # 3. Record citations and rules — skip (can't verify online)
        all_cites = parse_citations(memo_text)
        for cite in all_cites:
            if cite.citation_type in ("record", "nd_rule_app", "nd_rule_civ", "nd_rule_ev"):
                report.skipped.append(cite)

        logger.info("Verification complete: %s", report.summary)
        return report

    async def _verify_case(self, cite: Citation) -> VerificationResult:
        """Verify a case citation with fallback chain.

        Chain: Local data (instant) → CourtListener (if API key) → ND Courts scraper.
        """
        is_nd = cite.citation_type == "nd_case"

        # 1. Local opinion data (fastest — file lookup, ND cases only)
        if is_nd and self.local.available:
            result = await self.local.verify_citation(cite.normalized)
            if result.exists:
                return result

        # 2. CourtListener (requires API key)
        if self.cl.available:
            result = await self.cl.verify_citation(cite.normalized)
            if result.exists:
                return result

        # 3. ND Courts scraper (free, ND cases only)
        if is_nd:
            result = await self.nd_courts.verify_citation(cite.normalized)
            if result.exists:
                return result

        # Not found
        sources = []
        if is_nd and self.local.available:
            sources.append("local data")
        if self.cl.available:
            sources.append("CourtListener")
        if is_nd:
            sources.append("ND Courts")
        if not sources:
            error = "No verification sources available (set COURTLISTENER_API_KEY or COURT_DATA)"
        else:
            error = f"Not found in {', '.join(sources)}"

        return VerificationResult(
            exists=False,
            full_citation=cite.normalized,
            source="none",
            error=error,
        )
