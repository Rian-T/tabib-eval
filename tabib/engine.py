"""The engine: state, items, tasks, affordances, and no idea what any of it is.

`docs/ENGINE.md` is the specification. This is the contract a world is written
against, and it is the whole of what the engine knows:

    Item         an opaque dict; the engine reads `id` and nothing else
    Collection   an ordered set of items, and the policy governing access
    Task         a todo the world holds, stated factually, binding nothing
    Affordance   what the world offers; a handler, served and traced uniformly
    Response     what an affordance returns; never an exception
    State        collections, cursors, tasks, and the engine's own trace

The engine writes the trace itself, before the world's handler runs, **and
refuses a handler that writes it back**. That is not a convenience: a rung graded
from fields the audited code derives passes exactly when that code agrees with
itself, which is how a verification line came to be true by construction
(`docs/DEFECTS.md`). A probe reads the trace, the trace is the engine's, so it can
disagree with the world.

What that does not cover, and the honest limit: a world's answer *is* its
`Response`, so a world that declares a refusal accepted has not falsified the
trace, it has lied in it. No mechanism here can tell that from a world that meant
it, and VAGABOND is what reads the answers.

Nothing here requires progress. No affordance may refuse a call because a task is
open, unaddressed, or out of order; that is the difference between a world and a
corridor, and `VAGABOND` is what checks it.

It sits above Inspect and changes nothing below: a world is served through the
existing `World`/`ToolSpec` chokepoint, so tool conversion, the loop, resume and
the log are untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .world import ToolSpec, World, WorldError

VERSION = "0.1.0"

Item = dict


@dataclass(frozen=True)
class Response:
    """What an affordance returns.

    `accepted=False` is a *world* refusal ("that file is already closed") with
    its own text. The engine never invents one and never raises in its place.
    `effect` names the state change in one word, for the trace.
    """
    served: str
    truth: str = ""
    effect: str = ""
    accepted: bool = True
    # Which item this call concerned, when the arguments do not say. A reference
    # is often queried by content rather than by id, and only the world can know
    # whether that content was about the item it has open. The engine guessing
    # "whatever was open" credits a query about something else to the open item,
    # which is the defect this field exists to retire.
    about: str = ""

    def __post_init__(self):
        if not str(self.served).strip():
            raise ValueError("an affordance must answer something: an empty "
                             "response is a wall with no message on it")


@dataclass(frozen=True)
class Task:
    """A todo the world holds. It is consultable and it binds nothing.

    `closed_by` names the affordances whose call closes it. The engine can tell
    whether a task was addressed, in what order, and by what, and it cannot make
    the agent address it. A world whose state stops making sense when the todo
    list is ignored has failed the coherence properties.
    """
    id: str
    statement: str
    item_id: str | None = None
    closed_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class Collection:
    """An ordered set of items and the policy governing access to them.

    `access(state, collection, item_id) -> Item | None`. The engine offers the
    two policies it has evidence for and privileges neither: `any_item`, and
    `head_only` for a world that hands things over one at a time. Which one a
    world uses is the world's decision, never the engine's.
    """
    name: str
    items: list[Item]
    access: Callable[["State", "Collection", str], Item | None] = None


@dataclass(frozen=True)
class Affordance:
    """What the world offers, and how the engine serves it.

    `handler(state, args) -> Response`. `item_arg` names the parameter carrying
    an item id, which is what lets the engine attribute a call to a task without
    knowing what the item is.
    """
    name: str
    description: str
    params: dict[str, tuple[str, str]]
    handler: Callable[["State", dict], Response]
    item_arg: str = ""
    optional: tuple[str, ...] = ()
    referential: bool = False
    injected: bool = False


def any_item(state: "State", coll: Collection, item_id: str) -> Item | None:
    return next((i for i in coll.items if str(i.get("id")) == item_id), None)


def head_only(state: "State", coll: Collection, item_id: str) -> Item | None:
    """Only the item at the cursor. A world's choice, offered here because two
    scenarios needed it; the engine does not care which policy a world picks."""
    head = state.head(coll.name)
    return head if head is not None and str(head.get("id")) == item_id else None


class State:
    """The world's state. The engine owns the trace, the cursors and the ledger;
    `meta` is the world's own dict and the engine never reads it."""

    def __init__(self, collections: list[Collection], tasks: list[Task],
                 meta: dict | None = None):
        self.collections = {c.name: c for c in collections}
        self.cursor: dict[str, int] = {c.name: 0 for c in collections}
        self.tasks = list(tasks)
        self.trace: list[list] = []
        self.ledger: dict[str, dict] = {}
        self.meta = dict(meta or {})

    # --- items ----------------------------------------------------------
    def head(self, name: str) -> Item | None:
        """The item at the cursor, or None once the collection is worked out."""
        coll, at = self.collections[name], self.cursor[name]
        return coll.items[at] if at < len(coll.items) else None

    def reach(self, name: str, item_id: str) -> Item | None:
        """The item a call names, if the collection's policy allows it."""
        coll = self.collections[name]
        policy = coll.access or any_item
        return policy(self, coll, str(item_id))

    def advance(self, name: str) -> Item | None:
        """Move the cursor on and return what is now open.

        The engine offers the cursor and takes no position on what moves it: a
        world may advance on an act, on a pull, on both, or never. A collection
        that only advances by acting makes the act the only way forward, which is
        a corridor, but that is the world's decision to defend, not the engine's.
        """
        self.cursor[name] = min(self.cursor[name] + 1,
                                len(self.collections[name].items))
        return self.head(name)

    def open_items(self) -> list[str]:
        """The id at each collection's cursor: what the world has open right now."""
        return [str(item.get("id")) for name in sorted(self.collections)
                if (item := self.head(name)) is not None]

    # --- tasks ----------------------------------------------------------
    def open_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.id not in self.ledger]

    def close(self, task: Task, by: str, at: int) -> None:
        self.ledger[task.id] = {"by": by, "at": at, "rank": len(self.ledger) + 1}

    # --- what the world looks like from outside --------------------------
    def describe(self) -> str:
        """The state in one line, without the world's help.

        Generic on purpose: a world that has to write its own renderer would be
        a world that can fail to. VAGABOND asks only that this does not raise:
        which it will if a cursor ran off, a collection lost its items, or the
        ledger points at a task nobody declared.
        """
        parts = [f"{name}: {self.cursor[name]}/{len(coll.items)}"
                 for name, coll in sorted(self.collections.items())]
        known = {t.id for t in self.tasks}
        stray = sorted(set(self.ledger) - known)
        if stray:
            raise ValueError(f"the ledger closed tasks nobody declared: {stray}")
        return (f"{', '.join(parts)}; tasks {len(self.ledger)}/{len(self.tasks)} "
                f"closed; {len(self.trace)} calls")


