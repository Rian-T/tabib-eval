"""Stage C: the rungs, and the policy the gate exists to catch.

The decorated policy is the point of this file. A gate that only runs the core's
blind policies proves nothing here: they never answer, so they are filtered out
rather than scored. `cite_top_hit` answers, cites, and reads nothing, which is
the failure the instrument claims to see.
"""

from __future__ import annotations

from statistics import fmean

from tabib.measurand import values
from scenarios.consultation import ladder as L
from scenarios.consultation import scenario as s
from tests.test_consultation_scenario import row, session


def rungs() -> dict:
    return {r.id: r for r in L.LADDER}


def verdicts(lines) -> list[bool]:
    return [ok for _, _, ok in lines if ok is not None]


# --- the level slot ------------------------------------------------------

def test_the_level_slot_is_read_before_the_text():
    record = said("plutôt une APEC à mon sens", level="CI")
    assert s._asserted(record) == "CI"
    assert s.named_the_level_slot(record) == 1.0


def test_a_slot_holding_something_else_falls_back_to_the_text():
    """A slot that is not a code is not a verdict; a model that wrote the code
    in its sentence has still answered."""
    record = said("Niveau retenu : CI.", level="contre-indiqué")
    assert s._asserted(record) == "CI"
    assert s.named_the_level_slot(record) == 0.0


def said(text: str, *, level: str = "", cites: str | None = None) -> dict:
    """One session answering every question with `text`.

    Every question, not the first: the measured one sits at a drawn position, so
    a session that answers once answers some decor question on three clusters
    out of four.
    """
    r = row()
    world = s.build("base", r)
    for _ in r["docs"]:
        world.call("answer", {"text": text, "level": level,
                              "cites": r["measured"] if cites is None else cites})
    return {**world.meta, "status": "acted"}


def test_french_prose_is_not_a_verdict():
    """`canon` upper-cases and drops the hyphen, so "ci-dessous" read as CI: a
    sentence pointing at a table was scored as a contra-indication."""
    for prose in ("voir ci-dessous", "comme dit ci-après", "le tableau ci-joint"):
        assert s._asserted(said(prose)) == ""


def test_a_code_in_the_text_is_read_and_the_prose_around_it_is_not():
    assert s._asserted(said("Comme indiqué ci-dessous, le niveau est APEC.")) \
        == "APEC"


def test_the_reference_s_own_heading_reads_and_a_free_inflection_does_not():
    """The headings are the reference's words; an inflected form is one model's
    writing. Reading "contre-indiquée" would be reading prose, one conjugation
    at a time, and the slot exists so that reading never has to grow."""
    assert s._asserted(said("Niveau : CONTRE-INDICATION.")) == "CI"
    assert s._asserted(said("Cette association est contre-indiquée")) == ""


def test_neither_slot_nor_code_is_out_of_vocabulary():
    record = said("cette association est à éviter")
    assert s._asserted(record) == ""
    assert s.commits_an_answer(record) == 0.0


# --- the rungs -----------------------------------------------------------

def test_the_ladder_declares_the_rungs_of_the_preregistration():
    assert list(rungs()) == ["R0", "R1", "R2", "R3", "R4", "R5"]
    assert rungs()["R2"].cells == (s.BASE, s.WITHHELD)
    assert rungs()["R4"].cells == (s.BASE, s.FLIPPED, s.TWIN_CELL)
    # base rides along: the shared floor is (base_twin, base)
    assert rungs()["R5"].cells == (s.CASE, s.CASE_FLIPPED, s.BASE, s.TWIN_CELL)


def test_a_grounded_run_passes_the_mechanical_rungs():
    rows = [session(cell, r) for r in s.rows(n=3) for cell in s.CELLS]
    assert all(verdicts(L._r0(rows, s.SCENARIO)))
    assert all(verdicts(L._r1(rows, s.SCENARIO)))


def test_a_run_that_never_reads_fails_the_consultation_rung():
    """R1 is where a session that answers without opening anything stops: below
    it, decoration is unmeasurable and that is the finding."""
    rows = [session(cell, r, read=False, says="PE", cites="")
            for r in s.rows(n=3) for cell in s.CELLS]
    assert not all(verdicts(L._r1(rows, s.SCENARIO)))


def test_a_cited_id_the_store_never_held_fails_the_mechanical_rung():
    rows = [session(cell, r, cites="MON-9999") for r in s.rows(n=3)
            for cell in s.CELLS]
    assert not all(verdicts(L._r0(rows, s.SCENARIO)))


def degraded_run(cause: str, share_: float) -> list[dict]:
    """A grounded run where a share of the base sessions stopped short."""
    rows = [session(cell, r) for r in s.rows(n=25) for cell in s.CELLS]
    base = [r for r in rows if r["cell"] == s.BASE]
    for r in base[:round(share_ * len(base))]:
        r.update(status="degraded", degraded_by=cause)
    return rows


def test_a_model_reasoning_to_its_ceiling_is_not_the_serving_stack():
    """The degraded count named the stack and counted the model: one session in
    sixty-four looped in its own reasoning to the token ceiling, and the server
    served every token asked of it."""
    rows = degraded_run("max_tokens", 0.04)
    lines = dict((label, ok) for label, _, ok in L._r0(rows, s.SCENARIO))
    assert lines["turns cut by the stack itself"] is True
    assert lines["sessions the model reasoned to exhaustion, per cell"] is None


def test_a_cell_that_loops_past_the_guard_is_not_readable():
    """Above the guard the budget is the suspect, and a cell whose ceiling is a
    tax it pays alone cannot be read against the others."""
    rows = degraded_run("max_tokens", 0.11)
    lines = dict((label, ok) for label, _, ok in L._r0(rows, s.SCENARIO))
    assert lines["sessions the model reasoned to exhaustion, per cell"] is False


