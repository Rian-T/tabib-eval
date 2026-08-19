"""E1: VAGABOND admits a world, and refuses one, line by line.

A rung that has never been seen to fail is a rung nobody has tested. Every
condition here gets a world built to break exactly it, and nothing else, the
toy is a parcel counter and names no domain at all.
"""

from __future__ import annotations

import pytest

from tabib import engine as en
from tabib import vagabond as vg
from tests.test_engine import parcels, toy


def broken(*, handler=None, extra_task: bool = False) -> en.World:
    """The same counter, with one affordance replaced by a bad one."""
    coll = en.Collection("counter", parcels(2), access=en.head_only)

    def hand_over(state, args):
        got = state.reach("counter", args.get("parcel", ""))
        if got is None:
            return en.Response(served="Ce colis n'est pas au guichet.",
                               accepted=False)
        state.advance("counter")
        return en.Response(served="[remis]", effect="handed")

    tasks = [en.Task(f"T{i}", f"remettre P{i}", item_id=f"P{i}",
                     closed_by=("hand_over",)) for i in (1, 2)]
    return en.build(
        prompt="Guichet colis.",
        collections=[coll],
        tasks=tasks,
        affordances=[
            en.Affordance("look", "Regarde le colis.",
                          {"parcel": ("string", "Référence.")},
                          handler or (lambda s, a: en.Response(served="un colis")),
                          item_arg="parcel"),
            en.Affordance("hand_over", "Remet le colis.",
                          {"parcel": ("string", "Référence.")}, hand_over,
                          item_arg="parcel"),
        ],
        world_version="broken/1.0.0")


def verdicts(world) -> dict[str, bool | None]:
    return {label: ok for label, _, ok in vg.check(world)}


# --- a world that behaves ------------------------------------------------

@pytest.mark.parametrize("access", [None, en.head_only])
def test_a_coherent_world_is_admitted(access):
    world = toy(access=access)
    assert vg.admits(lambda: world) is True


def test_the_walk_is_the_same_walk_every_time():
    """A failure has to be reproducible, and a diff between two runs of one world
    must mean the world changed."""
    a = [tried for tried, _ in vg.walk(toy(access=en.head_only))]
    b = [tried for tried, _ in vg.walk(toy(access=en.head_only))]
    assert a == b and len(a) > 8


def test_deviating_is_never_refused_for_being_out_of_order():
    """Nothing the vagabond does is forbidden: it is unusual, which is the
    point. What comes back may be a refusal about *this item*, never about the
    order the agent chose."""
    world = toy(access=en.head_only)
    answers = dict(vg.walk(world))
    assert not any(o in got.lower() for got in answers.values()
                   for o in vg.OBLIGATION)


# --- and one that does not, one line at a time ---------------------------

def test_a_handler_that_raises_fails_the_first_line():
    def boom(state, args):
        raise KeyError("parcel")
    lines = verdicts(broken(handler=boom))
    assert lines["no handler raised"] is False
    # and the rung stops there rather than reporting on a world that crashed
    assert len(lines) == 1


def test_a_harness_wall_fails_its_line():
    def wall(state, args):
        return en.Response(served="KeyError: 'parcel' — invalid tool call")
    assert verdicts(broken(handler=wall))[
        "every answer is the world's, not the harness's"] is False


def test_an_obligation_fails_its_line():
    """The line that catches a corridor. Saying which parcel is open is a fact;
    saying the agent must open it first is a mechanism."""
    def bossy(state, args):
        return en.Response(served="Vous devez d'abord traiter le colis P1.")
    assert verdicts(broken(handler=bossy))[
        "nothing the world says is an obligation"] is False


def test_a_world_that_writes_the_engine_s_records_is_refused_by_the_engine():
    """The trace and the ledger are what a probe reads to contradict a world, so
    a world that writes them is a world nothing can contradict.

    This used to be caught by VAGABOND's shape line, which only worked because
    the walk happened to trigger the lie. A world lying under a condition the walk
    never meets passed, and three generic measurands could be falsified on an
    admitted world. It is a mechanism now: the call fails where it is made.
    """
    def forger(state, args):
        state.trace.append([1, "look", {}, True, "invented", []])
        return en.Response(served="un colis")

    def sneak(state, args):
        for task in state.open_tasks():
            state.close(task, "look", len(state.trace))
        return en.Response(served="un colis")

    for handler in (forger, sneak):
        world = broken(handler=handler)
        with pytest.raises(en.WorldError, match="wrote the engine's own records"):
            world.call("look", {"parcel": "P1"})
        # and the admission rung refuses it, at its first line
        assert verdicts(broken(handler=handler))["no handler raised"] is False


