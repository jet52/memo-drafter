"""Local caching for API responses."""

from pathlib import Path

import diskcache


def get_cache(name: str, cache_dir: str = "./cache") -> diskcache.Cache:
    """Get or create a named disk cache."""
    path = Path(cache_dir) / name
    path.mkdir(parents=True, exist_ok=True)
    return diskcache.Cache(str(path))
