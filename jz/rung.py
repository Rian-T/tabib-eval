"""One rung at a time. `docs/LADDER.md` is the doctrine, this file runs it.

A rung names the cells it needs, the number it reads and the condition that
number must meet. The condition lives in code, committed before the rung runs,
because the failure mode of a threshold kept in someone's head is that it
widens by exactly the amount needed once the number is on screen.

Each scenario declares its rungs in `scenarios/<name>/ladder.py`, next to the
scenario they grade; this file holds what every ladder shares: the Rung shape,
the readers, the golden-rule `spread`, and the commands. Adding a scenario is
adding a ladder file, not editing this one.

A rung that fails is a design to repair. A rung that passes is permission to
build the next one, never a finding about a model.

Usage:
  uv run python jz/rung.py <scenario>                          list the ladder
  uv run python jz/rung.py <scenario> <rung> <tag> [--n 40] [--reps 3]
  uv run python jz/rung.py <scenario> climb <tag>              up to the first fail
  uv run python jz/rung.py <scenario> <rung> --from <log dir>  grade past logs
  uv run python jz/rung.py <scenario> spread --from <log dir>  the last rung

`climb` exists because a rung costs an allocation and a model takes ten minutes
to load, not because several rungs may be read at once. It stops at the first
failure and prints nothing above it.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Callable

from analysis.collect import records
from tabib import measures, models
from tabib import scenario as reg
from tabib.measurand import interval, values

LOG = Path("logs/_rung")
NAN = float("nan")


@dataclass(frozen=True)
class Rung:
    """`check` returns the lines to print: (label, text, verdict or None).

    A line with a verdict is a condition; a line without is context the reader
    needs to interpret the ones that have one. A rung passes when every line
    that carries a verdict carries a true one.
    """
    id: str
    question: str
    cells: tuple[str, ...]
    condition: str
    check: Callable[[list[dict], object], list[tuple[str, str, bool | None]]]


def ladders() -> list[str]:
    """The scenarios that declare a ladder, found rather than listed here."""
    root = Path(__file__).resolve().parent.parent / "scenarios"
    return sorted(p.parent.name for p in root.glob("*/ladder.py"))


def ladder(name: str) -> tuple[Rung, ...]:
    return importlib.import_module(f"scenarios.{name}.ladder").LADDER


# --- reading a pile of records -------------------------------------------

def cell(rows: list[dict], name: str) -> list[dict]:
    return [r for r in rows if r.get("cell") == name]


def live(rows: list[dict], name: str) -> list[dict]:
    """One cell's sessions that ran to completion.

    Three ladders wrote this line, which is where a repeated helper stops being
    a coincidence. A session the serving stack cut short is a serving setting,
    and it belongs on no rung's numerator.
    """
    return [r for r in cell(rows, name) if measures.alive(r)]


def share(rows: list[dict], f: Callable[[dict], float]) -> float:
    return fmean(f(r) for r in rows) if rows else NAN


def band(sc, name: str, rows: list[dict]) -> tuple[float, float, float]:
    by_name = {m.name: m for m in sc.measurands}
    if name not in by_name:
        raise KeyError(f"{sc.name} declares no measurand {name!r}")
    return interval(values(by_name[name], rows))


def fmt(x: float) -> str:
    return "n/a" if x != x else f"{x:+.3f}"


def agreement(left: dict[str, float], right: dict[str, float]) -> float:
    """Rank correlation between two axes, over the models both of them place.

    Written out rather than imported: it is six lines, the panel is five points,
    and a dependency for that would be paid on every machine that runs the
    instrument.
    """
    shared = sorted(k for k in left.keys() & right.keys()
                    if left[k] == left[k] and right[k] == right[k])
    n = len(shared)
    if n < 3:
        return NAN
    rank = lambda d: {k: i for i, k in enumerate(sorted(shared, key=d.get))}
    a, b = rank(left), rank(right)
    d2 = sum((a[k] - b[k]) ** 2 for k in shared)
    return 1 - 6 * d2 / (n * (n * n - 1))


def sources(argv: list[str]) -> list[str]:
    """Every path after `--from`, so a shell glob reaches several models.

    A panel lives in one directory per model, and the rung that reads a panel
    cannot be handed one of them. Pointing at their common parent instead would
    pool every rung's copy of the same cell and silently multiply n.
    """
    at = argv.index("--from") + 1
    out = []
    for arg in argv[at:]:
        if arg.startswith("--"):
            break
        out.append(arg)
    return out


def moved(value: tuple[float, float, float], floor: tuple[float, float, float]
          ) -> bool:
    """Is a movement distinguishable from the instrument's own disagreement.

    Two intervals that overlap are one number seen twice. Comparing point
    estimates instead asks whether a mean landed exactly on another mean, which
    no finite sample ever does: the first climb failed a model on a placebo of
    +0.008 against a floor of exactly 0.000, and that placebo's own interval
    covered zero. The interval was computed, printed, and not used.

    This is the same question the condition always asked, tested the way the
    quantities allow it to be tested. It is not a widened threshold: a channel
    whose interval clears the floor's still fails, which is what one model does
    here at seven times its floor.
    """
    _, lo, hi = value
    _, flo, fhi = floor
    if any(x != x for x in (lo, hi, flo, fhi)):
        return False
    return lo > fhi or hi < flo


# --- the last rung, and it is about the panel rather than a model ---------

def spread(sc, rows: list[dict]) -> bool:
    """Do the models land in different places on the figure's own axes.

    The golden rule, as a rung. A contrast can be perfectly identified, no
    blind policy reproduces it, the oracle separates it, every floor is below
    it, and put every model on the same dot. Nothing is wrong with that number
    and nobody learns anything from it, so the design is what failed, not the
    panel.

    It is read on the axes the scenario declares in `plots`, because those are
    the axes a reader will look at, and it is the last rung because it is the
    only one that cannot be climbed one model at a time.

    **Every axis of a plot has to spread, not one of them.** The first version
    of this rung asked for one, which passes exactly the figure that motivated
    writing it: a panel spread across the abscissa and stacked on a single
    ordinate value is a ranking drawn as a plane, and drawing it that way is
    how a one-dimensional result gets presented as a choice.
    """
    models = sorted({r["model"] for r in rows})
    print(f"\n{sc.name}: do the models scatter, on the figure's own axes")
    print("  condition (written before the run): on every axis of a declared "
          "plot, the range across the panel exceeds every model's floor, and "
          "the two axes do not order the panel alike (|rho| < 0.9)")
    print(f"  {len(models)} models\n")
    if len(models) < 2:
        print("   X  one model is not a panel")
        return False

    floors = {}
    for tag in models:
        mine = [r for r in rows if r["model"] == tag]
        f, _, fhi = band(sc, "differs_from_its_twin", mine)
        floors[tag] = max(abs(f), abs(fhi)) if f == f else 0.0
    room = max(floors.values())

    def axis(name: str) -> dict[str, float]:
        return {tag: band(sc, name, [r for r in rows if r["model"] == tag])[0]
                for tag in models}

    ok = True
    for pair in sc.plots:
        print(f"  plot: {pair[0]} against {pair[1]}")
        got = []
        for name in pair:
            per = axis(name)
            got.append(per)
            seen = [v for v in per.values() if v == v]
            rng = max(seen) - min(seen) if len(seen) > 1 else NAN
            wide = rng == rng and rng > room
            ok = ok and wide
            line = "  ".join(f"{t.split('/')[-1]}={fmt(v)}"
                             for t, v in per.items())
            print(f" {' ok' if wide else '  X'}  {name:<40} range {fmt(rng)}"
                  f"\n      {line}")
        # Spread on both axes is not enough. Two axes that order the panel the
        # same way are one axis drawn twice: the dots fall on a line, every
        # model is dominated or dominating, and a reader has no choice to make.
        # A frontier needs at least one inversion between the two orderings.
        rho = agreement(got[0], got[1])
        loose = rho == rho and abs(rho) < 0.9
        ok = ok and loose
        print(f" {' ok' if loose else '  X'}  the two axes order the panel "
              f"differently        rho {fmt(rho)}")
    print(f"\n      largest floor on the panel                 {fmt(room)}")
    print("\n  ->", "every axis separates the panel and they disagree about "
          "it; the figure offers a choice" if ok else
          "this is a ranking pretending to be a choice: an axis puts the whole "
          "panel in one place, or both axes order it alike. Change the axis or "
          "drop the plot, do not publish the line.")
    return ok


# --- running and reporting ------------------------------------------------

def run(sc, rung: Rung, tag: str, n: int, reps: int) -> list[dict]:
    """Serve only the cells this rung needs, into a directory of its own.

    Set aside first, never deleted: `records` reads every log under a
    directory, so a reused one silently pools yesterday's code with today's and
    multiplies n without saying so. This used to be an rmtree, and a reclimb
    destroyed 101 readable sessions nobody had copied: the third time in this
    project's life that our own tooling deleted data. Renamed aside instead:
    the fresh directory is just as clean, and what was measured stays on disk.
    """
    from datetime import datetime
    from inspect_ai import eval as inspect_eval

    out = LOG / tag / f"{sc.name}_{rung.id}"
    if out.exists():
        out.rename(out.with_name(
            f"{out.name}.replaced-{datetime.now():%Y%m%dT%H%M%S}"))
    rows = []
    for name in rung.cells:
        into = out / name
        inspect_eval(reg.build_task(sc, name, reps=reps, n=n),
                     model=models.model(tag), log_dir=str(into), display="none")
        rows += records(into, include_pilot=True)
    return rows


def report(sc, rung: Rung, rows: list[dict]) -> bool:
    print(f"\n{sc.name} {rung.id}: {rung.question}")
    print(f"  condition (written before the run): {rung.condition}")
    print(f"  {len(rows)} cases over cells {', '.join(rung.cells)}\n")
    lines = rung.check(rows, sc)
    for label, text, ok in lines:
        mark = "   " if ok is None else (" ok" if ok else "  X")
        print(f" {mark}  {label:<48} {text}")
    passed = all(ok for _, _, ok in lines if ok is not None)
    # a missing number and a number that missed its condition are different
    # facts, and calling both a failed design sends the repair to the wrong
    # place: one is a cell that did not run, the other is a cell that did
    blank = any(ok is False and text.startswith(("n/a", "nan"))
                for _, text, ok in lines)
    if passed:
        print(f"\n  -> {rung.id} passes; the next rung may be built")
    elif blank:
        print(f"\n  -> {rung.id} has no data. These records do not carry the "
              "cells it reads; run it rather than grade it.")
    else:
        print(f"\n  -> {rung.id} FAILS. Repair the design. Do not widen the "
              "condition, and do not read the rungs above it.")
    return passed


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    name = args[0]
    if name not in ladders():
        print(f"unknown scenario {name!r}; the ladder covers {ladders()}")
        return 2
    importlib.import_module(f"scenarios.{name}.scenario")
    sc = reg.get(name)
    rungs = ladder(name)
    if len(args) == 1:
        print(f"\n{name}\n")
        for r in rungs:
            print(f"  {r.id}  {r.question}\n      cells: {', '.join(r.cells)}"
                  f"\n      pass:  {r.condition}\n")
        return 0

    opt = lambda flag, default: (int(argv[argv.index(flag) + 1])
                                 if flag in argv else default)
    if args[1].lower() == "spread":
        if "--from" not in argv:
            print("spread reads a panel, so it grades logs: pass --from <dir>")
            return 2
        source = sources(argv)
        rows = [r for d in source for r in records(d, include_pilot=True)
                if r.get("scenario") == name]
        if not rows:
            print(f"no {name} records under {source}")
            return 2
        return 0 if spread(sc, rows) else 1

    if args[1].lower() == "climb":
        if len(args) < 3:
            print("a tag is needed to climb")
            return 2
        # `--carry-on` climbs past a broken rung, printing it above everything
        # that follows. It is for a rung the panel has already shown to break on
        # some models and not others: the instrument works there, it separated
        # the panel, and stopping would throw away the models the figure exists
        # to tell apart. It is never for a rung that broke on everyone.
        keep_going = "--carry-on" in argv
        broken: list[str] = []
        for r in rungs:
            rows = run(sc, r, args[2], opt("--n", 40), opt("--reps", 3))
            if broken:
                print(f"\n[carried past {', '.join(broken)}. Every number "
                      "below is read under that.]")
            if not report(sc, r, rows):
                broken.append(r.id)
                if not keep_going:
                    print(f"\n=== the ladder stops at {sc.name} {r.id}. The "
                          "rungs above it were not run and would not be "
                          "readable.")
                    return 1
        if broken:
            print(f"\n=== {sc.name}: climbed to the top, carrying "
                  f"{', '.join(broken)}. Nothing above them is publishable "
                  "without them printed beside it.")
            return 1
        print(f"\n=== {sc.name}: every rung passes at this sample size.")
        return 0

    rung = next((r for r in rungs if r.id == args[1].upper()), None)
    if rung is None:
        print(f"unknown rung {args[1]!r}; {name} has "
              f"{[r.id for r in rungs]}")
        return 2

    if "--from" in argv:
        source = sources(argv)
        rows = [r for d in source for r in records(d, include_pilot=True)
                if r.get("scenario") == name and r.get("cell") in rung.cells]
        if not rows:
            print(f"no {name} records for cells {rung.cells} under {source}")
            return 2
        print(f"\n[grading past logs from {source}. They were produced by "
              "whatever code was checked out then, which is not necessarily "
              "this code.]")
    else:
        if len(args) < 3:
            print("a tag is needed to run a rung; or pass --from <log dir>")
            return 2
        rows = run(sc, rung, args[2], opt("--n", 40), opt("--reps", 3))

    return 0 if report(sc, rung, rows) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
