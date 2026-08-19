"""Stage A: the consultation package loads, is admitted, and serves what it says.

Mechanics only. No cell, no measurand and no threshold is tested here: what the
experiment asks of this world is the scenario's business, and a world that
passes these lines is a world an experiment can be written against.
"""

from __future__ import annotations

import json
import shutil

import pytest

from tabib import engine as en
from tabib import vagabond as vg
from tabib.worlds import WorldError, load_world

WORLD = load_world("consult-world")


def session(source: str = "true", arm: str = "CI"):
    row = next(r for r in WORLD.clusters() if r["arm"] == arm)
    return WORLD.serve(row, source=source), row


def measured(row: dict) -> dict:
    return next(d for d in row["docs"] if d["id"] == row["measured"])


# --- the package ---------------------------------------------------------

def test_the_package_declares_both_versions_and_its_reference():
    assert WORLD.VERSION == "consult-world/1.6.0"
    assert WORLD.MANIFEST["world"]["engine"] == ">=0.1,<0.2"
    assert "ANSM" in WORLD.MANIFEST["world"]["reference"]
    world, _ = session()
    assert world.meta["world"] == WORLD.VERSION
    assert world.meta["engine"] == en.VERSION


def test_content_that_moved_under_the_package_is_caught_at_load(tmp_path):
    copy = tmp_path / "consult-world"
    shutil.copytree(WORLD.PATH, copy)
    blob = copy / "content" / "clusters.json"
    rows = json.loads(blob.read_text(encoding="utf-8"))
    rows[0]["arm"] = "TAMPERED"
    blob.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(WorldError, match="not the file this package declares"):
        load_world(str(copy))


def test_a_vignette_carries_exactly_one_documented_interaction():
    """[A11], checked on the content the package ships and not on the draw.

    In the case form the treatment is the measured pair's own substance plus the
    decor's, and the measured interactant is the drug being added. Every pair
    that meets on that patient is checked against the reference:

    - a decor substance paired with the drug added leaves "this pair" without a
      single answer, and the question stops being well posed;
    - two treatment drugs paired with each other distract unequally from one
      cluster to the next, which lands in the naked-against-case comparison as a
      difference between clusters rather than between forms.

    The measured pair is the one interaction the vignette carries, and it is why
    the question has an answer. Verified against the reference itself, because a
    check that reads the drawing logic is one the drawing passes by construction.
    """
    from itertools import combinations

    from scenarios.ansm import corpus

    listed = {e.keys for e in corpus.load()}
    clashes = []
    for row in WORLD.clusters():
        mine = next(d for d in row["docs"] if d["id"] == row["measured"])
        added = mine["interactant"]
        treatment = [mine["substance"]] + [d["substance"] for d in row["docs"]
                                           if d["id"] != row["measured"]]
        pairs = [(a, b) for a, b in combinations(treatment + [added], 2)
                 if {corpus.canon(a), corpus.canon(b)}
                 != {corpus.canon(mine["substance"]), corpus.canon(added)}]
        clashes += [(row["cluster"], a, b) for a, b in pairs
                    if frozenset((corpus.canon(a), corpus.canon(b))) in listed]
    assert clashes == []
    # and the pair under measurement is still documented, or the vignette would
    # carry a question the reference cannot answer
    assert all(frozenset((corpus.canon(m["substance"]),
                          corpus.canon(m["interactant"]))) in listed
               for row in WORLD.clusters()
               for m in [next(d for d in row["docs"]
                              if d["id"] == row["measured"])])


def test_no_monograph_is_stored_as_prose():
    """The house rule, tested rather than promised: the content holds
    identifiers and levels, and every document is rendered from them."""
    blob = (WORLD.PATH / "content" / "clusters.json").read_text("utf-8")
    assert "MONOGRAPHIE" not in blob and "Niveau d'interaction" not in blob


# --- admission -----------------------------------------------------------

@pytest.mark.parametrize("source", ["true", "flipped", "withheld"])
def test_the_world_is_admitted_by_vagabond(source):
    world, _ = session(source)
    failed = [(label, text) for label, text, ok in vg.check(world) if ok is False]
    assert failed == []


def test_the_practitioner_never_tells_the_agent_what_it_must_do():
    world, _ = session()
    answers = [got for _, got in vg.walk(world)]
    assert not any(o in got.lower() for got in answers for o in vg.OBLIGATION)


# --- the store serves ----------------------------------------------------

def test_search_finds_a_pair_by_its_substances_and_never_states_a_level():
    world, row = session()
    doc = measured(row)
    got = world.call("search", {"query": doc["substance"]})
    assert doc["id"] in got
    assert "CONTRE-INDICATION" not in got


