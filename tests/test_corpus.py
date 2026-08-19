"""The ground truth is the one thing every scenario trusts without checking.

These tests exist because it was wrong. The extraction reads a two-column PDF
and recognises a substance heading by its shape; a heading it fails to recognise
is swallowed into the previous description, and every row of the block that
follows is then filed under the previous substance. That produced 221
misattributed rows: a contra-indication between two substances that have
nothing to do with each other, and nothing downstream could have noticed.
"""

from __future__ import annotations

import csv
import re

from scenarios.ansm import corpus

# a description ending in a long uppercase run is a swallowed heading
SWALLOWED = re.compile(r"(?:^|[.\s])([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ' \-()+,]{8,})\s*$")


def raw() -> list[dict]:
    with corpus.TRUTH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_no_substance_heading_was_swallowed_into_a_description():
    hits = [f"{r['substance']} -> {SWALLOWED.search(r['description'].strip()).group(1)}"
            for r in raw() if SWALLOWED.search(r["description"].strip())]
    assert hits == [], hits


def test_every_row_carries_a_known_level_and_both_names():
    for row in raw():
        assert row["niveau"] in corpus.HEADING, row
        assert row["substance"].strip() and row["interactant"].strip(), row


def test_truncated_passages_stay_out_of_the_corpus():
    # the extraction loses a line across some page breaks; those passages are
    # excluded rather than served, and the ceiling is asserted so that a
    # regression in the extraction shows up here instead of in a result
    dropped = [r for r in raw()
               if corpus.truncated(corpus.Entry(r["substance"], r["interactant"],
                                                r["niveau"], r["description"],
                                                r["conduite"]))]
    assert len(dropped) <= 30, f"{len(dropped)} truncated passages"
    assert not any(corpus.truncated(e) for e in corpus.load())


def test_a_pair_listed_at_two_levels_has_no_ground_truth_and_is_dropped():
    seen = {}
    for e in corpus.load():
        assert e.pair_id not in seen, f"{e.pair_id} kept twice"
        seen[e.pair_id] = e.level


def test_canon_is_only_ever_compared_through_itself():
    # the rule that cost two bugs in one night: an identifier built by a
    # function is compared only through that function
    assert corpus.canon("PHÉNOBARBITAL") == corpus.canon("PHENOBARBITAL")
    assert corpus.canon("acide  cholique") == "ACIDE CHOLIQUE"
    assert corpus.canon("IMAO-B") == "IMAO B"
    pair = corpus.Entry("Aspirine", "IBUPROFÈNE", "CI", "x.", "")
    assert pair.pair_id == "ASPIRINE__IBUPROFENE"
    assert pair.keys == {"ASPIRINE", "IBUPROFENE"}


def test_a_passage_is_the_official_entry_and_nothing_else():
    entry = next(e for e in corpus.load() if e.conduite.strip())
    text = entry.passage()
    assert text.startswith(f"{entry.substance} + {entry.interactant}")
    assert corpus.HEADING[entry.level] in text
    assert entry.description in text
    assert text.count("Conduite à tenir") == 1
