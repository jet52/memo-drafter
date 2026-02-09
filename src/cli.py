"""Command-line interface for Bench Memo Generator."""

import asyncio
import re
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import Settings
from src.bundle_paths import get_project_root
from src.generator.claude_client import ClaudeClient
from src.generator.memo_generator import generate_memo
from src.utils.logging import setup_logging

console = Console()


def _load_settings() -> Settings:
    load_dotenv(get_project_root() / ".env", override=True)
    return Settings()


def _make_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Bench Memo Generator for the North Dakota Supreme Court.

    \b
    Generates bench memos from appellate case PDFs using a multi-stage
    Claude API pipeline (analyze, frame, select key docs, generate).

    \b
    EXPECTED INPUT:
      A folder or set of PDF files for a single case. The tool
      automatically classifies each PDF by filename and content:

    \b
      Recognized document types and filename patterns:
        Appellant brief   - filename contains "Apt" or "Appellant" + "Br"
        Appellee brief    - filename contains "Ape" or "Appellee" + "Br"
        Reply brief       - filename contains "Reply" + "Br"
        District court order - filename contains "Order"
        Judgment          - filename contains "Judgment"
        Findings/Conclusions - filename contains "Finding"
        Notice of appeal  - filename contains "Notice" + "Appeal"
        Transcript        - filename contains "Transcript"
        Exhibit           - filename contains "Exhibit"

    \b
      Example folder layout:
        case_20250319/
          20250319_State-v-Landen_Apt-Br.pdf
          20250319_State-v-Landen_Ape-Br.pdf
          20250319_State-v-Landen_Apt-Reply.pdf
          20250319_State-v-Landen_Order.pdf
          20250319_State-v-Landen_Judgment.pdf

    \b
    OUTPUT:
      A Markdown bench memo written to an output/ subdirectory next to the
      input (default), or to a path you specify with -o.

    \b
    SETUP:
      Requires ANTHROPIC_API_KEY in .env or as an environment variable.
      Optional: COURTLISTENER_API_KEY for citation verification.

    \b
    COMMANDS:
      generate  - Generate a bench memo from case PDFs
      estimate  - Preview token count and estimated cost
      verify    - Verify citations in an existing memo

    \b
    Run 'bench-memo COMMAND --help' for details on each command.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@cli.command()
