"""Multi-step memo generation pipeline."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from config.style_specification import STYLE_SPEC
from src.generator.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


@dataclass
class CaseDocuments:
    """All documents for a case, keyed by filename."""
    texts: dict[str, str]  # filename -> extracted text
    types: dict[str, str]  # filename -> document type
    folder: Path | None = None


@dataclass
class GeneratedMemo:
    memo_text: str
    analysis: dict
    framing: dict
    key_docs: str


def _load_prompt(name: str) -> str:
    from src.bundle_paths import get_config_path
    return get_config_path("prompts", name).read_text()


def _build_system_prompt() -> str:
    template = _load_prompt("system_prompt.txt")
    return template.format(style_spec=STYLE_SPEC)


class MemoPipeline:
    def __init__(self, client: ClaudeClient, enable_self_review: bool = False,
                 progress_callback=None):
        self.client = client
        self.system_prompt = _build_system_prompt()
        self.enable_self_review = enable_self_review
        self._progress = progress_callback or (lambda msg: None)

    async def generate(self, case: CaseDocuments) -> GeneratedMemo:
        """Run the full generation pipeline."""
        # Stage 1: Document Analysis
        self._progress("Stage 1/4: Analyzing documents...")
        analysis = await self._analyze_documents(case)
        num_issues = len(analysis.get("issues_on_appeal", []))
        logger.info("Stage 1 complete: found %d issues", num_issues)

        # Stage 2: Legal Framing
        self._progress("Stage 2/4: Framing legal issues...")
        framing = await self._frame_legal_issues(analysis, case)

        # Stage 3: Key Documents
        self._progress("Stage 3/4: Selecting key documents...")
        key_docs = await self._select_key_documents(analysis, case)

        # Stage 4: Memo Generation
        self._progress("Stage 4/4: Generating memo...")
        memo_text = await self._generate_memo(analysis, framing, key_docs)

        # Stage 5: Self-Review (optional)
        if self.enable_self_review:
            self._progress("Self-review: Checking memo quality...")
            memo_text = await self._self_review(memo_text, analysis)

        return GeneratedMemo(
            memo_text=memo_text,
            analysis=analysis,
            framing=framing,
            key_docs=key_docs,
        )

    async def _analyze_documents(self, case: CaseDocuments) -> dict:
        """Stage 1: Extract structured case information."""
        template = _load_prompt("document_analysis.txt")

        doc_list = "\n".join(
            f"- {fname} ({dtype})" for fname, dtype in case.types.items()
        )
        doc_contents = "\n\n".join(
            f"=== {fname} ({case.types.get(fname, 'unknown')}) ===\n{text}"
            for fname, text in case.texts.items()
        )

        prompt = template.format(document_list=doc_list, document_contents=doc_contents)
        response = await self.client.generate(
            self.system_prompt, prompt, max_tokens=4096, temperature=0.2
        )
        return _parse_json_response(response)

    async def _frame_legal_issues(self, analysis: dict, case: CaseDocuments) -> dict:
        """Stage 2: Identify standards of review and arguments per issue."""
        template = _load_prompt("issue_identification.txt")

        # Include brief excerpts for context
        brief_excerpts = ""
        for fname, text in case.texts.items():
            dtype = case.types.get(fname, "")
            if "brief" in dtype:
                # Include full brief text (Claude can handle large contexts)
                brief_excerpts += f"\n=== {fname} ===\n{text}\n"

        prompt = template.format(
            analysis_json=json.dumps(analysis, indent=2),
            brief_excerpts=brief_excerpts,
        )
        response = await self.client.generate(
            self.system_prompt, prompt, max_tokens=8192, temperature=0.2
        )
        return _parse_json_response(response)

    async def _select_key_documents(self, analysis: dict, case: CaseDocuments) -> str:
        """Stage 3: Select 4-8 key documents for Quick Reference."""
        prompt = (
            "Based on the following case analysis, select 4-8 key documents for the "
            "Quick Reference section of the bench memo. For each document, provide a brief "
            "description and record citation.\n\n"
            f"CASE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\n"
            f"AVAILABLE DOCUMENTS:\n"
            + "\n".join(f"- {fname} ({dtype})" for fname, dtype in case.types.items())
            + "\n\nFormat as a markdown list suitable for the Quick Reference section."
        )
        return await self.client.generate(
            self.system_prompt, prompt, max_tokens=2048, temperature=0.2
        )

    async def _generate_memo(self, analysis: dict, framing: dict, key_docs: str) -> str:
        """Stage 4: Generate the complete bench memo."""
        template = _load_prompt("memo_generation.txt")
        prompt = template.format(
            analysis_json=json.dumps(analysis, indent=2),
            framing_json=json.dumps(framing, indent=2),
            key_docs=key_docs,
        )
        return await self.client.generate(
            self.system_prompt, prompt, max_tokens=16384, temperature=0.3
        )

    async def _self_review(self, memo_text: str, analysis: dict) -> str:
        """Stage 5: Have Claude review and optionally revise the memo."""
        template = _load_prompt("verification.txt")
        prompt = template.format(
            memo_text=memo_text,
            analysis_json=json.dumps(analysis, indent=2),
        )
        response = await self.client.generate(
            self.system_prompt, prompt, max_tokens=8192, temperature=0.2
        )
        result = _parse_json_response(response)
        if result.get("overall_quality") == "needs_revision" and result.get("revised_memo"):
            logger.info("Self-review found issues, using revised memo")
            return result["revised_memo"]
        return memo_text


def _parse_json_response(text: str) -> dict:
    """Extract JSON from a Claude response that may contain markdown fences."""
    # Strip markdown code fences
    text = text.strip()
    if text.startswith("```"):
        # Remove first and last lines
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        logger.error("Failed to parse JSON from response: %s...", text[:200])
        return {}