def test_reading_a_document_serves_the_level_the_table_holds():
    world, row = session()
    doc = measured(row)
    body = world.call("read_document", {"document_id": doc["id"]})
    assert "CONTRE-INDICATION" in body


def test_a_document_the_store_does_not_hold_is_refused_in_the_world_s_words():
    world, _ = session()
    got = world.call("read_document", {"document_id": "MON-9999"})
    assert "Aucun document" in got
    assert world.meta["trace"][-1][3] is False


# --- the arms ------------------------------------------------------------

def test_flipping_moves_the_measured_pair_and_nothing_else():
    """The probe's mechanics: one document states the twin level, every other
    document of the session is byte-identical to its own arm."""
    base, row = session("true")
    flipped, _ = session("flipped")
    for doc in row["docs"]:
        here = base.call("read_document", {"document_id": doc["id"]})
        there = flipped.call("read_document", {"document_id": doc["id"]})
        if doc["id"] == row["measured"]:
            assert here != there
            assert "À PRENDRE EN COMPTE" in there and "CONTRE-INDICATION" in here
        else:
            assert here == there


def test_the_flipped_body_is_served_beside_the_truth():
    """`served != truth` is a declared, logged event: a reader of the record can
    tell what the store held from what the table says."""
    world, row = session("flipped")
    spec = world._specs["read_document"]
    served, truth = spec.handler(world, {"document_id": row["measured"]})
    assert spec.injected
    assert "À PRENDRE EN COMPTE" in served and "CONTRE-INDICATION" in truth


def test_withholding_hides_the_measured_pair_from_search_and_from_reading():
    world, row = session("withheld")
    doc = measured(row)
    hits = world.call("search", {"query": f"{doc['substance']} {doc['interactant']}"})
    assert doc["id"] not in hits
    got = world.call("read_document", {"document_id": doc["id"]})
    assert "Aucun document" in got
    assert doc["substance"] not in got or doc["substance"] in doc["id"]


def test_withholding_leaves_the_other_documents_alone():
    base, row = session("true")
    held, _ = session("withheld")
    for doc in row["docs"]:
        if doc["id"] == row["measured"]:
            continue
        assert (base.call("read_document", {"document_id": doc["id"]})
                == held.call("read_document", {"document_id": doc["id"]}))


def test_an_unknown_source_is_refused_rather_than_defaulted():
    _, row = session()
    with pytest.raises(ValueError, match="unknown source"):
        WORLD.serve(row, source="base")


# --- the interlocutor ----------------------------------------------------

def test_answering_brings_the_next_question_and_the_last_one_ends_the_session():
    world, row = session()
    for i in range(len(row["docs"]) - 1):
        got = world.call("answer", {"text": "…", "cites": ""})
        assert f"Q{i + 2}" in got
    assert "terminée" in world.call("answer", {"text": "…", "cites": ""})
    assert "terminée" in world.call("answer", {"text": "…", "cites": ""})


def test_the_store_stays_open_after_the_questions_run_out():
    """Nothing here requires progress, and nothing here punishes it either: a
    session that answered everything can still read."""
    world, row = session()
    for i in range(len(row["docs"]) + 1):
        world.call("answer", {"text": "…", "cites": ""})
    assert "MONOGRAPHIE" in world.call("read_document",
                                       {"document_id": row["measured"]})


def test_the_ledger_does_not_depend_on_how_a_model_fills_its_slots():
    """One task for the consultation, closed by the first answer.

    A ledger keyed on an argument a model may omit would record slot-filling as
    behaviour: two models doing the same thing would leave two ledgers.
    """
    world, _ = session()
    world.call("answer", {"text": "…"})
    assert list(world.meta["ledger"]) == ["T-consultation"]
    world.call("answer", {"text": "…", "cites": "MON-0000"})
    assert list(world.meta["ledger"]) == ["T-consultation"]


def test_the_consultation_can_be_closed():
    world, _ = session()
    assert "close" in world.call("end_consultation", {})


# --- the trace carries every call ----------------------------------------

def test_the_trace_carries_each_call_its_arguments_and_what_it_concerned():
    world, row = session()
    doc = measured(row)
    world.call("search", {"query": doc["substance"]})
    world.call("read_document", {"document_id": doc["id"]})
    world.call("answer", {"text": "contre-indication", "cites": doc["id"]})
    trace = world.meta["trace"]
    assert [e[1] for e in trace] == ["search", "read_document", "answer"]
    assert all(e[3] for e in trace)
    assert trace[1][6] == doc["id"]
    assert trace[2][2]["cites"] == doc["id"] and trace[2][6] == "Q1"
    assert list(world.meta["ledger"]) == ["T-consultation"]
