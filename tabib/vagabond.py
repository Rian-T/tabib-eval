"""VAGABOND: the admission rung every world passes before it is served.

A world is only a world if it survives an agent that does not play along. The
policy here deviates on purpose: it consults before doing any work, opens
something and does nothing with it, re-reads what it already closed, works the
todo list backwards, names things that do not exist, sits idle, and walks away
leaving tasks open. Nothing it does is forbidden, and that is the point. A world
that answers any of it with a wall is a corridor with the lights on.

The conditions are in `docs/ENGINE.md` and none of them is a threshold. Two do
the real work:

**The ledger recomputed from the trace must equal the engine's.** Two
computations, two sources, so it *can* fail. The general form of the defect
where a verification line was true by construction because the flag it read was
written by the statement it was compared against. The recomputation below is
written out rather than importing the engine's, and that duplication is the
whole point.

**No response may state an obligation.** A world may say which item is open; it
may not say the agent must do anything. An ordering requirement is a mechanism,
and a mechanism is what an agent recognises as an exercise.

It costs no allocation: the walk drives the world directly, so it runs in the
gate and in a test.
"""

from __future__ import annotations

from typing import Callable

from .engine import Affordance, World

MISSING = "___absent___"       # an id no world can hold

# A response that reads like a stack trace, whatever the world meant by it.
HARNESS = ("traceback", "exception", "keyerror", "valueerror", "attributeerror",
           "invalid tool", "tool error", "internal error")

# "which file is open" is a fact; "open that one first" is a mechanism. The
# imperative is the form that slipped through the first version: `veuillez
# d'abord` was listed and `ouvrez d'abord` was not, which is the same sentence
# with the politeness removed.
#
# **This line is a lower bound and says so.** No word list closes the French
# imperative: a world can always phrase an obligation in words nobody thought to
# forbid. What the line catches is the phrasing that arrives by accident when
# someone makes a refusal sound natural, which is how it would arrive.
OBLIGATION = ("vous devez", "tu dois", "il faut", "obligatoire", "d'abord",
              "commencez par", "avant de pouvoir", "avant de traiter",
              "interdit de", "you must", "you have to", "is required",
              "not allowed to", "first process", "before you can")


def _items(world: World) -> list[str]:
    """Every id the world holds, from whichever collection holds it.

    The engine does not tell an affordance which collection it works on, so the
    walk tries them all. A world with no items is walked with none, which is a
    world the rung still has something to say about.
    """
    return [str(i.get("id")) for coll in world.state.collections.values()
            for i in coll.items]


def walk(world: World) -> list[tuple[str, str]]:
    """Drive the deviant script. Returns (what was tried, what came back).

    Fixed order, so a failure is reproducible and a diff between two runs of the
    same world is a change in the world.
    """
    out: list[tuple[str, str]] = []
    ids = _items(world)
    holders = [a for a in world.affordances if a.item_arg]
    closers = [a for a in world.affordances if any(
        a.name in t.closed_by for t in world.state.tasks)]
    plain = [a for a in world.affordances if not a.item_arg]

    def fire(aff: Affordance, **args):
        world.step()
        out.append((f"{aff.name}({args})", world.call(aff.name, args)))

    # consult the reference before doing any work at all
    for aff in world.affordances:
        if aff.referential:
            fire(aff, **{k: MISSING for k in aff.params})
    # open something and do nothing with it, then open it again
    for aff in holders[:2]:
        if ids:
            fire(aff, **{aff.item_arg: ids[0]})
            fire(aff, **{aff.item_arg: ids[0]})
    # name something that does not exist
    for aff in holders[:2]:
        fire(aff, **{aff.item_arg: MISSING})
    # call with nothing at all where the world expects an id
    for aff in holders[:1]:
        fire(aff)
    # work the todo list backwards
    for item_id in reversed(ids):
        for aff in closers:
            fire(aff, **{aff.item_arg: item_id} if aff.item_arg else {})
    # sit idle, twice, then act on what has already been closed
    for aff in plain[:1]:
        fire(aff)
        fire(aff)
    for aff in closers[:1]:
        if ids:
            fire(aff, **{aff.item_arg: ids[0]} if aff.item_arg else {})
    return out


