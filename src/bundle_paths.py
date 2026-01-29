"""Resolve file paths that work both in development and PyInstaller bundles."""

import sys
from pathlib import Path


def _base_path() -> Path:
    """Return the base path for bundled data files.

    When running as a PyInstaller bundle, sys._MEIPASS points to the
    temporary directory where bundled data is extracted. Otherwise,
    fall back to the project root (parent of the src/ package).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_config_path(*parts: str) -> Path:
    """Return the path to a file under the config/ directory."""
    return _base_path().joinpath("config", *parts)


def get_project_root() -> Path:
    """Return the project root (or bundle base) path."""
    return _base_path()
