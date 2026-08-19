"""The v3 declaration: what we ask of the world, and nothing about how it works.

If a test here has to reach into the world's mechanics, the separation has
failed: a world is where the agent works, a scenario is what we ask of it.
"""

from __future__ import annotations

import pytest

from tabib import measures as ms
from scenarios.hospital import scenario as h


def row(arm: str = "CI") -> dict:
    return next(r for r in h.rows(n=2) if r["arm"] == arm)


def test_the_triptych_is_declared_once_and_every_point_has_a_floor():
    assert len(h.SCENARIO.cells) == 16
    floors = {m.cells[1] for m in h.MEASURANDS
              if m.name.startswith("differs_from_its_twin")}
    assert floors == set(h.SERVED + h.SWEEP)


@pytest.mark.parametrize("cell", h.SERVED + h.SWEEP)
def test_a_twin_is_its_cell_byte_for_byte(cell):
    """Prompt, queue and tool set. A twin that fetched what its cell was handed
    would print the modality delta as instrument noise."""
    r = row()
    mine, twin = h.build(cell, r), h.build(f"{cell}_twin", r)
    assert mine.prompt == twin.prompt
    assert [s.name for s in mine.specs] == [s.name for s in twin.specs]
    assert mine.meta["measured"] == twin.meta["measured"]


def test_the_served_cell_hands_the_evidence_over():
    r = row()
    served, fetched = h.build("chat", r), h.build("l1", r)
    names = [s.name for s in served.specs]
    assert "read_record" not in names and "lookup_reference" not in names
    # the act vocabulary is identical, so the modality step reads what the model
    # had to do to reach the file and never a different set of verbs
    assert names == [s.name for s in fetched.specs][2:]
    assert r["cells"]["l1"][0]["record"] in served.prompt


def test_the_generic_measurands_travel_with_the_where_they_ship_with():
    """Taking the `y` and forgetting the `where` is how a cell mean becomes nan
    and a rung reads nan as False."""
    for name in ("tasks_closed", "consulted_before_acting", "worked_in_order"):
        declared = [m for m in h.MEASURANDS if m.name.startswith(name + "_")]
        assert declared
        for m in declared:
            assert m.y is ms.GENERIC[name]
            assert m.where is ms.WHERE[name]


def test_the_risk_axis_reads_the_engine_s_ledger():
    """The one thing generic code cannot know is which item is under
    measurement; everything else about the session is the engine's."""
    r = row("CI")
    world = h.build("l4", r)
    files = r["cells"]["l4"]
    for f in files:
        world.call("dispense", {"file_id": f["file_id"], "motif": ""})
    record = {**world.meta, "status": "acted"}
    assert h._act_on_measured(record) == "dispense"
    assert h._permissive(record) == 1.0 and h._forbidden(record)
    assert ms.closed(record) == 1.0


def test_rows_counts_clusters_per_arm():
    from collections import Counter
    got = h.rows(n=3)
    assert Counter(x["arm"] for x in got) == {"CI": 3, "APEC": 3}
    with pytest.raises(ValueError, match="per arm"):
        h.rows(n=10_000)


def test_the_budget_is_per_file():
    for cell in h.SCENARIO.cells:
        length = len(h.WORLD.clusters()[0]["cells"][h._key(cell)])
        assert h.budget(cell) == (h.STEPS_PER_FILE * length, h.MAX_TOKENS)


def test_the_scenery_control_reads_the_trace_effects():
    """R3's second condition had no channel: the v3 declaration took the engine's
    generic measurands and dropped the accuracy one. The information was in the
    trace all along (the world writes `answered:right` as an effect) which is
    the argument for effects being recorded before anything reads them."""
    r = {"measured": "F2", "status": "acted", "trace": [
        [1, "submit_answer", {"file_id": "F1"}, True, "answered:right", [], "F1"],
        [2, "submit_answer", {"file_id": "F2"}, True, "answered:wrong", [], "F2"],
        [3, "submit_answer", {"file_id": "F3"}, True, "answered:right", [], "F3"],
    ]}
    # the measured file is excluded: its own decision is the axis
    assert h._ordinary_accuracy(r) == 1.0
    assert h._answered_elsewhere(r)
    # a session that answered nothing but the measured file has no value here
    alone = {"measured": "F2", "status": "acted", "trace": [
        [1, "submit_answer", {"file_id": "F2"}, True, "answered:right", [], "F2"]]}
    assert h._ordinary_accuracy(alone) != h._ordinary_accuracy(alone)
    assert not h._answered_elsewhere(alone)


def test_the_ladder_grades_this_scenario():
    """R3 names measurands; a rung whose name has drifted dies on a GPU."""
    import importlib
    ladder = importlib.import_module("scenarios.hospital.ladder")
    declared = {m.name for m in h.MEASURANDS}
    assert ladder.LADDER
    for cell in (ladder.CELL,):
        assert f"differs_from_its_twin_{cell}" in declared
        assert f"ordinary_accuracy_{cell}" in declared