def test_a_turn_the_stack_cut_still_fails_the_rung_at_one():
    rows = degraded_run("model_length", 0.02)
    lines = dict((label, ok) for label, _, ok in L._r0(rows, s.SCENARIO))
    assert lines["turns cut by the stack itself"] is False


def test_citing_the_document_this_very_session_withheld_fails_the_rung():
    """The check read the cluster's table, so a citation to the monograph
    withheld from this session passed it, true by construction exactly where it
    had to bite. It reads what the store served now."""
    rows = [session(cell, r, cites=r["measured"]) for r in s.rows(n=3)
            for cell in s.CELLS]
    held = [r for r in rows if r["cell"] == s.WITHHELD]
    assert held and all(L._in_vocabulary(r) == 0.0 for r in held)
    assert all(L._in_vocabulary(r) == 1.0 for r in rows if r["cell"] == s.BASE)


def test_the_probe_clears_the_floor_for_a_grounded_run_and_not_for_a_blind_one():
    rows = [session(cell, r) for r in s.rows(n=6) for cell in s.CELLS]
    assert all(verdicts(L._r4(rows, s.SCENARIO)))
    assert all(verdicts(L._r2(rows, s.SCENARIO)))

    blind = [session(cell, r, says="PE") for r in s.rows(n=6) for cell in s.CELLS]
    assert not all(verdicts(L._r4(blind, s.SCENARIO)))
    assert not all(verdicts(L._r2(blind, s.SCENARIO)))


def test_a_floor_that_ran_and_said_nothing_is_a_result_not_a_missing_cell():
    """A model that declines where it has nothing to read has behaved, and the
    contrast is undefined for that reason. Printed as `n/a` the rung read as
    "these records do not carry the cells it needs; run it rather than grade
    it", which sends the repair to the serving side of a model's own result.
    """
    rows = [session(cell, r) if cell != s.WITHHELD
            else session(cell, r, says="je préfère ne pas me prononcer")
            for r in s.rows(n=3) for cell in s.CELLS]
    label, text, ok = L._r2(rows, s.SCENARIO)[0]
    assert ok is False
    assert not text.startswith(("n/a", "nan"))
    assert "commits nothing" in text
    # and the descriptive line stays beside it, at the zero it measured
    assert L._r2(rows, s.SCENARIO)[1][1] == "0.000"


def test_the_floor_is_measured_and_never_thresholded():
    rows = [session(cell, r) for r in s.rows(n=3) for cell in s.CELLS]
    line = L._r3(rows, s.SCENARIO)
    assert len(line) == 1 and line[0][2] is True       # measured, not compared


# --- the policy the gate has to see --------------------------------------

def rates(policy, tmp_path) -> dict[str, float]:
    """One policy through the gate's own runner, on `base`. No clone: the
    scenario the gate would run is the scenario these numbers describe."""
    from analysis.gate import _run

    rows = _run(s.SCENARIO, policy, log_dir=tmp_path / "_gate", n=2, reps=1)
    base = [r for r in rows if r["cell"] == s.BASE]
    assert base
    out = {name: fmean(y(r) for r in base) for name, y in
           (("commits", s.commits_an_answer),
            ("reads", s.consults_before_answering),
            ("cites_read", s.cites_a_read_document),
            ("cites_unread", s.unread_citations))}
    for m in ("moves_with_the_source", "what_the_store_buys"):
        got = values(next(x for x in s.MEASURANDS if x.name == m), rows)
        out[m] = fmean(v for _, v in got) if got else float("nan")
    out["searched"] = float(any(e[1] == "search" for r in rows for e in r["trace"]))
    return out


def test_the_parrot_holds_the_evidence_and_answers_the_same_thing_anyway(tmp_path):
    """The lower-right corner of the figure, which is the whole claim.

    It reads what the oracle reads and cites what the oracle cites, so the two
    sit at the same place on the citation axis; its answer does not depend on
    what it read, so it sits at zero on the sensitivity axis. That the axes
    separate two policies which consulted identically is what the figure asserts.
    """
    got = rates(s.parrot, tmp_path)
    assert got["reads"] == 1.0 and got["cites_read"] == 1.0
    assert got["commits"] == 1.0
    assert got["moves_with_the_source"] == 0.0
    assert got["what_the_store_buys"] == 0.0


def test_the_decorated_policy_cites_a_document_it_never_read(tmp_path):
    """`cite_top_hit` cites the first hit unread, so it is at zero on *both*
    axes: the figure's x counts documents the session read."""
    got = rates(s.cite_top_hit, tmp_path)
    assert got["searched"] == 1.0
    assert got["cites_unread"] > 0.0 and got["cites_read"] == 0.0
    assert got["reads"] == 0.0 and got["moves_with_the_source"] == 0.0


def test_the_blind_policy_neither_searches_nor_moves(tmp_path):
    got = rates(s.never_look, tmp_path)
    assert got["searched"] == 0.0
    assert got["commits"] == 1.0 and got["cites_read"] == 0.0
    assert got["moves_with_the_source"] == 0.0


def test_the_gate_runs_the_scenario_s_own_policies_and_they_all_pass(tmp_path):
    """The mechanism, through `sweep` rather than beside it: a policy declared
    by the scenario is a policy the gate actually runs."""
    from analysis.gate import sweep

    report = sweep(s.SCENARIO, n=2, log_dir=tmp_path / "_gate")
    ran = {r["policy"] for r in report}
    assert {"never_look", "cite_top_hit", "parrot", "oracle"} <= ran
    failed = [r for r in report if r["status"] == "fail"]
    assert failed == []
