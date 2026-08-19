"""Three verbs over the instrument: load a package, run it, compare two runs.

    import tabib

    package = tabib.load("companion-world")
    result = tabib.run(agent="dev", world=package, repetitions=1)
    tabib.compare(result)

Nothing here measures anything. The engine, the measurands and the analysis are
where they were; this file only offers what a package declares and refuses the
rest. A cell outside the package's protocol is not runnable, because the
conditions under which the numbers mean something travel with the world and not
with the caller's discipline.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass, field

from .measurand import Measurand, interval, values
from .nulls import degenerate
from .scenario import Scenario
from .worlds import WorldError, load_world


@dataclass(frozen=True)
class Protocol:
    """The test plan a package declares, and the whole menu `run` offers."""
    cells: tuple[str, ...]
    contrasts: tuple[str, ...]      # measurands identified as a difference
    rates: tuple[str, ...]          # measurands printed without an interval
    claims: tuple[tuple[str, str], ...]   # one movement against another
    figure: tuple[tuple[str, str], ...]   # the declared pair of axes


@dataclass(frozen=True)
class Package:
    """A world and the science served on it, resolved and verified."""
    name: str
    world: object                   # the package module, with MANIFEST attached
    scenario: Scenario
    protocol: Protocol = field(init=False)

    def __post_init__(self):
        sc = self.scenario
        object.__setattr__(self, "protocol", Protocol(
            cells=sc.cells,
            contrasts=tuple(m.name for m in sc.measurands if m.contrast),
            rates=tuple(m.name for m in sc.measurands if not m.contrast),
            claims=sc.compares,
            figure=sc.plots))

    @property
    def noise_floor(self) -> tuple[str, ...]:
        """The measurands that read the same cell served twice.

        Derived from the cell names: a floor is a contrast between `x_twin` and
        `x`. There is no manifest field for it today, so a package that names
        its twin cells differently has no floor here and `compare` says so
        rather than inventing one.
        """
        return tuple(m.name for m in self.scenario.measurands
                     if m.contrast and m.cells[0] == m.cells[1] + "_twin")

    @property
    def controls(self) -> dict:
        """The scripted agents the package ships, by name.

        Every policy the core derives from the declared acts, the scenario's
        own, and its oracle. `analysis.gate` runs exactly this dict; a package
        whose probes cannot tell them apart fails there.
        """
        return {**degenerate(self.scenario.acts), **dict(self.scenario.policies),
                "oracle": self.scenario.oracle}


def load(ref: str) -> Package:
    """A package, resolved from disk or from the local cache, hashes verified.

    The manifest names the scenario: a bare name is a module under
    `scenarios/`, a path ending in `.py` is a file inside the package. A
    package that names none cannot be run through this API.
    """
    world = load_world(ref)
    declared = world.MANIFEST.get("world", {}).get("scenario")
    if not declared:
        raise WorldError(
            f"{ref} declares no scenario: add `scenario = \"<name>\"` to its "
            "manifest, or load the world alone with tabib.worlds.load_world")
    module = (_from_file(world.PATH / declared) if declared.endswith(".py")
              else importlib.import_module(f"scenarios.{declared}.scenario"))
    return Package(name=world.MANIFEST["world"]["name"], world=world,
                   scenario=module.SCENARIO)


def _from_file(at):
    spec = importlib.util.spec_from_file_location(f"tabib_pkg.{at.stem}", at)
    if spec is None or spec.loader is None:
        raise WorldError(f"cannot import {at}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*, agent, world: Package, cells: tuple[str, ...] | None = None,
        repetitions: int = 1, n: int = 150, mode: str = "pilot",
        name: str | None = None) -> dict:
    """Run a package against one or more agents. Returns the run's record.

    `cells` defaults to everything the protocol declares; naming one it does
    not declare is refused here rather than measured and discarded later.
    """
    from . import campaign, runs as run_module

    cells = tuple(cells or world.protocol.cells)
    unknown = [c for c in cells if c not in world.protocol.cells]
    if unknown:
        raise ValueError(
            f"{world.name} does not declare {unknown}: its protocol serves "
            f"{list(world.protocol.cells)}. A package runs its own plan or "
            "nothing.")
    agents = [agent] if isinstance(agent, str) else list(agent)
    label = name or run_module.new(world.scenario.name)
    ok, log_dir = campaign.launch(world.scenario, label, agents, n=n,
                                  reps=repetitions, mode=mode, cells=cells)
    return {"package": world, "scenario": world.scenario.name, "name": label,
            "log_dir": log_dir, "cells": cells, "agents": agents,
            "complete": ok}


def _rows(result: dict) -> list[dict]:
    from analysis.collect import carry, records

    rows = [r for r in records(result["log_dir"], include_pilot=True)
            if r.get("scenario") == result["scenario"]]
    for cell, key, name in result["package"].scenario.carries:
        carry(rows, cell=cell, key=key, as_=name)
    return rows


def _floor(package: Package, m: Measurand) -> Measurand | None:
    """The twin contrast reading the same number as `m`, if the package has one.

    Matched on the function, which is what makes it the same number: a floor
    computed from a different `y` would be a floor under something else.
    """
    return next((f for f in package.scenario.measurands
                 if f.name in package.noise_floor and f.y is m.y and f is not m),
                None)


def compare(result: dict, *, baseline: dict | None = None) -> list[dict]:
    """The package's contrasts, per agent, with their interval and their floor.

    With a `baseline`, each contrast is differenced against the same contrast
    in that run, paired on the cluster, so a change between two runs gets its
    own interval instead of two numbers side by side. Both runs must come from
    the same package.

    `beyond_floor` is None where the package declares no twin for a contrast:
    an effect nobody put a floor under is neither above one nor below it.
    """
    package = result["package"]
    if baseline is not None and baseline["package"].name != package.name:
        raise ValueError("two runs of different packages do not compare")
    rows = _rows(result)
    was = _rows(baseline) if baseline is not None else None
    out = []
    for m in package.scenario.measurands:
        if not m.contrast:
            continue
        floor = _floor(package, m)
        for model in sorted({r["model"] for r in rows}):
            mine = [r for r in rows if r["model"] == model]
            got = values(m, mine)
            if was is not None:
                theirs = dict(values(m, [r for r in was if r["model"] == model]))
                got = [(c, v - theirs[c]) for c, v in got if c in theirs]
            point, lo, hi = interval(got) if got else (float("nan"),) * 3
            level = (abs(interval(values(floor, mine))[0])
                     if floor and values(floor, mine) else None)
            out.append({"measurand": m.name, "model": model, "point": point,
                        "lo": lo, "hi": hi, "clusters": len(got),
                        "floor": level, "paired_against": (
                            baseline["name"] if baseline is not None else None),
                        "beyond_floor": None if level is None
                        else bool(lo > level or hi < -level)})
    return out
