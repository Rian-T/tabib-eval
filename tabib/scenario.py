"""Where a scenario declares itself, and the only file the rest of the core
reads it through.

Adding a scenario is one `register` call and no edit anywhere else. The gate,
the launcher and collection all work from this record.

`oracle` is required. A gate that only checks that blind policies score zero
also passes a scenario where nothing scores anything, so the positive control is
part of the declaration rather than an optional extra.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from inspect_ai import Task

from .measurand import Measurand
from .nulls import Act, degenerate
from .session import session
from .task import cell_task, make_samples


@dataclass(frozen=True)
class Scenario:
    name: str
    acts: tuple[Act, ...]                # the terminal acts a model may commit
    system: str                          # the system prompt, the same for all cells
    rows: Callable                       # (*, n, seed) -> one dict per unit
    build: Callable                      # (cell, row) -> World
    measurands: tuple[Measurand, ...]
    oracle: Callable                     # a scripted policy that has the behaviour
    # pairs of contrasts whose difference is the claim: "this movement is
    # larger than that one". Named here so the difference gets an interval
    # instead of being left to the reader's eye.
    compares: tuple[tuple[str, str], ...] = ()
    # (cell, key, name): a fact from one served version carried onto every
    # record of the same unit, so a contrast can be split by what the model did
    # elsewhere. Declared here because which cell means what is scenario
    # knowledge, and analysis that hardcodes a cell name stops being generic.
    carries: tuple[tuple[str, str, str], ...] = ()
    # `budget(cell) -> (max_steps, max_tokens)`. A scenario whose cells hold a
    # different number of cases cannot run on one fixed step count: the longest
    # cell would end on the budget and "in session" would mean "ran out". Left
    # unset, the session's own defaults apply, which is every scenario but the
    # one that needed this.
    budget: Callable | None = None
    # (x, y): two measurands to place a model against each other, when the
    # figure is a position and not a claim. Separate from `compares` on purpose:
    # a difference of two rates is reproducible by a policy that answers a
    # constant, so it gets a plane and never an interval.
    plots: tuple[tuple[str, str], ...] = ()
    # Scripted policies the gate runs beside the ones the core derives from the
    # acts, as (name, policy). What counts as blind can be a property of the
    # scenario: where a decision is one act carrying a payload the core's own
    # policies cover it, and where it is a session of several calls they answer
    # nothing at all and are filtered out rather than scored. A scenario needing
    # a policy that acts and reads nothing declares it here.
    policies: tuple[tuple[str, Callable], ...] = ()

    def __post_init__(self):
        if not self.acts:
            raise ValueError(f"scenario {self.name!r} declares no act")
        if len({a.name for a in self.acts}) != len(self.acts):
            raise ValueError(f"scenario {self.name!r}: duplicate act name")
        if not self.measurands:
            raise ValueError(f"scenario {self.name!r} declares no measurand")
        if not callable(self.oracle):
            raise ValueError(f"scenario {self.name!r} needs an oracle policy")
        # a scenario policy sharing a name with one of the core's would replace
        # it in the gate's own dict, and the check it silences is the one the
        # scenario has the least standing to remove
        clash = {n for n, _ in self.policies} & ({"oracle"} | set(degenerate(self.acts)))
        if clash:
            raise ValueError(
                f"scenario {self.name!r} declares policies the core already "
                f"derives: {sorted(clash)}. A scenario policy that shadows a "
                "blind one removes a control rather than adding one")
        named = {m.name for m in self.measurands if m.contrast}
        for pair in self.compares:
            missing = set(pair) - named
            if missing:
                raise ValueError(f"scenario {self.name!r} compares {missing}, "
                                 "which is not a declared contrast")
        every = {m.name for m in self.measurands}
        for pair in self.plots:
            missing = set(pair) - every
            if missing:
                raise ValueError(f"scenario {self.name!r} plots {missing}, "
                                 "which is not a declared measurand")

    @property
    def cells(self) -> tuple[str, ...]:
        """Every served version the measurands name, in a stable order. Derived,
        so a cell nobody measures is never served and a cell a measurand names
        is never left out."""
        return tuple({c: None for m in self.measurands for c in m.cells})


# What a scenario declaring no budget receives, and it is the session's own
# defaults spelled once. Named rather than inlined so a test can assert the two
# have not drifted: a scenario that predates the budget field must keep running
# on exactly the numbers it ran on before the field existed.
DEFAULT_BUDGET = (8, 2000)

_SCENARIOS: dict[str, Scenario] = {}


def register(scenario: Scenario) -> Scenario:
    if scenario.name in _SCENARIOS:
        raise ValueError(f"scenario {scenario.name!r} is already registered")
    _SCENARIOS[scenario.name] = scenario
    return scenario


def get(name: str) -> Scenario:
    if name not in _SCENARIOS:
        raise KeyError(f"unknown scenario {name!r}; registered: {sorted(_SCENARIOS)}")
    return _SCENARIOS[name]


def build_task(scenario: Scenario, cell: str, *, reps: int = 1,
               mode: str = "pilot", **row_kw) -> Task:
    """A runnable task from the declaration alone, so the gate runs a scenario
    exactly the way a campaign does."""
    steps, tokens = scenario.budget(cell) if scenario.budget else DEFAULT_BUDGET
    return cell_task(
        scenario.name, cell, reps=reps, mode=mode,
        samples=make_samples(scenario.rows(**row_kw)),
        solver=session(cell, scenario.build, scenario.system, acts=scenario.acts,
                       max_steps=steps, max_tokens=tokens))
