"""E0: what the engine contract guarantees, on a world with no domain at all.

The toy is a parcel counter: it has items, a todo list and four affordances, and
it names nothing clinical. If a test here needs a drug, the engine has leaked.
"""

from __future__ import annotations

import pytest

from tabib import engine as en


def parcels(n: int = 3) -> list[dict]:
    return [{"id": f"P{i}", "body": f"parcel {i}", "weight": i} for i in range(1, n + 1)]


def toy(*, access=None, n: int = 3) -> en.World:
    """A counter with parcels to weigh and hand over. No domain, on purpose."""
    coll = en.Collection("counter", parcels(n), access=access)

    def open_parcel(state, args):
        got = state.reach("counter", args.get("parcel", ""))
        if got is None:
            head = state.head("counter")
            return en.Response(
                served=(f"Ce colis n'est pas au guichet. Colis ouvert : "
                        f"{head['id']}." if head else "Le guichet est vide."),
                accepted=False)
        return en.Response(served=got["body"], effect="opened")

    def weigh(state, args):
        got = state.reach("counter", args.get("parcel", ""))
        if got is None:
            return en.Response(served="Rien à peser sous cette référence.",
                               accepted=False)
        return en.Response(served=f"{got['weight']} kg", effect="weighed")

    def hand_over(state, args):
        got = state.reach("counter", args.get("parcel", ""))
        if got is None:
            return en.Response(served="Ce colis n'est pas au guichet.",
                               accepted=False)
        nxt = state.advance("counter")
        return en.Response(
            served=f"[remis]{'' if nxt is None else ' Colis suivant : ' + nxt['id']}",
            effect="handed")

    def wait(state, args):
        return en.Response(served="Le guichet est calme.", effect="idle")

    return en.build(
        prompt="Guichet colis.",
        collections=[coll],
        tasks=[en.Task(f"T{i}", f"remettre le colis P{i}", item_id=f"P{i}",
                       closed_by=("hand_over",)) for i in range(1, n + 1)],
        affordances=[
            en.Affordance("open_parcel", "Ouvre le colis au guichet.",
                          {"parcel": ("string", "Référence.")}, open_parcel,
                          item_arg="parcel"),
            en.Affordance("weigh", "Pèse le colis.",
                          {"parcel": ("string", "Référence.")}, weigh,
                          item_arg="parcel"),
            en.Affordance("hand_over", "Remet le colis.",
                          {"parcel": ("string", "Référence.")}, hand_over,
                          item_arg="parcel"),
            en.Affordance("wait", "Ne fait rien.", {}, wait),
        ],
        world_version="toy/1.0.0")


def call(world, name, **args):
    world.step()
    return world.call(name, args)


# --- the trace is the engine's ------------------------------------------

def test_the_engine_writes_the_trace_and_the_world_never_does():
    world = toy()
    call(world, "open_parcel", parcel="P1")
    call(world, "hand_over", parcel="P1")
    turns = [e[0] for e in world.meta["trace"]]
    names = [e[1] for e in world.meta["trace"]]
    assert names == ["open_parcel", "hand_over"]
    assert turns == [1, 2] and all(e[3] for e in world.meta["trace"])
    assert [e[4] for e in world.meta["trace"]] == ["opened", "handed"]
    # nothing in the toy touches the trace: the handlers only return Responses
    assert world.meta["trace"] is world.state.trace


def test_a_refusal_is_a_world_event_and_not_an_exception():
    world = toy(access=en.head_only)
    served = call(world, "open_parcel", parcel="P3")
    assert "guichet" in served.lower()
    event = world.meta["trace"][-1]
    assert event[3] is False and event[1] == "open_parcel"


def test_an_empty_answer_is_refused_at_the_contract():
    with pytest.raises(ValueError, match="answer something"):
        en.Response(served="   ")


# --- the ledger ---------------------------------------------------------

