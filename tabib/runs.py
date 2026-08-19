"""A run is a name. Launch, resume and analysis all take the same string.

Inspect already resumes: pointing `eval_set` at a log directory it has used
before continues that set, and it marks the directory with `.eval-set-id`. This
module adds only what Inspect has no opinion about: where those directories
live, and how to name one without typing a path twice.

    runs/<label>-<date>/<scenario>/     one eval set per scenario

Provenance is not stored here. Every `.eval` already carries the commit, the
dirty flag, the package versions and the full model config, so a second copy
beside the logs could only disagree with them.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

ROOT = Path(os.environ.get("TABIB_RUNS", "runs"))

# Inspect deletes the older logs of a task when a set is retried, which drops
# the provenance of every launch but the last. Campaigns pass this to eval_set.
KEEP_LOGS = {"retry_cleanup": False}


def new(label: str) -> str:
    """A dated run name: 'claim' -> 'claim-YYYYMMDD'."""
    return f"{label}-{date.today():%Y%m%d}"


def names() -> list[str]:
    return sorted(p.name for p in ROOT.glob("*") if any(p.glob("*/.eval-set-id")))


def resolve(spec: str) -> str:
    """Full name, unique prefix, or 'latest', the most recently written, not
    the last in alphabetical order."""
    known = names()
    if spec == "latest" and known:
        return max(known, key=lambda n: (ROOT / n).stat().st_mtime)
    hits = [n for n in known if n == spec] or [n for n in known if n.startswith(spec)]
    if len(hits) == 1:
        return hits[0]
    raise SystemExit(f"run {spec!r} matches {hits or known or 'nothing'}")


def log_dir(spec: str, scenario: str) -> str:
    """Where one scenario's eval set lives. A name that matches nothing yet is
    taken as is, so the first launch creates it and later ones resume it."""
    if os.sep in spec:
        return spec
    try:
        spec = resolve(spec)
    except SystemExit:
        # a name matching nothing is a new run; a name matching several is a
        # mistake, and creating a third directory would hide it
        if any(n.startswith(spec) for n in names()):
            raise
    d = ROOT / spec / scenario
    d.mkdir(parents=True, exist_ok=True)
    return str(d)
