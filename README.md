# Bench Memo Generator

A Python CLI tool that automates creation of legal bench memos from appellate case PDFs using a multi-stage Claude API pipeline. Built as an experiment using public documents.

## Installation

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and set your keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Anthropic API key for Claude |
| `COURTLISTENER_API_KEY` | No | CourtListener API key for citation verification ([free signup](https://www.courtlistener.com/sign-in/)) |
| `COURT_DATA` | No | Path to local court data directory containing `markdown/` and `pdfs/` subdirectories of ND opinions |

Additional settings in `.env`:

| Variable | Default | Description |
|---|---|---|
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `TEMPERATURE` | `0.3` | LLM temperature |
| `MAX_TOKENS` | `8192` | Max output tokens per API call |
| `VERIFICATION_CACHE_DIR` | `./cache` | Directory for caching verification results |

## Usage

### Generate a Bench Memo

```bash
bench-memo generate INPUTS... [OPTIONS]
```

Generates a bench memo from case PDF documents. `INPUTS` can be either:
- A **directory** containing PDF files (all PDFs in the directory are used)
- One or more **PDF file paths** (shell glob expansion supported)

| Argument / Option | Description |
|---|---|
| `INPUTS` | Directory or PDF file path(s) (required) |
| `-o, --output PATH` | Output file path. Defaults to `output/{name}_memo.md` |
| `--verify / --no-verify` | Run citation verification after generation (default: no-verify) |
| `--review / --no-review` | Enable LLM self-review stage (default: no-review) |
| `-v, --verbose` | Verbose logging output |

**Examples:**

```bash
# All PDFs in a directory
bench-memo generate ./cases/davis_v_state/ -o memo.md --verify --review -v

# Specific PDF files
bench-memo generate ./cases/brief1.pdf ./cases/brief2.pdf ./cases/order.pdf -o memo.md

# Shell glob pattern
bench-memo generate ./cases/20250319*.pdf -o memo.md
```

### Verify Citations

```bash
bench-memo verify MEMO_FILE [OPTIONS]
```

Verifies citations in an existing memo and appends a verification appendix.

| Argument / Option | Description |
|---|---|
| `MEMO_FILE` | Path to the memo markdown file (required) |
| `-o, --output PATH` | Output file path. Defaults to overwriting the input file |
| `-v, --verbose` | Verbose logging output |

**Example:**

```bash
bench-memo verify memo.md -o verified_memo.md
```

### Estimate Cost

```bash
bench-memo estimate INPUTS...
```

Estimates token count and API cost without making any API calls. Accepts the same input formats as `generate`.

| Argument / Option | Description |
|---|---|
| `INPUTS` | Directory or PDF file path(s) (required) |

**Examples:**

```bash
bench-memo estimate ./cases/davis_v_state/
bench-memo estimate ./cases/20250319*.pdf
```

## Pipeline Stages

The memo generation pipeline runs through these stages:

1. **Extract** — PDF text extraction from all case documents
2. **Analyze** — Document classification and initial analysis
3. **Frame** — Issue identification and legal framing
4. **Select Key Documents** — Identify the most relevant authorities
5. **Generate** — Full bench memo generation
6. *(Optional)* **Self-Review** — LLM reviews and refines its own output

## Citation Verification

Verification checks citations against multiple sources with a fallback chain:

1. **Local data** (instant) — Searches `COURT_DATA/markdown/{year}/{year}ND{number}.md` files
2. **CourtListener** (requires API key) — Searches the CourtListener database
3. **ND Courts scraper** (free, ND cases only) — Scrapes ndcourts.gov

Statute citations are verified against the ND Century Code via ndlegis.gov. Record citations and procedural rules are skipped (not verifiable online).

Verification is optional and never blocks memo generation.

## Testing

```bash
pytest                        # All tests
pytest -m "not integration"   # Unit tests only
pytest -v                     # Verbose
```
