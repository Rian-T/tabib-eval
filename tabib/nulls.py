"""The acts a scenario admits, and the policies the core derives from them.

The two live in one module because that is the point: a scenario says what a
model is allowed to do, and the core, not the scenario, enumerates the
policies that do it without reading anything. A policy blind to the manipulation
contributes the same to both sides of a within-cluster contrast, so it must come
out at exactly zero. When a scenario supplies its own list of standards instead,
the blind spot of the scenario becomes the blind spot of its calibration.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from inspect_ai.model import ModelOutput

# `get_model` disables memoization for mockllm on its own, so each policy gets
# its own model object rather than a cached one from a previous policy.
MOCK = "mockllm/model"

_DUMMY = {"string": "x", "integer": 1, "number": 1.0, "boolean": False}


@dataclass(frozen=True)
class Act:
    """A terminal act. `payload` names the argument carrying the verdict, which
    is scored instead of prose; `values` lists it when it is a closed set."""
    name: str
    payload: str = ""
    values: tuple[str, ...] = ()

    def __post_init__(self):
        if self.values and not self.payload:
            raise ValueError(f"act {self.name!r}: values need the argument that "
                             "carries them")


def points(acts: tuple[Act, ...]) -> list[tuple[str, dict]]:
    """(act name, payload override) for every distinguishable action."""
    return [(a.name, {a.payload: v}) if a.values else (a.name, {})
            for a in acts for v in (a.values or (None,))]


def _min_args(tools, name: str) -> dict:
    """Minimal valid arguments for a tool, from its schema, so a policy stays
    scenario-agnostic while argument validation stays exercised."""
    for t in tools:
        if t.name == name:
            props = t.parameters.properties or {}
            return {k: _DUMMY.get(getattr(props[k], "type", "string"), "x")
                    for k in (t.parameters.required or [])}
    return {}


def _call(tools, name: str, override: dict) -> ModelOutput:
    return ModelOutput.for_tool_call(MOCK, name, {**_min_args(tools, name), **override})


def label(name: str, override: dict) -> str:
    return f"const:{name}" + "".join(f"={v}" for v in override.values())


def degenerate(acts: tuple[Act, ...]) -> dict[str, Callable]:
    """Every policy blind to the manipulation, enumerated from the acts.

    `memoryless` is seeded from `config.seed`, which derives from the sample id
    and not from the served text, so both sides of a contrast draw the same
    action. That is what makes the null exactly zero rather than zero in
    expectation, and it is the only thing that would catch a seed derived from
    something that varies between cells.
    """
    space = points(acts)

    def constant(name, override):
        return lambda messages, tools, tool_choice, config: _call(tools, name, override)

    def silent(messages, tools, tool_choice, config):
        return ModelOutput.from_content(MOCK, "Rien à signaler.")

    def memoryless(messages, tools, tool_choice, config):
        rng = random.Random(getattr(config, "seed", None) or 0)
        return _call(tools, *rng.choice(space))

    def consulting(messages, tools, tool_choice, config):
        """Calls every non-act tool once, then answers constantly.

        Without it, a scenario whose manipulation sits behind a lookup is never
        reached by any blind policy: they all commit an act on the first turn,
        both cells serve the same prompt, and every null comes out at zero by
        construction rather than by measurement.
        """
        names = {a.name for a in acts}
        done = {c.function for m in messages
                for c in (getattr(m, "tool_calls", None) or [])}
        pending = [t.name for t in tools if t.name not in names and t.name not in done]
        if pending:
            return _call(tools, pending[0], {})
        return _call(tools, *space[0])

    return {**{label(n, o): constant(n, o) for n, o in space},
            "silent": silent, "memoryless": memoryless, "consulting": consulting}
