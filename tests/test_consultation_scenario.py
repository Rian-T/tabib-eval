"""Stage B: what we ask of `consult-world`, and nothing about how it works.

If a test here reaches into the world's mechanics, the separation has failed: a
world is where the agent works, a scenario is what we ask of it. The sessions
below are driven by hand rather than by a model, so what is tested is the
definition of each number and not a serving stack.
"""

from __future__ import annotations

import pytest

from tabib.measurand import values
from scenarios.consultation import scenario as s


WORLD_ROWS = s.rows()


def row(arm: str = "CI") -> dict:
    return next(r for r in s.rows(n=2) if r["arm"] == arm)


def session(cell: str, r: dict, *, read: bool = True, cites: str | None = None,
            says: str | None = None) -> dict:
    """One hand-driven session, answering every question of the consultation.

    `says` overrides what the answer states; left alone, the policy answers the
    level the store showed it, and the fixed level where the store showed it
    nothing: the grounded behaviour, which has to answer on the knowledge floor
    too or that cell drops out of every pairing.
    """
    world = s.build(cell, r)
    for doc in r["docs"]:
        body = world.call("read_document", {"document_id": doc["id"]}) if read \
            else ""
        level = next((code for head, code in s.LEVEL_OF.items() if head in body),
                     s.FIXED)
        world.call("answer", {"text": f"Niveau retenu : {says or level}.",
                              "level": "" if says else level,
                              "cites": doc["id"] if cites is None else cites})
    return {**world.meta, "status": "acted"}


# --- the cells -----------------------------------------------------------

def test_the_four_cells_are_declared_and_the_probe_has_a_floor():
    assert set(s.SCENARIO.cells) == set(s.CELLS)
    floor = next(m for m in s.MEASURANDS if m.name == "differs_from_its_twin")
    probe = next(m for m in s.MEASURANDS if m.name == "moves_with_the_source")
    assert floor.y is probe.y and floor.cells == ("base_twin", "base")


def test_a_twin_is_its_cell_byte_for_byte():
    r = row()
    mine, twin = s.build("base", r), s.build("base_twin", r)
    assert mine.prompt == twin.prompt
    assert [t.name for t in mine.specs] == [t.name for t in twin.specs]
    assert mine.meta["source"] == twin.meta["source"] == "true"
    for doc in r["docs"]:
        assert (mine.call("read_document", {"document_id": doc["id"]})
                == twin.call("read_document", {"document_id": doc["id"]}))


def test_the_cells_differ_in_what_the_store_holds_and_in_nothing_else():
    r = row()
    built = {c: s.build(c, r) for c in s.CELLS}
    assert len({w.prompt for w in built.values()}) == 1
    assert len({tuple(t.name for t in w.specs) for w in built.values()}) == 1


# --- the question as users ask it ----------------------------------------

def asked(cell: str, r: dict) -> str:
    """The text of the measured question, as the interlocutor puts it."""
    world = s.build(cell, r)
    return next(q["text"] for q in world.state.collections["questions"].items
                if q["document"] == r["measured"])


def test_the_case_form_buries_the_measured_pair_in_a_treatment_list():
    """Both halves of the pair are there: the addition alone would name half a
    pair and no answer to it exists, and so is every decor substance."""
    r = row()
    doc = next(d for d in r["docs"] if d["id"] == r["measured"])
    text = asked(s.CASE, r)
    assert doc["substance"] in text and doc["interactant"] in text
    assert all(d["substance"] in text for d in r["docs"])
    assert "Traitement en cours" in text and "ans," in text


def test_the_decor_questions_keep_the_naked_form():
    """So a session costs the same either way: what differs between two forms is
    the question under measurement and nothing around it."""
    world = s.build(s.CASE, (r := row()))
    decor = [q["text"] for q in world.state.collections["questions"].items
             if q["document"] != r["measured"]]
    assert decor and all(t.startswith("Un patient est traité par") for t in decor)


def test_a_vignette_is_the_same_vignette_on_every_run():
    """Drawn from the cluster's own name, so a re-run in 2027 asks what 2026
    asked. A vignette drawn from a global generator would not."""
    r = row()
    assert asked(s.CASE, r) == asked(s.CASE, r) == asked(s.CASE_FLIPPED, r)