# An event is [turn, affordance, args, accepted, effect, open items].
#
# An event is [turn, affordance, args, accepted, effect, open items, about].
#
# `open items` is what the world had at its cursors when the call was made, kept
# as context a reader may want. `about` is what the call *concerned*, and it is
# the world's word, not an inference: the engine used to derive it from whatever
# was open, which credited a reference query about something else to the open
# item. A world knows what its own query was about; the engine only copies it.


def _closing(state: State, name: str, args: dict, item_arg: str) -> list[Task]:
    """The open tasks this call closes: named by the affordance, and on its item
    if the task names one. Attribution without knowing what an item is."""
    got = str(args.get(item_arg, "")) if item_arg else ""
    return [t for t in state.open_tasks() if name in t.closed_by
            and (t.item_id is None or (item_arg and t.item_id == got))]


def _serve(state: State, aff: Affordance) -> Callable:
    """One affordance, wrapped so the engine traces it and keeps the ledger.

    The event is appended *before* the handler runs and completed from the
    Response. What matters is not the ordering but the authorship: the world
    never writes this list, so a grader reading it can contradict the world's own
    counters. A handler that raises is a failure of the world, and VAGABOND is
    where it is caught.
    """
    def run(world: World, args: dict):
        at = len(state.trace)
        named = str(args.get(aff.item_arg, "")) if aff.item_arg else ""
        state.trace.append([world.turn, aff.name, dict(args), True, "",
                            state.open_items(), named])
        # B2: by value, not by length. A world that rewrote an argument or
        # flipped an `accepted` in place left a trace indistinguishable from an
        # honest one, so the guard compares what the rows say and not how many
        # there are
        before = [tuple(map(repr, row)) for row in state.trace]
        # by value and all the way down, like the trace above it. `dict(...)` is
        # a shallow copy, so a world could reach into a row already written,
        # `row["at"] = 99` moved a consultation from 0 to 1 on an admitted world
        # and the comparison saw two dicts with the same keys and passed
        ledger = repr(state.ledger)
        try:
            answer = aff.handler(state, args)
        except Exception:
            # a call that never happened may not stay in the trace as an
            # accepted one. VAGABOND catches a raise on its own walk; this is
            # what keeps the record honest if one happens during a campaign
            state.trace[at][3] = False
            state.trace[at][4] = "raised"
            raise
        if ([tuple(map(repr, row)) for row in state.trace] != before
                or repr(state.ledger) != ledger):
            # the docstring says the world does not write the trace. It is a
            # mechanism now, not a promise: a world that appends to the trace or
            # closes its own tasks can falsify the measurands that read them, and
            # a check the world has to cooperate with is not a check
            raise WorldError(
                f"{aff.name} wrote the engine's own records: the trace and the "
                "ledger are what a probe reads to contradict a world, so a world "
                "that writes them is a world nothing can contradict")
        state.trace[at][3] = answer.accepted
        state.trace[at][4] = answer.effect
        state.trace[at][6] = answer.about or named
        if answer.accepted:
            for task in _closing(state, aff.name, args, aff.item_arg):
                state.close(task, aff.name, at)
        return answer.served, (answer.truth or answer.served)
    return run


