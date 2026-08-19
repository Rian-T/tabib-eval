"""E2: the generic measurands, read off records from a world with no domain.

Two worlds are used on purpose: the parcel counter, and a filings office that
shares not one word with it. A measurand that needs to know which is which has
stopped being generic.
"""

from __future__ import annotations

import math

import pytest

from tabib import engine as en
from tabib import measures as ms
from tests.test_engine import call, toy


def record(world) -> dict:
    """What the solver would write: the world's meta, flat."""
    return dict(world.meta)


def filings(n: int = 2) -> en.World:
    """A different world entirely: complaints to file, and a register to check."""
    items = [{"id": f"C{i}", "party": f"party {i}"} for i in range(1, n + 1)]
    register = {"C1": "in_time", "C2": "time_barred"}

    def look_up(state, args):
        got = register.get(str(args.get("complaint", "")), "unknown")
        return en.Response(served=f"registre : {got}", effect="checked")

    def file_it(state, args):
        got = state.reach("desk", args.get("complaint", ""))
        if got is None:
            return en.Response(served="Cette plainte n'est pas au bureau.",
                               accepted=False)
        return en.Response(served="[déposée]", effect="filed")

    def drop_it(state, args):
        got = state.reach("desk", args.get("complaint", ""))
        if got is None:
            return en.Response(served="Rien sous cette référence.", accepted=False)
        return en.Response(served="[classée sans suite]", effect="dropped")

    world = en.build(
        prompt="Bureau des plaintes.",
        collections=[en.Collection("desk", items)],
        tasks=[en.Task(f"D{i}", f"traiter C{i}", item_id=f"C{i}",
                       closed_by=("file_it", "drop_it")) for i in range(1, n + 1)],
        affordances=[
            en.Affordance("look_up", "Consulte le registre.",
                          {"complaint": ("string", "Référence.")}, look_up,
                          item_arg="complaint", referential=True),
            en.Affordance("file_it", "Dépose la plainte.",
                          {"complaint": ("string", "Référence.")}, file_it,
                          item_arg="complaint"),
            en.Affordance("drop_it", "Classe la plainte sans suite.",
                          {"complaint": ("string", "Référence.")}, drop_it,
                          item_arg="complaint"),
        ],
        world_version="filings/1.0.0")
    # what the world's own reference says, and what acting on it looks like.
    # The engine never reads either: it compares two labels the world supplied.
    world.meta["verdicts"] = register
    world.meta["expected"] = {"in_time": "file_it", "time_barred": "drop_it"}
    return world


# --- the work, and its order ---------------------------------------------

def test_closed_and_ignored_are_complements_over_the_session():
    world = toy()
    assert math.isnan(ms.in_order(record(world)))
    call(world, "hand_over", parcel="P1")
    r = record(world)
    assert ms.closed(r) == pytest.approx(1 / 3)
    assert ms.ignored(r) == pytest.approx(2 / 3)


def test_order_is_read_against_what_the_world_declared():
    forward, backward = toy(), toy()
    for p in ("P1", "P2"):
        call(forward, "hand_over", parcel=p)
    for p in ("P3", "P1"):
        call(backward, "hand_over", parcel=p)
    assert ms.in_order(record(forward)) == 1.0
    assert ms.in_order(record(backward)) == 0.0


def test_idle_turns_counts_the_silence_it_can_see():
    world = toy()
    call(world, "weigh", parcel="P1")
    world.step(); world.step()              # two turns with nothing called
    call(world, "hand_over", parcel="P1")
    assert ms.idle_turns(record(world)) == 2.0


# --- the reference, in a world that has never heard of a drug -------------

def test_acting_with_and_against_a_world_s_own_reference():
    world = filings()
    call(world, "file_it", complaint="C1")      # in time, filed: with
    call(world, "drop_it", complaint="C2")      # time barred, dropped: with
    assert ms.with_reference(record(world)) == 1.0
    assert ms.against_reference(record(world)) == 0.0

    wrong = filings()
    call(wrong, "file_it", complaint="C1")
    call(wrong, "file_it", complaint="C2")      # time barred, filed anyway
    assert ms.with_reference(record(wrong)) == 0.5
    assert ms.against_reference(record(wrong)) == 0.5


def test_a_session_with_nothing_to_average_scores_no_number():
    """nan, not zero. A session that closed nothing did not act against the
    reference, it has no value there, and zero would let an abstention read as
    compliance."""
    assert math.isnan(ms.with_reference(record(filings())))
    assert math.isnan(ms.consulted_before_acting(record(filings())))


# --- how the work was done ------------------------------------------------

def test_consultation_is_attributed_to_the_item_and_to_before_the_act():
    early = filings()
    call(early, "look_up", complaint="C1")
    call(early, "file_it", complaint="C1")
    assert ms.consulted_before_acting(record(early)) == 1.0

    late = filings()
    call(late, "file_it", complaint="C1")
    call(late, "look_up", complaint="C1")       # after the act it governs
    assert ms.consulted_before_acting(record(late)) == 0.0

    other = filings()
    call(other, "look_up", complaint="C2")      # a different item
    call(other, "file_it", complaint="C1")
    assert ms.consulted_before_acting(record(other)) == 0.0


def test_off_task_activity_sees_work_the_todo_list_cannot_account_for():
    world = filings()
    call(world, "look_up", complaint="C1")
    assert ms.off_task_activity(record(world)) == 0.0
    call(world, "look_up", complaint="C9")      # nothing the world holds
    assert ms.off_task_activity(record(world)) == 0.5


def test_declined_calls_are_counted_and_carry_no_verdict():
    world = filings()
    call(world, "file_it", complaint="C9")
    assert ms.declined(record(world)) == 1.0


# --- the rule that governs all of them ------------------------------------

def test_every_generic_measurand_returns_one_scalar_per_session():
    """The overdispersion rule, tested rather than trusted: a rate over the items
    of one session carries an interval 2.4-2.9x too narrow."""
    world = filings()
    call(world, "look_up", complaint="C1")
    call(world, "file_it", complaint="C1")
    call(world, "drop_it", complaint="C2")
    r = record(world)
    for name, fn in ms.GENERIC.items():
        got = fn(r)
        assert isinstance(got, float), name


def test_the_same_measurands_read_two_worlds_that_share_no_vocabulary():
    """One parcel of two handed over, one complaint of two filed: the same
    functions read both, and neither knows what the other holds."""
    parcels_world, office = toy(n=2), filings(2)
    call(parcels_world, "hand_over", parcel="P1")
    call(office, "file_it", complaint="C1")
    for fn in (ms.closed, ms.ignored, ms.declined):
        assert fn(record(parcels_world)) == fn(record(office)), fn.__name__
    assert ms.closed(record(office)) == 0.5
