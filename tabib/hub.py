"""Where a package published as `owner/name` lives on this machine.

Loading stays offline. A world that had to be downloaded where it is served is a
world that cannot be measured there, and the compute nodes have no network. So
the loader only ever reads the cache, and filling it is `fetch`, an explicit
step run from a machine that does have one.
"""

from __future__ import annotations

import os
from pathlib import Path

CACHE = Path(os.environ.get("TABIB_CACHE",
                            Path.home() / ".cache" / "tabib")).expanduser()


def cache_path(ref: str) -> Path:
    """`<cache>/owner/name`. A bare name is filed under `_`."""
    parts = ref.split("/")
    return CACHE / (parts[-2] if len(parts) > 1 else "_") / parts[-1]


def fetch(ref: str) -> Path:
    """Snapshot a published package into the cache. Never called at load.

    The download is not written: what is fixed here is that there is exactly
    one place a fetched package lands, and that loading never gets there on its
    own.
    """
    at = cache_path(ref)
    if at.is_dir():
        return at
    raise NotImplementedError(
        f"{ref} is not in the cache. Fetching is not implemented: place the "
        f"package at {at} by hand, or load it from a directory path.")
