"""One case, its tools, and the single place everything passes through.

A scenario builds a world for one served version of one unit: the prompt the
model sees, and the tools it may call. `World.call` is the only way any tool
runs, which is what makes the truth channel auditable: every call logs what was
served next to what is true, and serving something other than the truth without
declaring it is an error rather than a subtlety.

The first terminal act closes the case. Which tools are terminal is not declared
here: the session marks them from the acts the scenario registered, so the two
cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from inspect_ai.log import transcript
from inspect_ai.tool import ToolDef, ToolParam, ToolParams


@dataclass(frozen=True)
class ToolSpec:
    """`handler(world, args) -> (served, truth)`; `params` maps an argument name
    to (json type, description)."""
    name: str
    description: str
    params: dict[str, tuple[str, str]] = field(default_factory=dict)
    handler: Callable = None
    optional: tuple[str, ...] = ()      # arguments a model may leave out
    injected: bool = False              # allowed to serve other than the truth
    referential: bool = False           # queries the external reference


class WorldError(ValueError):
    pass


class World:
    def __init__(self, *, prompt: str, tools: list[ToolSpec],
                 meta: dict | None = None, markers: tuple[str, ...] = (),
                 followup: Callable | None = None):
        # `followup(world) -> str | None` reopens the case once the first act is
        # in: the text goes back as a user turn and the model may act again. It
        # takes no argument about what was committed, so the hand-over cannot
        # vary with the answer, since a follow-up that quoted the decision back would
        # change the served content at the same time as the manipulation.
        self.followup = followup
        self.prompt = prompt
        self.meta = dict(meta or {})
        self.markers = tuple(m.lower() for m in markers)
        self.terminal: set[str] = set()     # set by the session from the acts
        self.act: dict | None = None
        self.calls: list[str] = []
        self.consulted = False
        self.warned = False
        self._specs = {t.name: t for t in tools}
        if len(self._specs) != len(tools):
            raise WorldError("duplicate tool name")
        self._step = 0

    @property
    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def step(self) -> int:
        self._step += 1
        return self._step

    @property
    def turn(self) -> int:
        """Which model turn is executing, 1-based.

        The session increments the step once per generation, so a handler can
        tell a first turn from a later one. A queue world needs it: whether a
        model opens one file or several on its very first turn is what decided
        the whole session in the v1 logs.
        """
        return self._step

    def call(self, name: str, args: dict) -> str:
        spec = self._specs[name]
        served, truth = spec.handler(self, args)
        if served != truth and not spec.injected:
            raise WorldError(f"served != truth on '{name}' without injected=True")
        if name in self.terminal and self.act is None:
            self.act = {"tool": name, "args": dict(args)}
        self.calls.append(name)
        if spec.referential:
            # querying the reference and finding danger in it are two facts.
            # Folded together, "never checked" cannot be told from "checked, and
            # it said nothing": the whole answer wherever nothing is correct.
            # Both hold when the channel serves a manipulated version: the query
            # happened, and `truth` still carries the honest entry
            self.consulted = True
            self.warned = self.warned or any(m in truth.lower() for m in self.markers)
        transcript().info(
            {"type": "tool_truth", "step": self._step, "tool": name, "args": args,
             "served": served, "truth": truth, "injected": spec.injected},
            source="tabib")
        return served


_PY = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}
_EMPTY = {"string": '""', "integer": "0", "number": "0.0", "boolean": "False"}


def tooldefs(world: World) -> list[ToolDef]:
    """World.call wrapped as Inspect tools.

    A typed signature is generated per spec rather than accepting `**kwargs`.
    ToolDef does not need it, but the typed path coerces argument types and
    rejects a missing required argument. That rejection costs the model its
    whole turn, so an argument that is not part of the measurement (a citation,
    a justification) belongs in `optional`: otherwise a model that omits it is
    recorded as having done nothing, and that lands in the contrast.
    """
    def make(spec: ToolSpec):
        # `optional` has to reach the generated signature, not only the schema:
        # a parameter absent from `required` but without a default still raises
        # on the typed path, which is the rejection this exists to prevent.
        # Defaulted parameters must come last, so the order follows.
        keys = sorted(spec.params, key=lambda k: k in spec.optional)
        sig = ", ".join(
            f"{k}: {_PY[spec.params[k][0]]}"
            + (f" = {_EMPTY[spec.params[k][0]]}" if k in spec.optional else "")
            for k in keys)
        body = "{" + ", ".join(f"{k!r}: {k}" for k in keys) + "}"
        ns = {"_world": world, "_name": spec.name}
        exec(f"async def execute({sig}):\n    return _world.call(_name, {body})", ns)
        return ToolDef(ns["execute"], name=spec.name, description=spec.description,
                       parameters=ToolParams(
                           properties={k: ToolParam(type=spec.params[k][0],
                                                    description=spec.params[k][1])
                                       for k in keys},
                           required=[k for k in spec.params
                                     if k not in spec.optional]))
    return [make(s) for s in world.specs]
