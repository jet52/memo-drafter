# Bench Memo Generator: Detailed Implementation Guide

This document expands the project plan into specific implementation steps, technical decisions, and code architecture.

---

## Phase 1: Prototype (Weeks 1-3)

### 1.1 Project Setup

**Directory structure:**
```
bench_memo_generator/
├── pyproject.toml              # Project metadata, dependencies
├── README.md
├── .env.example                # Template for API keys
├── config/
│   ├── __init__.py
│   ├── settings.py             # Configuration management
│   ├── style_specification.py  # Style spec as Python constants
│   └── prompts/
│       ├── __init__.py
│       ├── system_prompt.txt   # Base system prompt with style spec
│       ├── document_analysis.txt
│       ├── issue_identification.txt
│       ├── memo_generation.txt
│       └── verification.txt
├── src/
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── extractor/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py    # PDF text extraction
│   │   └── document_parser.py  # Structure extraction from text
│   ├── classifier/
│   │   ├── __init__.py
│   │   └── document_classifier.py  # Identify document types
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── memo_generator.py   # Main orchestration
│   │   ├── claude_client.py    # Claude API wrapper
│   │   └── pipeline.py         # Multi-step generation pipeline
│   ├── verifier/
│   │   ├── __init__.py
│   │   ├── citation_parser.py  # Extract citations from text
│   │   ├── courtlistener.py    # CourtListener API client
│   │   ├── caselaw.py          # Harvard Case.law API client
│   │   ├── nd_courts.py        # ND Courts scraper
│   │   ├── nd_statutes.py      # ND Legislature scraper
│   │   └── verifier.py         # Orchestrate verification
│   ├── output/
│   │   ├── __init__.py
│   │   ├── markdown_writer.py  # Generate markdown output
│   │   └── appendix.py         # Generate verification appendix
│   └── utils/
│       ├── __init__.py
│       ├── cache.py            # Local caching for API responses
│       └── logging.py          # Minimal logging setup
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── test_extractor.py
    ├── test_classifier.py
    ├── test_generator.py
    └── fixtures/
        └── sample_briefs/      # Test PDFs
```

**Dependencies (pyproject.toml):**
```toml
[project]
name = "bench-memo-generator"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40.0",        # Claude API
    "pdfminer.six>=20231228",   # PDF extraction
    "click>=8.1.0",             # CLI framework
    "httpx>=0.27.0",            # Async HTTP client
    "python-dotenv>=1.0.0",     # Environment variables
    "diskcache>=5.6.0",         # Local caching
    "rich>=13.0.0",             # Terminal formatting/progress
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

### 1.2 PDF Extraction Module

**File: `src/extractor/pdf_extractor.py`**

**Purpose:** Extract text from appellate briefs and supporting documents.

**Key functions:**
```python
def extract_text(pdf_path: Path) -> str:
    """Extract all text from a PDF using pdfminer.six."""