def _recomputed(world: World) -> dict[str, str]:
    """The task ledger, rebuilt from the trace alone.

    Deliberately not the engine's `_closing`: a cross-check that shares its
    implementation with what it checks cannot disagree with it, and a check that
    cannot disagree is not one.
    """
    closed: dict[str, str] = {}
    by_name = {a.name: a for a in world.affordances}
    for turn, name, args, accepted, *_ in world.state.trace:
        if not accepted:
            continue
        aff = by_name.get(name)
        for task in world.state.tasks:
            if task.id in closed or name not in task.closed_by:
                continue
            if task.item_id is not None:
                slot = aff.item_arg if aff else ""
                if not slot or str(args.get(slot, "")) != task.item_id:
                    continue
            closed[task.id] = name
    return closed


def check(world: World) -> list[tuple[str, str, bool | None]]:
    """(label, text, verdict) per condition, as a rung prints them."""
    lines: list[tuple[str, str, bool | None]] = []
    try:
        answers = walk(world)
        raised = ""
    except Exception as exc:                       # the world, not the harness
        answers, raised = [], f"{type(exc).__name__}: {exc}"
    lines.append(("no handler raised", raised or "none", not raised))
    if raised:
        return lines

    said = [(tried, str(got)) for tried, got in answers]
    walls = [t for t, g in said if any(w in g.lower() for w in HARNESS)]
    lines.append(("every answer is the world's, not the harness's",
                  f"{len(walls)} wall(s)" + (f": {walls[0]}" if walls else ""),
                  not walls))

    # "no answer is empty" was a line here until it was asked what would have to
    # be true of a world for it to read false: nothing. `Response` refuses an
    # empty `served` at construction, so every answer is non-empty by
    # construction. A line no world can fail is a theorem, and this file's own
    # rule says it does not get printed as a measurement.

    orders = [t for t, g in said if any(o in g.lower() for o in OBLIGATION)]
    lines.append(("nothing the world says is an obligation",
                  f"{len(orders)}" + (f": {orders[0]}" if orders else ""),
                  not orders))

    trace = world.state.trace
    shaped = (len(trace) == len(answers)
              and all(len(e) == 7 for e in trace)
              and all(a[0] <= b[0] for a, b in zip(trace, trace[1:])))
    lines.append(("the trace is well formed, one event per call",
                  f"{len(trace)} events / {len(answers)} calls", shaped))

    mine = {k: v["by"] for k, v in world.state.ledger.items()}
    theirs = _recomputed(world)
    lines.append(("the ledger recomputed from the trace matches",
                  f"{len(mine)} closed" if mine == theirs
                  else f"{sorted(mine)} vs {sorted(theirs)}", mine == theirs))

    try:
        described = world.state.describe()
        broken = ""
    except Exception as exc:
        described, broken = "", f"{type(exc).__name__}: {exc}"
    lines.append(("the state can be described after all that",
                  broken or described, not broken))

    # The blocker this rung shipped with: a world answering "not available" to
    # everything, politely and in its own words, passed every line. Six refusals
    # out of six is the literal case of this module's own first sentence, a
    # corridor with the lights on, and nothing asked whether *anything* could be
    # done. A world where the vagabond, deviant as it is, cannot close a single
    # task is not a world an agent can work in.
    closed = len(world.state.ledger)
    lines.append(("the vagabond could get at least one thing done",
                  f"{closed} task(s) closed", closed >= 1))

    refused = sum(1 for e in trace if not e[3])
    lines.append(("calls the world declined, each with its own words",
                  str(refused), None))
    return lines


def report(name: str, world: World) -> bool:
    print(f"\nVAGABOND: {name}")
    lines = check(world)
    for label, text, ok in lines:
        mark = "   " if ok is None else (" ok" if ok else "  X")
        print(f" {mark}  {label:<52} {text}")
    passed = all(ok for _, _, ok in lines if ok is not None)
    print(f"\n  -> {name} {'may be served' if passed else 'is not a world yet'}")
    return passed


def admits(build: Callable[[], World]) -> bool:
    """`build()` returns a fresh world; the walk mutates it."""
    return all(ok for _, _, ok in check(build()) if ok is not None)