def test_a_handler_that_raises_leaves_no_accepted_call_behind():
    """The event is written before the handler runs, so a raise would otherwise
    leave a call that never happened recorded as accepted. VAGABOND catches a
    raise on its own walk; this is what keeps a campaign's record honest."""
    world = broken(handler=lambda s, a: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(RuntimeError):
        world.call("look", {"parcel": "P1"})
    assert world.state.trace[-1][3] is False
    assert world.state.trace[-1][4] == "raised"


def test_a_state_that_cannot_be_described_fails_its_line():
    """Outside a handler the engine guards nothing, it cannot: the world builds
    its own state. A ledger holding a task nobody declared is the case
    `describe()` exists to refuse."""
    world = broken()
    world.state.ledger["T-nobody-declared"] = {"by": "look", "at": 0, "rank": 1}
    assert verdicts(world)["the state can be described after all that"] is False


def test_every_line_of_the_rung_has_been_seen_to_fail():
    """The rung's own admission test. A condition no world has ever failed is a
    condition nobody has tested, and the registry has an entry for exactly that.
    """
    seen = {
        "no handler raised":
            broken(handler=lambda s, a: (_ for _ in ()).throw(RuntimeError("x"))),
        "every answer is the world's, not the harness's":
            broken(handler=lambda s, a: en.Response(served="Traceback (most recent)")),
        "nothing the world says is an obligation":
            broken(handler=lambda s, a: en.Response(served="Il faut ouvrir P1.")),
    }
    for line, world in seen.items():
        assert verdicts(world)[line] is False, line
    # the three structural ones have their own tests above; here we assert the
    # rung declares exactly the lines we think it does
    labels = [label for label, _, _ in vg.check(toy())]
    assert labels == [
        "no handler raised",
        "every answer is the world's, not the harness's",
        "nothing the world says is an obligation",
        "the trace is well formed, one event per call",
        "the ledger recomputed from the trace matches",
        "the state can be described after all that",
        "the vagabond could get at least one thing done",
        "calls the world declined, each with its own words",
    ]


def test_a_world_that_refuses_everything_is_not_a_world():
    """The rung shipped admitting this one. Every affordance answers "not
    available", politely, in the world's own words, with no obligation and no
    harness vocabulary, six refusals out of six, six green lines. It is the
    literal case of this module's first sentence, and nothing asked whether
    anything at all could be done."""
    shut = broken(handler=lambda s, a: en.Response(
        served="Ce colis n'est pas disponible.", accepted=False))
    # the other affordance too, so nothing in the world accepts anything
    shut.affordances = [
        en.Affordance(a.name, a.description, a.params,
                      lambda s, args: en.Response(
                          served="Ce colis n'est pas disponible.", accepted=False),
                      item_arg=a.item_arg)
        for a in shut.affordances]
    shut._specs = {a.name: en.ToolSpec(a.name, a.description, dict(a.params),
                                       en._serve(shut.state, a))
                   for a in shut.affordances}
    lines = verdicts(shut)
    assert lines["the vagabond could get at least one thing done"] is False
    # and every other line is green, which is exactly why this one had to exist
    others = [ok for label, ok in lines.items()
              if ok is not None
              and label != "the vagabond could get at least one thing done"]
    assert others == [True] * len(others) and len(others) >= 5


def test_a_world_that_edits_a_ledger_row_already_written_is_refused():
    """The shallow-copy hole, symmetrical with the trace's.

    The guard compared `dict(state.ledger)` before and after, which shares its
    rows with the original, so a world could reach into a row already written
    and the comparison saw two dicts with the same keys. Moving `at` to 99 took a
    consultation from 0 to 1 on a world VAGABOND admitted.
    """
    def meddler(state, args):
        for line in state.ledger.values():
            line["at"] = 99
        return en.Response(served="un colis")

    world = broken()
    world.call("hand_over", {"parcel": "P1"})          # something to meddle with
    world.affordances[0] = en.Affordance("meddle", "x", {}, meddler)
    world._specs["meddle"] = en.ToolSpec("meddle", "x", {},
                                         en._serve(world.state,
                                                   world.affordances[0]))
    with pytest.raises(en.WorldError, match="wrote the engine's own records"):
        world.call("meddle", {})
