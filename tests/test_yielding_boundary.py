"""What S2 holds fixed, asserted rather than claimed."""

from __future__ import annotations

from scenarios.yielding_boundary import scenario as s2

CELLS = ("rest", "fact", "distress", "authority")


def test_the_four_requests_are_matched_on_length():
    # otherwise the longest request moves the boundary and the finding is about
    # wordcount: so wordcount is what has to be checked, and it was not: the
    # characters agreed to 7% while the words disagreed by 12%
    texts = [s2._text(f"{c}.txt") for c in CELLS if c != "fact"]
    for measure in (len, lambda t: len(t.split())):
        sizes = [measure(t) for t in texts]
        assert max(sizes) - min(sizes) <= 0.1 * max(sizes), sizes


def _dangerous_row():
    return next(r for r in s2.rows(n=4) if r["expected"] == "block")


def test_moving_the_fact_leaves_the_wording_untouched():
    row = _dangerous_row()
    assert s2.build("rest", row).prompt == s2.build("fact", row).prompt


def test_moving_the_tone_leaves_the_reference_untouched():
    # only `fact` may serve something other than the truth. Asserted through
    # build, not by re-evaluating the condition build uses: a test that repeats
    # the implementation checks nothing
    row = _dangerous_row()
    for cell in CELLS:
        consult = next(t for t in s2.build(cell, row).specs
                       if t.name == "consult_thesaurus")
        assert consult.injected == (cell == "fact"), cell


def test_the_relabelled_reference_still_logs_the_real_one():
    # the manipulation is declared: the truth channel keeps the honest entry,
    # so `warned` records what the reference actually said
    from scenarios.ansm import corpus
    entry = next(e for e in corpus.load() if e.level == "CI")
    served, truth = s2._tools(relabel=True)[0].handler(
        None, {"substance_a": entry.substance, "substance_b": entry.interactant})
    assert corpus.HEADING["PE"] in served
    assert corpus.HEADING["CI"] in truth


def test_both_arms_are_drawn_and_the_reference_separates_them():
    # every pair was contra-indicated, so blocking was always right and a model
    # that blocks on sight scored like one that reads. The second arm is the
    # reference's mildest level, where opposing is over-refusal by the
    # reference's own words: not "absent from the table", which would require
    # ruling out every family entry that might cover the pair
    rows = s2.rows(n=20)
    assert {r["expected"] for r in rows} == {"block", "authorise"}
    assert len([r for r in rows if r["expected"] == "block"]) == len(rows) // 2


def test_the_factual_manipulation_only_touches_the_arm_that_has_room():
    for row in s2.rows(n=8):
        served = any(t.injected for t in s2.build("fact", row).specs)
        assert served == (row["expected"] == "block"), row["level"]


def test_every_case_is_a_pair_a_prescriber_could_submit():
    from scenarios.ansm import corpus
    for row in s2.rows(n=20):
        assert not any(corpus.is_class_label(part)
                       for part in row["couple"].split(" + "))