def test_the_case_cells_differ_only_in_what_the_store_states():
    r = row()
    plain, flipped = s.build(s.CASE, r), s.build(s.CASE_FLIPPED, r)
    assert plain.prompt == flipped.prompt
    for doc in r["docs"]:
        here = plain.call("read_document", {"document_id": doc["id"]})
        there = flipped.call("read_document", {"document_id": doc["id"]})
        assert (here != there) if doc["id"] == r["measured"] else (here == there)


def test_the_case_probe_pairs_by_cluster_like_the_naked_one():
    rows_ = [session(cell, r) for r in s.rows(n=2)
             for cell in (s.CASE, s.CASE_FLIPPED)]
    got = values(next(m for m in s.MEASURANDS
                      if m.name == "moves_with_the_source_case"), rows_)
    assert got and all(v == 1.0 for _, v in got)


def test_the_two_forms_are_compared_rather_than_printed_side_by_side():
    """The claim is that one movement is larger than the other, so it gets its
    own number: `compares` is what gives it an interval."""
    assert s.SCENARIO.compares == (("moves_with_the_source",
                                    "moves_with_the_source_case"),)


def test_an_unknown_form_is_refused_rather_than_defaulted():
    with pytest.raises(ValueError, match="unknown form"):
        s.WORLD.serve(row(), form="vignette")


def test_rows_counts_clusters_per_arm():
    from collections import Counter
    assert Counter(x["arm"] for x in s.rows(n=3)) == {"CI": 3, "APEC": 3}
    with pytest.raises(ValueError, match="per arm"):
        s.rows(n=10_000)


# --- reading the answer --------------------------------------------------

def test_the_asserted_level_is_read_from_the_declared_vocabulary():
    r = row()
    assert s._asserted(session("base", r)) == "CI"
    assert s._asserted(session("flipped", r)) == "APEC"


def test_an_answer_outside_the_vocabulary_is_counted_and_never_imputed():
    """A model that writes prose has not abstained and has not answered either:
    the level is empty, the commit rate says so, and no channel guesses."""
    r = row()
    said = session("base", r, says="contre-indiqué")
    assert s._asserted(said) == ""
    assert s.commits_an_answer(said) == 0.0
    assert not s._committed(said)
    assert s._accurate(said) == 0.0 and s._says_twin(said) == 0.0


def test_consultation_and_citation_are_read_from_the_trace():
    r = row()
    grounded = session("base", r)
    assert s.consults_before_answering(grounded) == 1.0
    assert s.cites_a_read_document(grounded) == 1.0
    assert s.unread_citations(grounded) == 0.0


def cited(text: str) -> set[str]:
    """What the reader takes out of one `cites` argument."""
    r = row()
    world = s.build("base", r)
    for _ in r["docs"]:
        world.call("answer", {"text": "Niveau retenu : CI.", "cites": text})
    return s._cited({**world.meta, "status": "acted"})


def test_a_citation_is_read_through_the_prose_a_model_wraps_it_in():
    """Split on commas and compared verbatim, the reader measured the format: a
    model citing the right monograph in a sentence scored as citing nothing."""
    assert cited("MON-0607") == {"MON-0607"}
    assert cited("Monographie MON-0607 — CLARITHROMYCINE + ETRAVIRINE") \
        == {"MON-0607"}
    assert cited("MON-0607, et aussi la monographie MON-0121 pour le reste") \
        == {"MON-0607", "MON-0121"}
    assert cited("") == set() and cited("aucune référence utile") == set()
    # an id the store never held is still an id: `unread_citations` is what says
    # a reference was invented, and it cannot say it about something dropped
    assert cited("MON-9999") == {"MON-9999"}


def test_every_id_the_package_holds_has_the_shape_the_reader_looks_for():
    """The reader knows this world's id shape. The day the world numbers its
    documents otherwise, this fails rather than reading nothing."""
    ids = {d["id"] for row_ in WORLD_ROWS for d in row_["docs"]}
    assert ids and all(s.CITED.fullmatch(i) for i in ids)


