"""Could a policy that reads nothing produce this result, and does the scenario
measure anything at all?

Two questions, one run. Every policy the core derives from the declared acts
goes through the scenario exactly as a model would, and every contrast must come
out at zero. Then the scenario's oracle goes through the same path, and the same
contrast must come out clearly away from zero, in the declared direction.

Both halves are needed. Blind policies alone pass a scenario where nothing
works, because a dead instrument also reports zero. An oracle alone passes an
effect any constant answer reproduces.

The gate blocks. It does not annotate a run with a warning, because a warning
printed next to a number reads as a number with a caveat rather than as a number
that should not exist.

Usage: uv run python -m analysis.gate <scenario> [--n 30] [--reps 1]
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path
from statistics import fmean

from inspect_ai import eval as inspect_eval
from inspect_ai.model import get_model

from analysis.collect import carry, records
from tabib import scenario as reg
from tabib.measurand import dropped, values
from tabib.nulls import MOCK, degenerate

ZERO = 1e-9         # a blind policy is exactly zero; this absorbs float noise
# One directory per scenario, set aside on entry, and deliberately not suffixed
# by pid. A suffix left one directory per invocation lying around, all named
# alike and none carrying the code it ran under; reading a stale one is how a
# campaign was cancelled over a field that had been added since. Setting the old
# one aside keeps that property (the live path holds exactly one run) without
# destroying the run before it.
LOGS = Path("logs/_gate")


def _run(sc, policy, *, log_dir: Path, n: int, reps: int) -> list[dict]:
    rows = []
    for cell in sc.cells:
        out = log_dir / cell
        inspect_eval(reg.build_task(sc, cell, reps=reps, n=n),
                     model=get_model(MOCK, custom_outputs=policy),
                     log_dir=str(out), display="none")
        rows += records(out, include_pilot=True)
    for cell, key, name in sc.carries:
        carry(rows, cell=cell, key=key, as_=name)
    return rows


def sweep(sc, *, n: int = 30, reps: int = 1, log_dir: Path = LOGS) -> list[dict]:
    """One line per (policy, contrast).

    A previous run is set aside, never deleted. Gate traces are disposable in the
    sense that nothing publishable is computed from them, but this used to be an
    `rmtree`, and this project has had its own tooling destroy readable data three
    times (`docs/DEFECTS.md`). "Disposable" is a statement about what we compute
    from a file, not a licence to delete it: a gate run that just failed is
    exactly the trace someone wants to read, and it was being wiped by the next
    invocation. `rung.py` was fixed the same way after a reclimb destroyed 101
    sessions. The fresh directory is just as clean either way.
    """
    if not log_dir.name.startswith("_gate"):
        raise ValueError(f"refusing to touch {log_dir}: a gate log dir is named _gate*")
    log_dir = log_dir / sc.name
    if log_dir.exists():
        log_dir.rename(log_dir.with_name(
            f"{log_dir.name}.replaced-{datetime.now():%Y%m%dT%H%M%S}"))

    report = []
    # the core's blind policies, then the scenario's own, then the oracle. A
    # scenario declares its own where a session of several calls leaves the
    # core's answering nothing at all: those are filtered out rather than
    # scored, and a gate running only them proves nothing about a policy that
    # acts, cites, and reads nothing
    for name, policy in {**degenerate(sc.acts), **dict(sc.policies),
                         "oracle": sc.oracle}.items():
        is_oracle = name == "oracle"
        rows = _run(sc, policy, log_dir=log_dir / name, n=n, reps=reps)
        for m in sc.measurands:
            if not m.contrast:
                continue
            paired = values(m, rows)
            got = fmean(v for _, v in paired) if paired else None
            unpaired = dropped(m, rows)
            # only the oracle is asked to move a contrast; everything else must
            # leave it at zero, placebo channels included
            want = m.oracle_moves if is_oracle else "none"
            if want == "unscripted":
                # no scripted reader has prior knowledge, so this channel has
                # nothing to prove against the oracle; the blind policies above
                # still had to come out at zero on it
                status = "abstained"
            elif got is None:
                # A measurand may select the records that count at all. A blind
                # policy filtered out entirely contributed nothing, so it did
                # not reproduce anything: that is a pass, and printed as its
                # own thing rather than as a zero it never scored. An oracle
                # with no data is the scenario failing to measure.
                #
                # Except on a channel the oracle is not asked to move. The
                # floor between the two cells where nothing is served has no
                # oracle data by construction: an oracle that reads the
                # document abstains when there is no document, which is what
                # makes it an oracle. Demanding data there would demand an
                # oracle that answers from nothing, and the half of the gate
                # that guards a `none` channel, where no blind policy
                # reproduces it, still runs and still has to pass.
                status = ("empty" if is_oracle and want != "none"
                          else "abstained")
            elif unpaired:
                # a contrast quietly covering a fraction of the corpus is not a
                # passing contrast, whatever value it comes out at
                status = "fail"
            elif want == "none":
                status = "ok" if abs(got) <= ZERO else "fail"
            else:
                # an oracle producing the effect backwards is a scenario wired
                # the wrong way round, not a passing one
                status = "ok" if (got >= m.separates if want == "up"
                                  else got <= -m.separates) else "fail"
            report.append({"policy": name, "measurand": m.name, "got": got,
                           "separates": m.separates,
                           "clusters": len(paired), "dropped": unpaired,
                           "oracle": is_oracle, "want": want, "status": status})
    return report


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("usage: gate <scenario> [--n 30] [--reps 1]")
        return 2
    # the core never imports a scenario; the entry point does it by name
    importlib.import_module(f"scenarios.{args[0]}.scenario")
    opt = lambda flag, default: (int(argv[argv.index(flag) + 1])
                                 if flag in argv else default)
    report = sweep(reg.get(args[0]), n=opt("--n", 30), reps=opt("--reps", 1))

    mark = {"ok": "ok  ", "fail": "FAIL", "empty": "----", "abstained": "n/a "}
    for r in report:
        got = "  none" if r["got"] is None else f"{r['got']:+.3f}"
        want = {"none": "== 0", "up": f">= {r['separates']}",
                "down": f"<= -{r['separates']}",
                "unscripted": "no scripted reader"}[r["want"]]
        print(f"{mark[r['status']]} {r['policy']:<24} {r['measurand']:<28} {got}  "
              f"(want {want}, {r['clusters']} clusters, {r['dropped']} unpaired)")

    failed = [r for r in report if r["status"] == "fail"]
    mute = [r for r in report if r["status"] == "abstained"]
    empty = sorted({r["measurand"] for r in report if r["status"] == "empty"})
    print("\ngate:", "PASS" if not failed and not empty else
          f"FAIL ({len(failed)} checks, {len(empty)} with no data)")
    if any(not r["oracle"] for r in failed):
        print("  a policy that reads nothing reproduces the result")
    if any(r["oracle"] for r in failed):
        print("  the oracle does not move it: the scenario measures nothing")
    if any(r["dropped"] for r in failed):
        print("  a cell was not served to every unit: the contrast covers less "
              "than the corpus it claims")
    for name in empty:
        print(f"  {name}: no cluster on both sides. Raise --n, or the corpus "
              "cannot support this stratum")
    if mute:
        print(f"  {len(mute)} blind checks selected out by a measurand's own "
              "filter: they committed nothing, so they faked nothing")
    return 1 if failed or empty else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