def extract_with_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text with page numbers for record citation mapping."""

def extract_metadata(pdf_path: Path) -> dict:
    """Extract PDF metadata (title, author, creation date)."""
```

**Implementation notes:**
- Use `pdfminer.six` with `LAParams` tuned for legal documents (tight line margins)
- Handle scanned PDFs gracefully (detect low text extraction, warn user)
- Preserve paragraph breaks for structure analysis
- Target: Process a 50-page brief in <5 seconds

---

### 1.3 Document Parser

**File: `src/extractor/document_parser.py`**

**Purpose:** Extract structure from raw text (headings, arguments, citations).

**Key functions:**
```python
def parse_brief(text: str) -> BriefStructure:
    """Parse an appellate brief into structured components."""
    # Returns: issues_presented, statement_of_case, arguments, conclusion

def parse_order(text: str) -> OrderStructure:
    """Parse a district court order/judgment."""
    # Returns: caption, holdings, findings_of_fact, conclusions_of_law

def extract_record_citations(text: str) -> list[RecordCitation]:
    """Extract all record citations (R##, T##) from text."""

def extract_case_citations(text: str) -> list[CaseCitation]:
    """Extract all case citations from text."""
```

**Data classes:**
```python
@dataclass
class BriefStructure:
    party: str  # "appellant" or "appellee"
    issues_presented: list[str]
    statement_of_case: str
    arguments: list[Argument]
    conclusion: str
    citations: list[Citation]

@dataclass
class Argument:
    heading: str
    text: str
    citations: list[Citation]
```

---

### 1.4 Document Classifier

**File: `src/classifier/document_classifier.py`**

**Purpose:** Identify document type from filename and content.

**Classification categories:**
```python
class DocumentType(Enum):
    APPELLANT_BRIEF = "appellant_brief"
    APPELLEE_BRIEF = "appellee_brief"
    REPLY_BRIEF = "reply_brief"
    DISTRICT_COURT_ORDER = "order"
    JUDGMENT = "judgment"
    FINDINGS_CONCLUSIONS = "findings"
    NOTICE_OF_APPEAL = "notice"
    TRANSCRIPT = "transcript"
    EXHIBIT = "exhibit"
    OTHER = "other"
```

**Classification logic:**
1. **Filename patterns:** "Appellant" → APPELLANT_BRIEF, "Order" → ORDER
2. **Content analysis:** Look for "APPELLANT'S BRIEF", "APPELLEE'S BRIEF", "ORDER FOR JUDGMENT"
3. **Fallback:** Use Claude to classify ambiguous documents (short prompt, cheap)

---

### 1.5 Claude API Client

**File: `src/generator/claude_client.py`**

**Purpose:** Wrap Anthropic SDK with retry logic and token tracking.

**Key functions:**
```python
class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> str:
        """Generate a response with automatic retry on rate limits."""

    def estimate_cost(self) -> float:
        """Estimate cost based on token usage."""
```

**Configuration:**
- Default model: `claude-sonnet-4-20250514` (good balance of quality/cost)
- Temperature: 0.3 (focused, consistent output)
- Max tokens: 8192 for memo generation, 2048 for classification tasks

---

### 1.6 Generation Pipeline

**File: `src/generator/pipeline.py`**

**Purpose:** Orchestrate multi-step memo generation.

**Pipeline stages:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    GENERATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Stage 1: DOCUMENT ANALYSIS                                     │
│  ──────────────────────────                                     │
│  Input:  Raw text from all documents                            │
│  Prompt: "Analyze these appellate documents and extract..."     │
│  Output: JSON with:                                             │
│          - case_number, case_name, parties                      │
│          - procedural_posture                                   │
│          - issues_on_appeal (list)                              │
│          - key_facts (list)                                     │
│          - key_documents (with record citations)                │
│                                                                 │
│  Stage 2: LEGAL FRAMING                                         │
│  ──────────────────────                                         │
│  Input:  Stage 1 output + brief excerpts                        │
│  Prompt: "For each issue, identify the standard of review..."   │
│  Output: JSON with per-issue:                                   │
│          - standard_of_review                                   │
│          - appellant_arguments (summarized)                     │
│          - appellee_arguments (summarized)                      │
│          - applicable_precedent (from briefs)                   │
│          - preliminary_assessment                               │
│                                                                 │
│  Stage 3: IMPORTANT DOCUMENTS SECTION                           │
│  ────────────────────────────────────                           │
│  Input:  Stage 1 key_documents + full document list             │
│  Prompt: "Select 4-8 key documents for Quick Reference..."      │
│  Output: Formatted Quick Reference section                      │
│                                                                 │
│  Stage 4: MEMO GENERATION                                       │
│  ────────────────────────                                       │
│  Input:  Stages 1-3 outputs + style specification               │
│  Prompt: "Generate a complete bench memo following this spec.." │
│  Output: Full markdown memo                                     │
│                                                                 │
│  Stage 5: SELF-REVIEW (Optional)                                │
│  ───────────────────────────────                                │
│  Input:  Stage 4 memo                                           │
│  Prompt: "Review this memo for: missing issues, citation        │
│           format errors, structural problems..."                │
│  Output: Revised memo or list of issues                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
class MemoPipeline:
    def __init__(self, client: ClaudeClient, style_spec: str):
        self.client = client
        self.style_spec = style_spec

    async def generate(self, case: CaseDocuments) -> GeneratedMemo:
        # Stage 1
        analysis = await self._analyze_documents(case)

        # Stage 2
        framing = await self._frame_legal_issues(analysis, case)

        # Stage 3
        key_docs = await self._select_key_documents(analysis, case)

        # Stage 4
        memo = await self._generate_memo(analysis, framing, key_docs)

        # Stage 5 (optional)
        if self.enable_self_review:
            memo = await self._self_review(memo)

        return memo
```

---

### 1.7 Prompt Design

**System prompt structure:**

```
You are a legal research assistant helping prepare bench memos for the
North Dakota Supreme Court. You will generate memos following the exact
style and format used by Central Legal Staff.

## STYLE SPECIFICATION
[Full style specification embedded here - ~3,000 tokens]

## YOUR TASK
[Stage-specific instructions]

## OUTPUT FORMAT
[JSON schema or markdown template]
```

**Stage 1 prompt (Document Analysis):**
```
Analyze the following appellate case documents and extract structured information.

DOCUMENTS PROVIDED:
- Appellant's Brief
- Appellee's Brief
- [Other documents listed]

Extract the following in JSON format:
{
  "case_number": "YYYYNNNN",
  "case_name": "Party v. Party",
  "appellant": "name",
  "appellee": "name",
  "procedural_posture": "Appeal from [order type] in [case type]",
  "issues_on_appeal": [
    {
      "number": 1,
      "statement": "Whether the district court erred in...",
      "appellant_framing": "...",
      "appellee_framing": "..."
    }
  ],
  "key_facts": ["fact1", "fact2"],
  "key_documents": [
    {"description": "Order Granting Summary Judgment", "record_cite": "R45"}
  ]
}
```

**Stage 4 prompt (Memo Generation):**
```
Generate a complete bench memo following the style specification provided.

CASE ANALYSIS:
[Stage 1 JSON]

LEGAL FRAMING:
[Stage 2 JSON]

KEY DOCUMENTS SECTION:
[Stage 3 output]

Generate the complete memo in markdown format. Begin with the header,
then Quick Reference, then the opening paragraph [¶1], then BACKGROUND,
then analysis of each issue, then CONCLUSION.

Remember:
- Every paragraph must be numbered [¶1], [¶2], etc.
- Use record citations (R##) throughout the background
- Cite cases as YYYY ND ### or ### N.W.2d ###
- Include standard of review before analyzing each issue
- State your recommendation in [¶1] and repeat in CONCLUSION
```

---

### 1.8 Command-Line Interface

**File: `src/cli.py`**

**Commands:**
```bash
# Generate a memo from a folder of case documents
bench-memo generate ./case_20250123/ --output memo.md

# Generate with specific options
bench-memo generate ./case_20250123/ \
    --output memo.md \
    --verify          # Run citation verification
    --no-recommend    # Don't include recommendation
    --verbose         # Show progress details

# Verify citations in an existing memo
bench-memo verify memo.md --output verified_memo.md

# Show cost estimate without generating
bench-memo estimate ./case_20250123/
```

**Implementation with Click:**
```python
@click.group()
def cli():
    """Bench Memo Generator for ND Supreme Court"""
    pass

@cli.command()
@click.argument('case_folder', type=click.Path(exists=True))
@click.option('--output', '-o', default='memo.md', help='Output file path')
@click.option('--verify/--no-verify', default=True, help='Verify citations')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def generate(case_folder, output, verify, verbose):
    """Generate a bench memo from case documents."""
    # Implementation
```

---

## Phase 2: Citation Verification (Weeks 4-5)

### 2.1 Citation Parser

**File: `src/verifier/citation_parser.py`**

**Purpose:** Extract and normalize citations from generated memo text.

**Citation patterns:**
```python
PATTERNS = {
    'nd_case': r'(\d{4})\s+ND\s+(\d+)',           # 2024 ND 156
    'nw2d': r'(\d+)\s+N\.W\.2d\s+(\d+)',          # 876 N.W.2d 234
    'ndcc': r'N\.D\.C\.C\.\s*§\s*([\d\-\.]+)',    # N.D.C.C. § 14-09-06.2
    'nd_rule_app': r'N\.D\.R\.App\.P\.\s*(\d+)',  # N.D.R.App.P. 35.1
    'nd_rule_civ': r'N\.D\.R\.Civ\.P\.\s*(\d+)',
    'nd_rule_ev': r'N\.D\.R\.Ev\.\s*(\d+)',
    'record': r'\(R(\d+)(?::(\d+))?(?::¶(\d+))?\)',  # (R45), (R45:12), (R45:12:¶15)
    'paragraph': r'¶\s*(\d+)',                     # ¶ 15
}

@dataclass
class Citation:
    raw_text: str           # Original text as found
    citation_type: str      # 'nd_case', 'statute', etc.
    normalized: str         # Normalized form for lookup
    context: str            # Surrounding text (for quotation checking)
    line_number: int        # Location in memo
```

### 2.2 CourtListener Client

**File: `src/verifier/courtlistener.py`**

**Purpose:** Primary case law verification via CourtListener API.

```python
class CourtListenerClient:
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = diskcache.Cache('./cache/courtlistener')

    async def verify_citation(self, citation: str) -> VerificationResult:
        """
        Verify a case citation exists and return details.

        Returns:
            VerificationResult with:
            - exists: bool
            - case_name: str (if found)
            - full_citation: str
            - url: str (link to opinion)
            - snippet: str (relevant excerpt if quotation provided)
        """

    async def search_by_name(self, case_name: str) -> list[SearchResult]:
        """Search for cases by party names."""

    async def get_opinion_text(self, opinion_id: int) -> str:
        """Retrieve full opinion text for quotation verification."""
```

**Caching strategy:**
- Cache all successful lookups indefinitely (case law doesn't change)
- Cache "not found" results for 24 hours (might be indexing delay)
- Use `diskcache` for persistence across sessions

### 2.3 Harvard Case.law Client

**File: `src/verifier/caselaw.py`**

**Purpose:** Backup verification and historical case access.

```python
class CaseLawClient:
    BASE_URL = "https://api.case.law/v1"

    async def verify_citation(self, citation: str) -> VerificationResult:
        """Verify via Case.law API (backup to CourtListener)."""

    async def get_full_text(self, case_id: str) -> str:
        """Get full case text for quotation verification."""
```

### 2.4 ND Courts Scraper

**File: `src/verifier/nd_courts.py`**

**Purpose:** Scrape recent ND Supreme Court opinions not yet in free databases.

```python
class NDCourtsScraper:
    BASE_URL = "https://www.ndcourts.gov"

    async def find_opinion(self, citation: str) -> Optional[str]:
        """
        Find and download ND Supreme Court opinion by citation.
        Returns extracted text or None if not found.
        """

    async def search_by_docket(self, docket_number: str) -> Optional[str]:
        """Search by docket number (e.g., 20240156)."""
```

**Implementation notes:**
- Scrape opinion list pages to build citation → URL mapping
- Download PDFs and extract text with pdfminer
- Cache extracted opinions locally
- Respect rate limits (1 request/second)

### 2.5 ND Statutes Scraper

**File: `src/verifier/nd_statutes.py`**

**Purpose:** Verify ND Century Code citations.

```python
class NDStatutesScraper:
    BASE_URL = "https://www.ndlegis.gov/cencode"

    async def verify_statute(self, section: str) -> VerificationResult:
        """
        Verify N.D.C.C. section exists and return text.

        Args:
            section: e.g., "14-09-06.2"
        """

    async def get_section_text(self, section: str) -> str:
        """Get full text of a statute section."""
```

### 2.6 Quotation Verifier

**File: `src/verifier/quotation_verifier.py`**

**Purpose:** Check that quoted text matches the source.

```python
async def verify_quotation(
    quoted_text: str,
    source_text: str,
    tolerance: float = 0.95
) -> QuotationResult:
    """
    Verify a quotation appears in source text.

    Uses fuzzy matching to handle:
    - Minor punctuation differences
    - Whitespace normalization
    - [bracketed] alterations
    - ... ellipses

    Returns:
        QuotationResult with:
        - verified: bool
        - match_score: float (0-1)
        - source_excerpt: str (context around match)
        - discrepancies: list[str] (if any)
    """
```

### 2.7 Verification Orchestrator

**File: `src/verifier/verifier.py`**

**Purpose:** Coordinate all verification sources.

```python
class CitationVerifier:
    def __init__(
        self,
        courtlistener: CourtListenerClient,
        caselaw: CaseLawClient,
        nd_courts: NDCourtsScraper,
        nd_statutes: NDStatutesScraper,
    ):
        ...

    async def verify_memo(self, memo_text: str) -> VerificationReport:
        """
        Verify all citations in a memo.

        Returns VerificationReport with:
        - verified_citations: list[VerifiedCitation]
        - unverified_citations: list[UnverifiedCitation]
        - quotation_issues: list[QuotationIssue]
        - summary: VerificationSummary
        """

    async def verify_single(self, citation: Citation) -> VerificationResult:
        """
        Verify a single citation using the appropriate source.

        Priority:
        1. CourtListener (fastest, best coverage)
        2. Case.law (backup, historical)
        3. ND Courts scraper (recent ND cases)
        4. ND Legislature (statutes)
        """
```

### 2.8 Verification Appendix Generator

**File: `src/output/appendix.py`**

**Output format:**
```markdown
---

## Citation Verification Appendix

### Verified Citations

| Citation | Case/Statute | Status | Source |
|----------|--------------|--------|--------|
| 2024 ND 156 | Smith v. Jones | ✓ Verified | [CourtListener](https://...) |
| N.D.C.C. § 14-09-06.2 | Custody factors | ✓ Verified | [ND Legislature](https://...) |

### Requires Manual Review

| Citation | Issue | Action Needed |
|----------|-------|---------------|
| 2025 ND 42 | Not found in databases | Verify case exists; may be too recent |
| ¶ 15 quote | Partial match (92%) | Check quotation accuracy |

### Quotation Verification

| Location | Quoted Text | Match | Notes |
|----------|-------------|-------|-------|
| ¶8 | "the district court abused its discretion..." | ✓ 100% | |
| ¶12 | "clearly erroneous standard applies..." | ⚠ 94% | Minor punctuation difference |

---
*Verification completed [timestamp]*
*Sources: CourtListener, Case.law, ndcourts.gov, ndlegis.gov*
```

---

## Phase 3: Production Hardening (Weeks 6-7)

### 3.1 Configuration Management

**File: `src/config/settings.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    courtlistener_api_key: str = ""  # Optional, increases rate limit

    # Model settings
    claude_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    max_tokens: int = 8192

    # Verification settings
    enable_verification: bool = True
    verification_cache_dir: str = "./cache"

    # Output settings
    include_appendix: bool = True

    class Config:
        env_file = ".env"
```

**User config file (`~/.bench-memo/config.toml`):**
```toml
[api]
anthropic_api_key = "sk-ant-..."
courtlistener_api_key = ""  # Optional

[generation]
model = "claude-sonnet-4-20250514"
temperature = 0.3
include_recommendation = true

[verification]
enabled = true
cache_directory = "~/.bench-memo/cache"

[output]
include_appendix = true
```

### 3.2 Error Handling

**Retry logic:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
)
async def call_claude(self, prompt: str) -> str:
    ...
```

**Graceful degradation:**
- If CourtListener fails → try Case.law → try ND Courts scraper
- If all verification fails → mark as "MANUAL_REVIEW", don't block generation
- If PDF extraction fails → warn user, skip document, continue with others

### 3.3 Progress Reporting

**Using Rich library:**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True,
) as progress:
    task = progress.add_task("Extracting documents...", total=None)
    # ... extraction
    progress.update(task, description="Analyzing case...")
    # ... analysis
    progress.update(task, description="Generating memo...")
    # ... generation
    progress.update(task, description="Verifying citations...")
    # ... verification
```

### 3.4 Packaging with PyInstaller

**Build script (`build.py`):**
```python
import PyInstaller.__main__

PyInstaller.__main__.run([
    'src/cli.py',
    '--onefile',
    '--name=bench-memo',
    '--add-data=config/prompts:config/prompts',
    '--add-data=config/style_specification.py:config',
    '--hidden-import=pdfminer.six',
    '--hidden-import=anthropic',
])
```

**Distribution:**
- Windows: `bench-memo.exe`
- macOS: `bench-memo` (universal binary)
- Include README with setup instructions

### 3.5 Logging

**Minimal logging setup:**
```python
import logging
from pathlib import Path

def setup_logging(verbose: bool = False):
    log_dir = Path.home() / ".bench-memo" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "bench-memo.log"),
        ]
    )
```

**What to log:**
- Errors and exceptions (always)
- API call summaries: tokens used, cost (if verbose)
- Verification results summary (if verbose)
- **Never log:** Full document content, API keys, case details

---

## Testing Strategy

### Unit Tests

```python
# test_citation_parser.py
def test_parse_nd_case():
    text = "See Smith v. Jones, 2024 ND 156, ¶ 12."
    citations = parse_citations(text)
    assert len(citations) == 2
    assert citations[0].citation_type == "nd_case"
    assert citations[0].normalized == "2024 ND 156"

def test_parse_statute():
    text = "Under N.D.C.C. § 14-09-06.2(1)(a), the court considers..."
    citations = parse_citations(text)
    assert citations[0].normalized == "14-09-06.2"
```

### Integration Tests

```python
# test_verification.py
@pytest.mark.integration
async def test_courtlistener_verification():
    client = CourtListenerClient(api_key=os.environ["CL_API_KEY"])
    result = await client.verify_citation("2024 ND 156")
    assert result.exists
    assert "Smith" in result.case_name or "Jones" in result.case_name
```

### End-to-End Tests

```python
# test_e2e.py
@pytest.mark.e2e
async def test_full_generation():
    """Test complete memo generation with sample case."""
    case_folder = Path("tests/fixtures/sample_case")
    memo = await generate_memo(case_folder)

    # Structure checks
    assert "[¶1]" in memo
    assert "Quick Reference:" in memo
    assert "BACKGROUND" in memo
    assert "CONCLUSION" in memo

    # Style checks
    assert re.search(r'\d{4} ND \d+', memo)  # Has ND citations
    assert re.search(r'\(R\d+\)', memo)       # Has record citations
```

---

## Milestones & Checkpoints

### Week 1: Foundation
- [ ] Project setup, dependencies installed
- [ ] PDF extraction working on sample briefs
- [ ] Document classifier identifying brief types
- [ ] Basic Claude client with retry logic

### Week 2: Generation Pipeline
- [ ] Stage 1-4 prompts drafted and tested
- [ ] Pipeline orchestration working
- [ ] Style specification embedded in prompts
- [ ] Generate first complete memo from sample case

### Week 3: CLI & Polish
- [ ] Command-line interface complete
- [ ] Progress indicators working
- [ ] Error handling robust
- [ ] Generate memos for 5+ test cases, manual review

### Week 4: Citation Verification
- [ ] Citation parser extracting all citation types
- [ ] CourtListener client working
- [ ] Case.law client working (backup)
- [ ] ND Courts scraper working

### Week 5: Verification Polish
- [ ] ND Statutes scraper working
- [ ] Quotation verification working
- [ ] Verification appendix generated
- [ ] Caching implemented

### Week 6: Production
- [ ] Configuration file support
- [ ] PyInstaller builds for Windows/Mac
- [ ] User documentation written
- [ ] Logging finalized

### Week 7: Testing & Release
- [ ] All unit tests passing
- [ ] Integration tests with live APIs
- [ ] End-to-end tests with real cases
- [ ] Beta release to 2-3 test users

---

*Implementation Guide v1.0 - January 28, 2026*
