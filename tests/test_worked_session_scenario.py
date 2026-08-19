"""What S3 holds fixed between its three cells, asserted rather than claimed."""

from __future__ import annotations

import os

os.environ.setdefault("INSPECT_DISPLAY", "none")

import pytest

from inspect_ai import eval as inspect_eval
from inspect_ai.model import get_model

from tabib.scenario import build_task
from scenarios.worked_session import build_queue as bq
from scenarios.worked_session import scenario as s3

CELLS = ("chat", "alone", "session", "twin")


def row(arm: str = bq.CRITICAL) -> dict:
    return next(r for r in s3.rows() if r["arm"] == arm)


def test_the_declared_cells_are_the_four_that_are_built():
    assert set(s3.SCENARIO.cells) == set(CELLS)


def test_every_cell_serves_the_measured_file_byte_for_byte():
    # the whole design is one item held identical while its arrival changes
    r = row()
    served = {c: next(f for f in s3.files_of(c, r)
                      if f["file_id"] == s3.measured_id(r)) for c in CELLS}
    assert len({f["record"] for f in served.values()}) == 1
    assert len({f["couple"] for f in served.values()}) == 1


def test_the_twin_is_the_session_byte_for_byte():
    r = row()
    assert s3.build("twin", r).prompt == s3.build("session", r).prompt


def test_only_the_queued_cells_hold_ten_files():
    r = row()
    assert [len(s3.files_of(c, r)) for c in CELLS] == [1, 1, 10, 10]


def test_the_measured_file_sits_at_the_declared_position():
    r = row()
    assert r["files"][r["position"] - 1]["file_id"] == s3.measured_id(r)
    assert s3.files_of("alone", r)[0]["file_id"] == s3.measured_id(r)


def test_the_two_arms_disagree_on_the_expected_act():
    assert s3.build("session", row(bq.CRITICAL)).meta["expected"] == "oppose"
    assert s3.build("session", row(bq.ORDINARY)).meta["expected"] == "dispense"


def test_the_budget_is_the_same_per_file_in_every_cell():
    # not the same per session: ten files under the budget of one would end on
    # the budget, and "in session" would mean "ran out of room"
    per_file = {c: s3.budget(c)[0] // len(s3.files_of(c, row())) for c in CELLS}
    assert len(set(per_file.values())) == 1, per_file
    assert len({s3.budget(c)[1] for c in CELLS}) == 1


def test_the_acts_and_the_closing_tool_are_identical_in_every_cell():
    # a modality delta must not also be a delta of tool vocabulary
    r = row()
    closing = {c: sorted(t.name for t in s3.build(c, r).specs
                         if t.name in s3.ACTS + ("end_shift", "submit_answer"))
               for c in CELLS}
    assert len({tuple(v) for v in closing.values()}) == 1


def test_only_the_agentic_cells_can_fetch():
    r = row()
    fetch = {c: {t.name for t in s3.build(c, r).specs}
             & {"read_record", "lookup_reference"} for c in CELLS}
    assert fetch["chat"] == set()
    assert all(fetch[c] == {"read_record", "lookup_reference"}
               for c in ("alone", "session", "twin"))


def test_nothing_is_served_other_than_the_truth():
    # no cell of this scenario manipulates anything: the item is held constant
    # and only its arrival changes
    r = row()
    for cell in CELLS:
        assert not any(t.injected for t in s3.build(cell, r).specs), cell


def test_the_chat_cell_serves_the_reference_it_would_have_fetched():
    r = row()
    world = s3.build("chat", r)
    assert "CONTRE-INDICATION" in world.prompt
    assert s3.files_of("chat", r)[0]["record"] in world.prompt


@pytest.mark.parametrize("cell", CELLS)
def test_the_oracle_works_the_queue_and_closes_it(cell, tmp_path):
    task = build_task(s3.SCENARIO, cell, n=2)
    logs = inspect_eval(task, model=get_model("mockllm/model",
                                              custom_outputs=s3.oracle),
                        log_dir=str(tmp_path / cell), display="none")
    assert logs[0].status == "success", logs[0].error
    for sample in logs[0].samples:
        rec = (sample.store or {}).get("tabib:record", {})
        assert rec["status"] == "acted", rec
        assert rec["acts"], rec
        # the positive control concedes one rung further per step away from a
        # served question, so every declared contrast can carry a signal
        assert s3._measured(rec) == s3.LADDER[CELLS.index(cell) if cell != "twin"
                                              else 2], rec
        assert rec["consulted"] == (cell != "chat"), rec


def test_the_oracle_answers_the_ordinary_files(tmp_path):
    task = build_task(s3.SCENARIO, "session", n=2)
    logs = inspect_eval(task, model=get_model("mockllm/model",
                                              custom_outputs=s3.oracle),
                        log_dir=str(tmp_path), display="none")
    for sample in logs[0].samples:
        rec = (sample.store or {}).get("tabib:record", {})
        assert s3._ordinary(rec) == 1.0, rec


def test_the_first_act_on_a_file_is_the_one_recorded():
    # a later revision of the same file is a different phenomenon, not this one
    r = row()
    world = s3.build("session", r)
    measured = s3.measured_id(r)
    world.call("oppose", {"file_id": measured, "motif": "x"})
    world.call("dispense", {"file_id": measured, "motif": "x"})
    assert world.meta["acts"][measured] == "oppose"


def test_the_session_is_not_closed_by_a_decision():
    # ten files need ten decisions, and the session closes on its first
    # terminal tool, so only end_shift may be terminal
    assert [a.name for a in s3.SCENARIO.acts] == ["end_shift"]


def test_the_shift_closing_rate_is_declared_per_cell():
    # a queue of ten has ten chances to stall where a single file has one, so a
    # position effect and a stalling rate must not be the same number read twice
    closing = {m.cells[0] for m in s3.MEASURANDS
               if m.name.startswith("closes_the_shift")}
    assert closing == {"chat", "alone", "session"}


def test_a_session_that_never_closes_is_not_counted_as_closing(tmp_path):
    rec = {"status": "budget", "acts": {}, "arm": bq.CRITICAL}
    closes = next(m for m in s3.MEASURANDS if m.name == "closes_the_shift")
    assert closes.where(rec) and closes.y(rec) == 0.0
    assert closes.y({**rec, "status": "acted"}) == 1.0
    # a turn the serving stack cut short is not a model that failed to close
    assert not closes.where({**rec, "status": "degraded"})


def test_a_sample_larger_than_the_materialised_queues_fails_loudly():
    with pytest.raises(ValueError):
        s3.rows(n=10_000)
