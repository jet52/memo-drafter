"""Minimal logging setup."""

import logging
from pathlib import Path


def setup_logging(verbose: bool = False):
    log_dir = Path.home() / ".bench-memo" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.WARNING

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "bench-memo.log"),
            logging.StreamHandler(),
        ],
    )
    # Only set our loggers to debug, not third-party libraries
    for name in ("src", "config"):
        logging.getLogger(name).setLevel(level)
