"""Launch, resume and analyse any registered scenario.

    uv run python -m tabib.campaign source_fidelity smoke --models dev --n 2
    uv run python -m tabib.campaign yielding_boundary claim --n 100 --reps 5 --mode claim

The second argument is a run name. Launch, resume and analysis all take the same
string, and relaunching a name continues that set rather than starting a new one.

Adding a scenario means registering it, not copying this file. Entry points may
import a scenario by name; core modules never do.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import subprocess
import sys
from pathlib import Path

from inspect_ai import eval_set

from analysis import watch  # noqa: F401  (importing arms the live invariants)
from tabib import models, runs
from tabib import scenario as reg


def fingerprint(root: str = "scenarios") -> dict[str, str]:
    """{path: sha256} over everything a scenario serves.

    The one thing an Inspect log does not record on its own. It already carries
    the commit, the dirty flag, the package versions and the model config; a
    served text edited between two launches is what stays invisible.
    """
    return {str(f): hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            for f in sorted(Path(root).rglob("*"))
            if f.is_file() and f.suffix in (".txt", ".csv", ".md")}


def dirty() -> bool:
    return bool(subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip())


def parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="campaign", description=__doc__)
    p.add_argument("scenario")
    p.add_argument("run", nargs="?", default=None, help="run name; defaults to a dated one")
    p.add_argument("--models", default=",".join(models.PANEL))
    p.add_argument("--n", type=int, default=150)
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--mode", choices=("pilot", "claim"), default="pilot")
    return p.parse_args(argv)


def launch(scenario, name: str, tags: list[str], *, n: int, reps: int,
           mode: str, cells: tuple[str, ...] | None = None) -> tuple[bool, str]:
    """Run one scenario over its cells. Returns (complete, log directory)."""
    # a claim from a dirty tree is not reproducible; the log would record the
    # tree as dirty after the fact rather than refusing up front
    if mode == "claim" and dirty():
        raise SystemExit("claim mode from a dirty tree: commit first")

    tasks = [reg.build_task(scenario, cell, reps=reps, mode=mode, n=n)
             for cell in (cells or scenario.cells)]
    log_dir = runs.log_dir(name, scenario.name)

    ok, _ = eval_set(
        tasks=tasks, model=[models.model(t) for t in tags],
        log_dir=log_dir,
        # content is the one thing the log does not fingerprint on its own, and
        # that includes the reference table the served passages are built from
        metadata={"content": fingerprint()},
        log_shared=30,        # so a run is watchable from another machine
        # one sample's failure is that sample's data, not the batch's: a model
        # that emits a malformed tool call in long sessions was killing every
        # in-flight session with it (CancelledError), and the resume loop then
        # re-measured only the survivors: attrition with a selection bias.
        # The failed sample stays in the log as an error and is read as a
        # degraded turn, which is what it is.
        fail_on_error=False,
        display="rich", **runs.KEEP_LOGS)
    print(f"run {name}: {'complete' if ok else 'incomplete, relaunch the same name'}")
    return ok, log_dir


def main(argv: list[str]) -> int:
    args = parse(argv)
    importlib.import_module(f"scenarios.{args.scenario}.scenario")
    scenario = reg.get(args.scenario)
    ok, _ = launch(scenario, args.run or runs.new(scenario.name),
                   args.models.split(","), n=args.n, reps=args.reps, mode=args.mode)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
