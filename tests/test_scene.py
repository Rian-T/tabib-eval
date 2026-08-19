"""The scene: every glyph from a declared property, and a floor that still draws."""

from __future__ import annotations

from types import SimpleNamespace

from rich.console import Console

from tabib import scene
from tests.conftest import call, run_probe, say, toy_task


def draw(*args) -> str:
    console = Console(width=110, record=True)
    console.print(scene.render(*args))
    return console.export_text()


def _sample(tools, calls, record=None):
    """A session-shaped stand-in: what was offered, what was called."""
    events = [SimpleNamespace(event="model", tools=[SimpleNamespace(name=n)
                                                   for n in tools])]
    events += [SimpleNamespace(event="tool", function=f, arguments=a, result=r,
                               error=None) for f, a, r in calls]
    return SimpleNamespace(events=events, id="s1",
                           store={"tabib:record": record or {}})


def test_a_world_with_no_roles_draws_named_boxes():
    sample = _sample(["look", "send"], [("look", {"at": "x"}, "un dossier")])
    drawn = scene.stations(sample, None)
    assert [s.role for s in drawn] == ["tool", "tool"]
    text = draw(drawn, scene.frames(sample), 0)
    assert "look" in text and "send" in text
    # no collection, so nothing is open and no queue is drawn
    assert "open " not in text


def test_the_roles_come_from_the_declaration():
    sample = _sample(["lookup_reference", "advise", "end_chat"], [],
                     record={"referential": ["lookup_reference"]})
    drawn = scene.stations(sample, "companion")
    assert {s.name: s.role for s in drawn} == {
        "lookup_reference": "referential", "advise": "tool", "end_chat": "act"}


def test_the_station_budget_collapses_the_role_less_ones():
    names = [f"t{i}" for i in range(12)] + ["ref"]
    drawn = scene.stations(_sample(names, []), None)
    assert len(drawn) == scene.STATIONS
    assert drawn[-1].role == "more" and "more tools" in drawn[-1].name


def test_a_frame_reads_the_trace_where_there_is_one():
    record = {"trace": [[2, "look", {"at": "x"}, True, "opened", ["d1", "d2", "d3"], "d1"]]}
    sample = _sample(["look"], [("look", {"at": "x"}, "le dossier d1")], record)
    shot = scene.frames(sample)[0]
    assert (shot.turn, shot.at, shot.effect) == (2, "look", "opened")
    assert shot.open == ("d1", "d2", "d3")
    text = draw(scene.stations(sample, None), [shot], 0)
    # the queue is capped and says how many it is not showing
    assert "open d1, d2 (+1)" in text
    assert "le dossier d1" in text


def test_an_idle_scene_draws_rather_than_raising():
    sample = _sample(["look"], [])
    assert "idle" in draw(scene.stations(sample, None), scene.frames(sample), 0)


def test_replay_reads_a_finished_log(tmp_path):
    """The floor on a real log: a world built without the engine still draws."""
    log = run_probe(toy_task(), [call("send", {"level": "high"}), say("fini")],
                    tmp_path)
    sample, scenario, model = scene.read(str(tmp_path))
    assert scenario == "toy" and model.endswith("model")
    shots = scene.frames(sample)
    assert [s.at for s in shots] == ["send"]
    # no engine trace on this world, so no open items and no effect
    assert shots[0].open == () and shots[0].effect == ""
    assert "send" in draw(scene.stations(sample, scenario), shots, 0)