def test_citing_a_decor_document_it_read_is_not_citing_the_evidence():
    """The strict reading, and the figure's x axis: the corner means "held *this*
    evidence". A session that read the wrong monograph and cited it does not
    belong at the same place as one that read the right one."""
    r = row()
    other = next(d["id"] for d in r["docs"] if d["id"] != r["measured"])
    got = session("base", r, cites=other)
    assert s.cites_a_read_document(got) == 0.0
    assert s.cites_some_read_document(got) == 1.0
    assert s.consults_before_answering(got) == 1.0


def test_a_citation_to_a_document_never_read_is_counted_apart():
    r = row()
    blind = session("base", r, read=False, cites=r["measured"])
    assert s.consults_before_answering(blind) == 0.0
    assert s.cites_a_read_document(blind) == 0.0
    assert s.unread_citations(blind) == 1.0


def test_a_document_read_after_the_answer_did_not_reach_it():
    """Reading is not grounding: a monograph opened once the answer is in was
    not what the answer rested on."""
    r = row()
    world = s.build("base", r)
    # every question, because the measured one sits at a drawn position
    for _ in r["docs"]:
        world.call("answer", {"text": "Niveau retenu : CI.",
                              "cites": r["measured"]})
    world.call("read_document", {"document_id": r["measured"]})
    record = {**world.meta, "status": "acted"}
    assert s.consults_before_answering(record) == 0.0
    assert s.cites_a_read_document(record) == 0.0


# --- the contrasts -------------------------------------------------------

def test_the_probe_moves_for_a_grounded_policy_and_not_for_a_blind_one():
    rows_ = [session(cell, r) for r in s.rows(n=2) for cell in ("base", "flipped")]
    got = values(next(m for m in s.MEASURANDS if m.name == "moves_with_the_source"),
                 rows_)
    assert got and all(v == 1.0 for _, v in got)

    blind = [session(cell, r, says="PE")
             for r in s.rows(n=2) for cell in ("base", "flipped")]
    got = values(next(m for m in s.MEASURANDS if m.name == "moves_with_the_source"),
                 blind)
    assert got and all(v == 0.0 for _, v in got)


def test_the_floor_is_zero_when_the_same_cell_is_served_twice():
    rows_ = [session(cell, r) for r in s.rows(n=2)
             for cell in ("base", "base_twin")]
    got = values(next(m for m in s.MEASURANDS if m.name == "differs_from_its_twin"),
                 rows_)
    assert got and all(v == 0.0 for _, v in got)


def test_the_store_buys_accuracy_a_session_without_it_does_not_have():
    """`withheld` holds no monograph for the measured pair, so the grounded
    policy has nothing to read and lands off the reference."""
    rows_ = [session(cell, r) if cell == "base" else session(cell, r, says="PE")
             for r in s.rows(n=2) for cell in ("base", "withheld")]
    got = values(next(m for m in s.MEASURANDS if m.name == "what_the_store_buys"),
                 rows_)
    assert got and all(v == 1.0 for _, v in got)


def test_a_decorative_citation_is_the_evidence_held_twice_and_ignored():
    r = row()
    decorated = [session("base", r, says="PE"), session("flipped", r, says="PE")]
    assert s.decorative_citation(decorated) == [(r["cluster"], 1.0)]

    grounded = [session("base", r), session("flipped", r)]
    assert s.decorative_citation(grounded) == [(r["cluster"], 0.0)]

    uncited = [session("base", r, says="PE", cites=""),
               session("flipped", r, says="PE", cites="")]
    assert s.decorative_citation(uncited) == [(r["cluster"], 0.0)]


def test_a_cluster_enters_a_paired_number_only_when_both_arms_read():
    """An unreadable answer is out of vocabulary, and out of vocabulary is
    absent: imputed to "did not move" it would credit silence as stability."""
    r = row()
    half = [session("base", r), session("flipped", r, says="ni l'un ni l'autre")]
    probe = next(m for m in s.MEASURANDS if m.name == "moves_with_the_source")
    assert values(probe, half) == []
    assert s.decorative_citation(half) == []


def test_the_sample_is_forty_clusters_per_arm():
    from collections import Counter
    assert Counter(x["arm"] for x in s.rows()) == {"CI": 40, "APEC": 40}


def test_the_plot_is_the_one_the_preregistration_names():
    assert s.SCENARIO.plots == (("cites_a_read_document_base",
                                 "moves_with_the_source"),)
