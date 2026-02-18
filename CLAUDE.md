# CLAUDE.md

## Project Overview

Bench Memo Generator for the North Dakota Supreme Court. A Python CLI tool that automates creation of legal bench memos from appellate case PDFs using a multi-stage Claude API pipeline.

**Status:** Implementation specification complete; code implementation in progress.

## Tech Stack

- **Language:** Python 3.11+
- **CLI:** Click
- **LLM:** Anthropic Claude API (claude-sonnet-4-20250514)
- **PDF:** pdfminer.six
- **HTTP:** httpx (async)
- **Cache:** diskcache
- **Terminal UI:** Rich
- **Config:** Pydantic, python-dotenv
- **Tests:** pytest, pytest-asyncio

## Project Structure

```
bench_memo_generator/
├── config/          # Settings, style spec, prompt templates
├── src/
│   ├── cli.py       # Click CLI entry point
│   ├── extractor/   # PDF text extraction & document parsing
│   ├── classifier/  # Document type classification
│   ├── generator/   # Memo generation pipeline & Claude client
│   ├── verifier/    # Citation verification (CourtListener, Case.law, ND Courts, ND Legislature)
│   ├── output/      # Markdown writer & appendix generation
│   └── utils/       # Caching, logging
└── tests/           # pytest suite with fixtures/sample_briefs/
```

## Build & Run

```bash
pip install -e ".[dev]"       # Install with dev deps
cp .env.example .env          # Configure ANTHROPIC_API_KEY

bench-memo generate ./case_folder/ --output memo.md
bench-memo generate ./case_folder/ --verify --output memo.md
bench-memo estimate ./case_folder/
bench-memo verify memo.md --output verified_memo.md
bench-memo extract-cites ./case_folder/ --output items.txt
```

## Testing

```bash
pytest                        # All tests
pytest -m "not integration"   # Unit tests only
pytest -v                     # Verbose
```

## Key Conventions

- Async/await for all I/O operations
- Type hints throughout
- Dataclasses for structured data
- Cache-first pattern for API calls (check diskcache before network)
- Graceful degradation: verification failures never block memo generation
- Retry with exponential backoff for rate-limited APIs

## Citation Formats

```
ND Cases:    2024 ND 156
Reporter:    876 N.W.2d 234
Statutes:    N.D.C.C. § 14-09-06.2
Rules:       N.D.R.App.P. 35.1, N.D.R.Civ.P. 12(b), N.D.R.Ev. 401
Record:      (R45), (R45:12), (R45:12:¶15)
Paragraphs:  ¶ 1, ¶ 15
```

## Architecture Notes

- 5-stage pipeline: Extract → Analyze → Frame → Select Key Docs → Generate
- Optional self-review and citation verification stages
- Multi-source verification fallback: CourtListener → Case.law → ND Courts
- Implementation guide: `Bench_Memo_Implementation_Guide.md`
