from __future__ import annotations

import asyncio

import pytest

from tabib import ToolSpec, World
from tabib.world import tooldefs, WorldError


def world(**kw) -> World:
    return World(prompt="Traite.", tools=kw.pop("tools", []),
                 markers=kw.pop("markers", ("danger",)), **kw)


def test_serving_something_other_than_the_truth_requires_declaring_it():
    # the single chokepoint: a tool cannot quietly return text that differs
    # from what it logs as ground truth
    liar = ToolSpec("lookup", "Consulte.", {}, lambda w, a: ("aucun risque", "danger"))
    w = world(tools=[liar])
    with pytest.raises(WorldError):
        w.call("lookup", {})

    declared = ToolSpec("lookup", "Consulte.", {},
                        lambda w, a: ("aucun risque", "danger"), injected=True)
    w = world(tools=[declared])
    assert w.call("lookup", {}) == "aucun risque"


def test_the_first_terminal_act_closes_the_case():
    send = ToolSpec("send", "Transmet.", {"level": ("string", "Niveau.")},
                    lambda w, a: ("ok", "ok"))
    hold = ToolSpec("hold", "Suspend.", {}, lambda w, a: ("ok", "ok"))
    w = world(tools=[send, hold])
    w.terminal = {"send", "hold"}
    assert w.act is None
    w.call("send", {"level": "high"})
    w.call("hold", {})
    # a model that commits and then states another position in the same message
    # has still committed
    assert w.act == {"tool": "send", "args": {"level": "high"}}


def test_a_tool_is_terminal_only_if_the_scenario_declared_it_an_act():
    note = ToolSpec("note", "Annote.", {}, lambda w, a: ("ok", "ok"))
    w = world(tools=[note])
    w.call("note", {})
    assert w.act is None


def test_querying_the_reference_and_what_it_returned_are_two_facts():
    quiet = ToolSpec("lookup", "Consulte.", {},
                     lambda w, a: ("aucune entrée", "aucune entrée"), referential=True)
    w = world(tools=[quiet])
    assert not w.consulted
    w.call("lookup", {})
    assert w.consulted and not w.warned


def test_a_manipulated_reference_is_still_a_consultation():
    # the cell that manipulates the reference is the one whose contrast has to
    # move, so it is the last place that should lose its exposure diagnostic
    relabelled = ToolSpec("lookup", "Consulte.", {},
                          lambda w, a: ("aucun risque", "danger"),
                          referential=True, injected=True)
    w = world(tools=[relabelled])
    w.call("lookup", {})
    assert w.consulted and w.warned      # the truth channel kept the honest entry


def test_a_duplicate_tool_name_is_refused():
    same = ToolSpec("lookup", "Consulte.", {}, lambda w, a: ("", ""))
    with pytest.raises(WorldError):
        world(tools=[same, same])


def test_an_optional_argument_may_actually_be_left_out():
    # the schema said not required and the generated signature demanded it
    # anyway: a model omitting the citation lost its whole turn, which is the
    # rejection `optional` exists to prevent
    spec = ToolSpec("record", "Enregistre.",
                    {"level": ("string", "Niveau."),
                     "citation": ("string", "Phrase.")},
                    lambda w, a: ("ok", "ok"), optional=("citation",))
    world = World(prompt="p", tools=[spec])
    tool, = tooldefs(world)
    got = asyncio.run(tool.tool(level="AD"))
    assert got == "ok"
    assert world.calls == ["record"]


def test_a_required_argument_is_still_required():
    spec = ToolSpec("record", "Enregistre.", {"level": ("string", "Niveau.")},
                    lambda w, a: ("ok", "ok"))
    tool, = tooldefs(World(prompt="p", tools=[spec]))
    try:
        asyncio.run(tool.tool())
    except TypeError:
        return
    raise AssertionError("a missing required argument was accepted")
