"""What S1 holds fixed, asserted rather than claimed.

Every served version is a coherent claim: the pair and one heading, no prose
under it. A relabelled entry with its description left in asserts one level and
describes another, and what a model does with that object measures how it
resolves a contradiction we built rather than whether it follows a source.
"""

from __future__ import annotations

from inspect_ai.model import ChatMessageUser

from scenarios.ansm import corpus
from scenarios.source_fidelity import scenario as s1

SERVED = ("agree", "twin", "harder", "softer", "mismatched", "placebo")


def rows(n=12):
    return s1.rows(n=n)


def _said(text: str) -> ChatMessageUser:
    return ChatMessageUser(content=text)


def test_every_served_version_is_a_coherent_claim():
    # two lines: the pair, and one heading. Nothing under it can disagree with
    # it, so a false version is a false claim and not a self-contradiction
    for i, row in enumerate(rows()):
        for cell in SERVED:
            assert row[cell].count("\n") == 1, (cell, i)


def test_the_twin_is_byte_identical_to_the_cell_it_duplicates():
    # the whole point: if two cells serving the same text disagree, the size of
    # that disagreement is the floor under every contrast this scenario reports
    for i, row in enumerate(rows()):
        assert row["twin"] == row["agree"], i
        assert row["twin_level"] == row["agree_level"]


def test_only_the_heading_differs_between_the_pair_s_own_versions():
    # the mismatched cell is another pair's entry, so it differs on both lines
    # by design and is excluded here
    for i, row in enumerate(rows()):
        own = ("agree", "harder", "softer", "placebo")  # twin duplicates agree
        assert len({row[c].split("\n")[0] for c in own}) == 1, i
        assert len({row[c].split("\n")[1] for c in own}) == 4, i


def test_the_true_level_is_spread_over_the_corpus():
    # with one true level, "gave the right answer" is "emitted that one label",
    # and the labels a model will emit differ by a factor of four between models
    levels = {row["level"] for row in rows(24)}
    assert len(levels) > 1, levels
    assert levels <= set(s1.LEVELS[1:-1])


def test_each_unit_carries_both_directions():
    for row in rows():
        got = s1.steps(row["level"])
        assert got["harder"] != got["softer"]
        assert row["harder_level"] == got["harder"]
        assert row["softer_level"] == got["softer"]


def test_the_manipulated_levels_follow_the_unit_s_own_level():
    assert s1.steps("AD") == {"harder": "CI", "softer": "PE"}
    assert s1.steps("PE") == {"harder": "AD", "softer": "APEC"}
    for edge in ("CI", "APEC"):
        try:
            s1.steps(edge)
        except ValueError:
            continue
        raise AssertionError(f"{edge} has no neighbour on one side and was accepted")


def test_the_mismatched_cell_serves_another_pair():
    # the one cell where not following is unambiguously right: without it,
    # "follows every time" and "the instrument cannot record a refusal" read
    # exactly alike
    for i, row in enumerate(rows()):
        assert not row["mismatched"].startswith(row["couple"]), i


def test_the_placebo_replaces_the_heading_rather_than_adding_to_it():
    for i, row in enumerate(rows()):
        agree, placebo = (row[c].split("\n")[1] for c in ("agree", "placebo"))
        assert placebo != agree and agree not in placebo, i
        assert row["placebo"].split("\n")[0] == row["agree"].split("\n")[0]


def test_the_placebo_adds_no_token_of_the_answer_vocabulary():
    codes = lambda line: {c for c in s1.LEVELS if c in line}
    for i, row in enumerate(rows()):
        agree, placebo = (row[c].split("\n")[1] for c in ("agree", "placebo"))
        assert codes(placebo) - codes(agree) == set(), i


def test_the_placebo_still_states_the_level_the_entry_carries():
    for i, row in enumerate(rows()):
        heading = row["placebo"].split("\n")[1].upper()
        assert corpus.HEADING[row["level"]].upper() in heading, i
        assert not any(corpus.HEADING[lvl].upper() in heading
                       for lvl in s1.steps(row["level"]).values()), i


def test_a_perfect_reader_finds_nothing_in_the_placebo():
    for row in rows(4):
        read = [s1.oracle([_said(row[cell])], None, None, None)
                for cell in ("placebo", "agree")]
        levels = {out.message.tool_calls[0].arguments["level"] for out in read}
        assert levels == {row["level"]}


def test_every_cell_declares_what_the_excerpt_claims():
    # compliance is read from this, so the analysis never re-parses served text
    for row in rows():
        for cell in SERVED:
            assert row[f"{cell}_level"] in s1.LEVELS, cell
        assert row["agree_level"] == row["level"]
        assert row["closed"] == ""