def build(*, prompt: str, collections: list[Collection], tasks: list[Task],
          affordances: list[Affordance], meta: dict | None = None,
          markers: tuple[str, ...] = (), world_version: str = "") -> World:
    """A served world, from the declaration alone.

    Returns the same `World` the solver already drives, so the loop, the tool
    conversion and the log are untouched. Its `meta` carries the engine's trace
    and ledger by reference, so the record written at the end holds them without
    anyone copying anything.

    Both versions ride on every record. A number that moves between 2026 and 2027
    has to be attributable to a model or to an instrument, and one version string
    cannot carry both.
    """
    state = State(collections, tasks, meta)
    # what a generic measurand needs to read a record it knows nothing about:
    # which tasks existed, which affordance names an item and in which argument,
    # and which of them query the world's own reference
    state.meta.update({
        "engine": VERSION, "world": world_version,
        "trace": state.trace, "ledger": state.ledger,
        "tasks": [{"id": t.id, "item": t.item_id, "by": list(t.closed_by)}
                  for t in tasks],
        "item_args": {a.name: a.item_arg for a in affordances if a.item_arg},
        "referential": [a.name for a in affordances if a.referential]})
    specs = [ToolSpec(a.name, a.description, dict(a.params), _serve(state, a),
                      optional=a.optional, referential=a.referential,
                      injected=a.injected)
             for a in affordances]
    served = World(prompt=prompt, tools=specs, meta=state.meta, markers=markers)
    served.state = state
    # kept for the admission rung, which has to walk a world it knows nothing
    # about: the item argument and the closing affordances are not on a ToolSpec
    served.affordances = list(affordances)
    return served
