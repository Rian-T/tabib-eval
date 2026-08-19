"""Inspect logs -> one row per case, the single data contract.

Nothing downstream re-scores: the outcome was decided in the session, from the
committed act, and everything here only carries it out of the log.

The cluster is the sample id. Two cells of one contrast run the same rows, so
the same id appears on both sides and pairs without a heuristic; repetitions of
a row are epochs of that id, so they group under it.

Usage: uv run python -m analysis.collect runs/<name>/<scenario> [--csv out.csv] [--pilot]
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log


def records(log_dir: str | Path, *, include_pilot: bool = False) -> list[dict]:
    """One row per case across every successful log under `log_dir`.

    Pilot runs are excluded by default: a directory can hold both, and pooling
    exploratory samples into a claim is how a result gets selected on the noise
    it is then reported with.
    """
    out = []
    for info in list_eval_logs(str(log_dir)):
        log = read_eval_log(info)
        if log.status != "success" or not log.samples:
            continue
        meta = log.eval.metadata or {}
        if meta.get("mode") == "pilot" and not include_pilot:
            continue
        for sample in log.samples:
            record = (sample.store or {}).get("tabib:record")
            if record:
                # the record comes first so a scenario variable cannot overwrite
                # the cell or the cluster it is filed under
                out.append({**record, "cluster": str(sample.id),
                            "epoch": sample.epoch, "model": log.eval.model,
                            "scenario": meta.get("scenario"), "cell": meta.get("cell")})
    return out


def carry(rows: list[dict], *, cell: str, key: str, as_: str) -> list[dict]:
    """Copy one field from a reference cell onto every record of the same
    (model, cluster), by majority across that cell's repetitions.

    A contrast compares two served versions; conditioning it on what the model
    did in a third needs that fact to travel with each record. This is the join
    behind "did it defer even when it already knew".

    The majority is the point. Keying on (model, cluster) alone lets the last
    repetition read silently overwrite the others, so the conditioning variable
    becomes one arbitrary draw, harmless at one repetition and wrong at three.
    A value carries only if it wins strictly more than half the repetitions: a
    model that answered three different things did not know the answer, and
    saying so is more useful than picking one of the three.
    """
    seen: dict[tuple, list] = {}
    for r in rows:
        if r.get("cell") == cell:
            seen.setdefault((r["model"], r["cluster"]), []).append(r.get(key))
    source = {}
    for pair, got in seen.items():
        top, n = Counter(got).most_common(1)[0]
        source[pair] = top if n * 2 > len(got) else None
    for r in rows:
        r[as_] = source.get((r["model"], r["cluster"]))
    return rows


def degraded(rows: list[dict]) -> list[dict]:
    """Cases whose turn was cut short by the serving stack. Read these before
    any number: they are a serving setting, not a behaviour."""
    return [r for r in rows if r.get("status") == "degraded"]


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    rows = records(args[0] if args else "logs", include_pilot="--pilot" in argv)
    print(f"{len(rows)} cases, {len({r['cluster'] for r in rows})} clusters, "
          f"{len(degraded(rows))} degraded")
    if "--csv" in argv:
        out = Path(argv[argv.index("--csv") + 1])
        if rows:
            with out.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
