"""Main orchestration: load documents, classify, run pipeline, write output."""

import logging
from pathlib import Path

from src.classifier.document_classifier import classify
from src.extractor.pdf_extractor import extract
from src.generator.claude_client import ClaudeClient
from src.generator.pipeline import CaseDocuments, GeneratedMemo, MemoPipeline
from src.output.markdown_writer import write_memo

logger = logging.getLogger(__name__)


async def generate_memo(
    output_path: Path,
    client: ClaudeClient,
    case_folder: Path | None = None,
    pdf_files: list[Path] | None = None,
    enable_self_review: bool = False,
    progress_callback=None,
) -> GeneratedMemo:
    """Full end-to-end memo generation.

    Provide either case_folder (all PDFs in directory) or pdf_files (explicit list).
    """

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    # 1. Discover and extract PDFs
    _progress("Extracting documents...")
    if pdf_files:
        files = sorted(pdf_files)
    elif case_folder:
        files = sorted(case_folder.glob("*.pdf"))
    else:
        raise ValueError("Must provide either case_folder or pdf_files")

    if not files:
        raise FileNotFoundError(f"No PDF files found in {case_folder}")

    texts: dict[str, str] = {}
    types: dict[str, str] = {}

    for pdf_path in files:
        _progress(f"  Extracting {pdf_path.name}...")
        text = extract(pdf_path)
        doc_type = classify(pdf_path.name, text)
        texts[pdf_path.name] = text
        types[pdf_path.name] = doc_type.value
        logger.info("Classified %s as %s", pdf_path.name, doc_type.value)

    case = CaseDocuments(texts=texts, types=types, folder=case_folder)

    # 2. Run pipeline
    pipeline = MemoPipeline(client, enable_self_review=enable_self_review,
                            progress_callback=_progress)
    memo = await pipeline.generate(case)

    # 3. Write output
    _progress(f"Writing memo to {output_path}...")
    write_memo(memo.memo_text, output_path)

    _progress("Done!")
    return memo
