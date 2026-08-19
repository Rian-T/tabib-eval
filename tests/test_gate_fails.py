"""A gate nobody has seen fail is not a gate.

Two toy scenarios differing in one line: how the measurand is defined. The sound
one asks what the model did, the broken one asks whether the model was right,
and the two served cells disagree on what right means. The second is the exact
shape of a real defect: an effect entirely reproducible by a policy that reads
nothing, so the gate must reject it and accept the first.
"""

from __future__ import annotations

import pytest
from inspect_ai.model import ModelOutput

from analysis.gate import sweep
from tabib import Measurand, Scenario, World
from tabib.nulls import MOCK
from tests.conftest import TOY_ACTS, toy_tools

SERVED = {"v1": "élevé", "v0": "faible"}


def oracle(messages, tools, tool_choice, config) -> ModelOutput:
    """Reads the served level and acts on it: the behaviour under test."""
    served = messages[-1].text if messages else ""
    if SERVED["v1"] in served:
        return ModelOutput.for_tool_call(MOCK, "send", {"level": "high"})
    return ModelOutput.for_tool_call(MOCK, "hold", {})


def scenario(name: str, measurand: Measurand) -> Scenario:
    def rows(*, n=6, seed=0):
        return [{"id": f"p{i}"} for i in range(n)]

    def build(cell: str, row: dict) -> World:
        return World(
            tools=toy_tools(), # the answer key: what a correct answer looks like differs by cell,
            # which is exactly the mistake the broken measurand makes
            meta={"level": "high" if cell == "v1" else ""},
            prompt=f"Dossier. La source indique un niveau {SERVED[cell]}.")

    return Scenario(name=name, acts=TOY_ACTS, system="Tu traites des dossiers.",
                    rows=rows, build=build, measurands=(measurand,), oracle=oracle)


SOUND = scenario("toy_sound",
                 # what the model DID: the same act scores the same on both sides
                 Measurand("follows_source", lambda r: float(r["act"] == "send"),
                           ("v1", "v0")))

BROKEN = scenario("toy_broken",
                  # whether the model was RIGHT, with two cells that disagree on
                  # right: a constant act is correct on one side, wrong on the other
                  Measurand("looks_like_tracking",
                            lambda r: float(r["payload"] == r["level"]),
                            ("v1", "v0")))

BACKWARDS = scenario("toy_backwards",
                     # the measurand counts the act the oracle does NOT take under
                     # v1, so the effect comes out with the wrong sign
                     Measurand("follows_source", lambda r: float(r["act"] == "hold"),
                               ("v1", "v0")))


def test_the_gate_accepts_a_scenario_whose_contrast_needs_reading(tmp_path):
    report = sweep(SOUND, n=4, log_dir=tmp_path / "_gate")
    assert all(r["status"] == "ok" for r in report), \
        [r for r in report if r["status"] != "ok"]
    assert next(r["got"] for r in report if r["oracle"]) == 1.0


def test_a_measurand_read_against_the_answer_key_rewards_reading_nothing(tmp_path):
    # the diagnostic signature of the defect: scoring "was the model right"
    # across two cells that disagree on right inverts the instrument. The
    # constant answer collects the whole effect, the perfect reader collects none
    report = sweep(BROKEN, n=4, log_dir=tmp_path / "_gate")
    constant = next(r for r in report if r["policy"] == "const:send=high")
    oracle_line = next(r for r in report if r["oracle"])
    assert constant["got"] == 1.0 and constant["status"] == "fail"
    assert oracle_line["got"] == 0.0 and oracle_line["status"] == "fail"


def test_the_gate_rejects_an_oracle_that_moves_it_backwards(tmp_path):
    report = sweep(BACKWARDS, n=4, log_dir=tmp_path / "_gate")
    line = next(r for r in report if r["oracle"])
    assert line["got"] == -1.0 and line["status"] == "fail"


def test_a_measurand_may_declare_the_direction_it_expects(tmp_path):
    signed = Measurand("follows_source", lambda r: float(r["act"] == "hold"),
                       ("v1", "v0"), oracle_moves="down")
    report = sweep(scenario("toy_signed", signed), n=4, log_dir=tmp_path / "_gate")
    assert all(r["status"] == "ok" for r in report)


def test_every_cluster_is_paired_on_both_sides(tmp_path):
    report = sweep(SOUND, n=4, log_dir=tmp_path / "_gate")
    assert {r["clusters"] for r in report} == {4}
    assert {r["dropped"] for r in report} == {0}