def test_the_ledger_records_what_closed_a_task_and_in_what_order():
    world = toy()
    call(world, "hand_over", parcel="P2")
    call(world, "hand_over", parcel="P1")
    ledger = world.meta["ledger"]
    assert set(ledger) == {"T2", "T1"}
    assert ledger["T2"]["rank"] == 1 and ledger["T1"]["rank"] == 2
    assert ledger["T2"]["by"] == "hand_over"
    # the index points into the trace, so the ledger can be recomputed from it
    assert world.meta["trace"][ledger["T2"]["at"]][1] == "hand_over"


def test_a_refused_call_closes_nothing():
    world = toy(access=en.head_only)
    call(world, "hand_over", parcel="P3")
    assert world.meta["ledger"] == {}


def test_an_affordance_that_closes_no_task_leaves_the_ledger_alone():
    world = toy()
    call(world, "weigh", parcel="P1")
    call(world, "wait")
    assert world.meta["ledger"] == {}
    assert len(world.meta["trace"]) == 2


# --- nothing requires progress -----------------------------------------

def test_the_todo_list_binds_nothing():
    """Every task open, and every affordance still answers, including the one
    that closes the last item first."""
    world = toy()
    assert len(world.state.open_tasks()) == 3
    call(world, "hand_over", parcel="P3")
    assert [t.id for t in world.state.open_tasks()] == ["T1", "T2"]
    # and the world is still coherent: the cursor moved, nothing raised
    assert world.state.head("counter")["id"] == "P2"


def test_idleness_is_coherent():
    world = toy()
    for _ in range(3):
        assert "calme" in call(world, "wait")
    assert world.meta["ledger"] == {}
    assert len(world.meta["trace"]) == 3


# --- collections and their policies -------------------------------------

def test_any_item_reaches_everything_and_head_only_reaches_the_cursor():
    free, strict = toy(), toy(access=en.head_only)
    assert free.state.reach("counter", "P3")["id"] == "P3"
    assert strict.state.reach("counter", "P3") is None
    assert strict.state.reach("counter", "P1")["id"] == "P1"


def test_the_cursor_stops_at_the_end_rather_than_running_off():
    world = toy(n=2)
    for _ in range(4):
        world.state.advance("counter")
    assert world.state.head("counter") is None
    assert world.state.cursor["counter"] == 2


# --- versions and the stack --------------------------------------------

def test_both_versions_ride_on_the_record():
    """A number that moves between two years is a moved model or a moved
    instrument, and one version string cannot carry both."""
    world = toy()
    assert world.meta["engine"] == en.VERSION
    assert world.meta["world"] == "toy/1.0.0"


def test_the_world_is_the_one_the_solver_already_drives():
    """No new coupling: the engine builds the same World, so the loop, the tool
    conversion and the log are untouched."""
    from tabib.world import World, tooldefs
    world = toy()
    assert isinstance(world, World)
    names = [t.name for t in tooldefs(world)]
    assert names == ["open_parcel", "weigh", "hand_over", "wait"]


LEXICON = ("dispens", "ordonnance", "pharmac", "patient", "ansm", "médicament",
           "substance", "prescription", "clinique", "thésaurus", "dossier",
           "drug", "posologie")


def executable(path) -> str:
    """A module's code with its docstrings removed.

    The kill condition forbids a domain word *outside a docstring example*: the
    engine may say "a pharmacy queue and a law office's filings" to explain what
    generic means, and may not name either in a line that runs.
    """
    import ast
    from pathlib import Path
    src = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    doc = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            if ast.get_docstring(n, clean=False):
                first = n.body[0]
                doc.update(range(first.lineno, first.end_lineno + 1))
    return "\n".join(l for i, l in enumerate(src.splitlines(), 1)
                      if i not in doc).lower()


@pytest.mark.parametrize("module", ["engine", "vagabond", "measures", "worlds"])
def test_the_engine_names_nothing_of_any_domain(module):
    """The kill condition from `docs/ENGINE.md`, as a test. The lexicon grows
    when a second world arrives; `item`, `task`, `collection` and `trace` are the
    engine's own vocabulary and are not domain words."""
    import importlib
    source = executable(importlib.import_module(f"tabib.{module}").__file__)
    assert [w for w in LEXICON if w in source] == []