@click.argument("inputs", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--verify/--no-verify", default=False, help="Run citation verification")
@click.option("--review/--no-review", default=False, help="Enable self-review stage")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def generate(inputs: tuple[str, ...], output: str | None, verify: bool, review: bool, verbose: bool):
    """Generate a bench memo from case documents.

    \b
    INPUTS can be:
      - A single directory containing PDF files for one case
      - One or more individual PDF file paths (supports shell globs)

    \b
    The pipeline runs 4 stages (5 with --review):
      1. Document analysis  - extracts parties, issues, and structure
      2. Legal framing      - identifies standards of review per issue
      3. Key doc selection  - picks 4-8 documents for Quick Reference
      4. Memo generation    - writes the complete bench memo
      5. Self-review        - (optional) Claude reviews its own output

    \b
    OUTPUT defaults to an output/ subdirectory next to the input:
      ./case_folder/  ->  ./output/case_folder_memo.md
    Use -o to specify a file path or directory.

    \b
    Examples:
      bench-memo generate ./case_folder/
      bench-memo generate ./cases/brief1.pdf ./cases/brief2.pdf
      bench-memo generate ./cases/20250319*.pdf
      bench-memo generate ./case_folder/ -o ./memos/
      bench-memo generate ./case_folder/ --verify --review
    """
    setup_logging(verbose)
    settings = _load_settings()

    if not settings.anthropic_api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY not set. Create a .env file or set the environment variable.")
        raise SystemExit(1)

    # Determine if input is a directory or list of files
    input_paths = [Path(p) for p in inputs]
    if len(input_paths) == 1 and input_paths[0].is_dir():
        case_folder = input_paths[0]
        pdf_file_list = None
        label = case_folder.name
        default_output_dir = case_folder.parent / "output"
    else:
        for p in input_paths:
            if not p.is_file():
                console.print(f"[red]Error:[/red] {p} is not a file.")
                raise SystemExit(1)
            if p.suffix.lower() != ".pdf":
                console.print(f"[red]Error:[/red] {p} is not a PDF file.")
                raise SystemExit(1)
        case_folder = None
        pdf_file_list = input_paths
        # Extract case number from filename (leading digits, e.g. "20250305" from "20250305_State-v-Landen_Apt-Br.pdf")
        first_name = pdf_file_list[0].stem
        match = re.match(r"(\d+)", first_name)
        label = match.group(1) if match else first_name
        default_output_dir = pdf_file_list[0].parent / "output"

    if output is None:
        output_path = default_output_dir / f"{label}_memo.md"
    else:
        output_path = Path(output)
        if output_path.is_dir():
            output_path = output_path / f"{label}_memo.md"

    client = ClaudeClient(api_key=settings.anthropic_api_key, model=settings.claude_model)

    with _make_progress() as progress:
        task = progress.add_task("Starting...", total=None)

        def on_progress(msg: str):
            progress.update(task, description=msg)

        memo = asyncio.run(
            generate_memo(
                output_path=output_path,
                client=client,
                case_folder=case_folder,
                pdf_files=pdf_file_list,
                enable_self_review=review,
                progress_callback=on_progress,
            )
        )

    console.print(f"\n[green]✓[/green] Memo written to [bold]{output_path}[/bold]")
    console.print(f"  {client.usage_summary()}")

    # Optional: citation verification
    if verify:
        _run_verification(output_path, settings)


@cli.command("verify")
@click.argument("memo_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", default=None, help="Output file (appends appendix)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def verify_cmd(memo_file: str, output: str | None, verbose: bool):
    """Verify citations in an existing memo.

    \b
    Checks case citations, statutes, and rules against external sources:
      - CourtListener API (ND cases, N.W.2d reporter cites)
      - ND Courts website (recent opinions)
      - ND Legislature (N.D.C.C. statutes)

    \b
    Appends a verification appendix to the memo showing each citation's
    status (verified, not found, or error). By default, writes back to
    the same file; use -o to write to a different location.

    \b
    MEMO_FILE should be a Markdown memo previously generated by this tool.

    \b
    Examples:
      bench-memo verify ./output/case_memo.md
      bench-memo verify ./output/case_memo.md -o ./verified/
    """
    setup_logging(verbose)
    settings = _load_settings()
    memo_path = Path(memo_file)
    if output:
        output_path = Path(output)
        if output_path.is_dir():
            output_path = output_path / memo_path.name
    else:
        output_path = memo_path
    _run_verification(memo_path, settings, output_path)


def _run_verification(memo_path: Path, settings: Settings, output_path: Path | None = None):
    """Run citation verification on a memo file."""
    from src.output.appendix import generate_appendix
    from src.verifier.verifier import CitationVerifier

    if output_path is None:
        output_path = memo_path

    memo_text = memo_path.read_text(encoding="utf-8")

    with _make_progress() as progress:
        task = progress.add_task("Verifying citations...", total=None)

        def on_progress(msg: str):
            progress.update(task, description=msg)

        verifier = CitationVerifier(
            courtlistener_api_key=settings.courtlistener_api_key,
            court_data_dir=settings.court_data,
            cache_dir=settings.verification_cache_dir,
            progress_callback=on_progress,
        )
        report = asyncio.run(verifier.verify_memo(memo_text))

    # Generate and append appendix
    appendix = generate_appendix(report)
    combined = memo_text.rstrip() + "\n" + appendix
    output_path.write_text(combined, encoding="utf-8")

    console.print(f"\n[green]✓[/green] Verification complete: {report.summary}")
    console.print(f"  Appendix written to [bold]{output_path}[/bold]")


@cli.command()
@click.argument("inputs", nargs=-1, required=True, type=click.Path(exists=True))
def estimate(inputs: tuple[str, ...]):
    """Estimate token count and cost for case documents.

    \b
    Extracts text from each PDF, classifies the document type, and
    reports per-file character counts with a rough cost estimate for
    the full generation pipeline.

    \b
    INPUTS can be:
      - A single directory containing PDF files for one case
      - One or more individual PDF file paths (supports shell globs)

    \b
    Does NOT call the Claude API -- safe to run without cost.

    \b
    Examples:
      bench-memo estimate ./case_folder/
      bench-memo estimate ./cases/20250319*.pdf
    """
    from src.extractor.pdf_extractor import extract
    from src.classifier.document_classifier import classify

    input_paths = [Path(p) for p in inputs]
    if len(input_paths) == 1 and input_paths[0].is_dir():
        pdf_files = sorted(input_paths[0].glob("*.pdf"))
    else:
        pdf_files = sorted(input_paths)

    if not pdf_files:
        console.print("[red]No PDF files found.[/red]")
        raise SystemExit(1)

    total_chars = 0
    console.print(f"\nFound {len(pdf_files)} PDF files:\n")
    for pdf_path in pdf_files:
        text = extract(pdf_path)
        doc_type = classify(pdf_path.name, text)
        chars = len(text)
        total_chars += chars
        console.print(f"  {pdf_path.name}: {chars:,} chars ({doc_type.value})")

    # Rough estimate: ~4 chars per token, pipeline uses ~2x input for multi-stage
    est_tokens = (total_chars // 4) * 2
    est_cost = (est_tokens / 1_000_000) * 3.0 + (est_tokens / 1_000_000 * 0.3) * 15.0

    console.print(f"\nTotal text: {total_chars:,} characters")
    console.print(f"Estimated tokens: ~{est_tokens:,}")
    console.print(f"Estimated cost: ~${est_cost:.2f}")


if __name__ == "__main__":
    cli()
