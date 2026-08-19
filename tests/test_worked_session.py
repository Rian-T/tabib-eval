"""What the queue guarantees, on synthetic records.

The real corpus of reports is not committed here, so the records are built by
this file; the ANSM table is the real one, because the claim under test is
about which pairs the reference holds.
"""

from __future__ import annotations

import dataclasses

import pytest

from scenarios.ansm import corpus
from scenarios.worked_session import build_queue as bq

SEED = 4321


def fake_records(n: int = 30) -> list[dict]:
    """Reports long enough to be admitted, each naming one age once."""
    return [{"id": f"SPE-{i:05d}", "specialty": "SPE", "age": 20 + i,
             "text": f"COMPTE-RENDU\n\nPatient de {20 + i} ans.\n" + "Suivi. " * 200}
            for i in range(n)]


def queue(**kw):
    return bq.build(fake_records(), seed=SEED, **kw)


def test_the_ten_files_have_the_same_shape():
    files = queue()
    assert len(files) == 10
    fields = {f.name for f in dataclasses.fields(bq.File)}
    for f in files:
        assert set(dataclasses.asdict(f)) == fields
        assert all(dataclasses.asdict(f)[k] for k in fields)


def test_every_ordinary_task_has_a_computable_answer():
    # the answer is the age the record states, and it states exactly one
    for f in queue():
        assert set(bq.AGE.findall(f.record)) == {f.answer}


def test_the_same_seed_builds_the_same_queue():
    assert queue() == queue()
    assert queue() != bq.build(fake_records(), seed=SEED + 1)


def test_one_file_is_contra_indicated_and_the_nine_others_are_not():
    files = queue(position=6)
    levels = {e.pair_id: e.level for e in corpus.load()}
    for rank, f in enumerate(files, start=1):
        expected = bq.CRITICAL if rank == 6 else bq.ORDINARY
        assert levels[f.pair_id] == expected == f.level, rank
        assert f.expected_act == bq.ACT[expected]


def test_no_pair_is_prescribed_twice():
    assert len({f.pair_id for f in queue()}) == 10


def test_a_queue_shorter_than_asked_fails_loudly():
    with pytest.raises(ValueError):
        bq.build(fake_records(4), seed=SEED)


def test_no_file_names_the_substance_it_prescribes():
    entries = {e.pair_id: e for e in corpus.load()}
    for f in queue():
        record = f.record[:f.record.index(bq.MARKER)]
        assert not bq.mentions(record, entries[f.pair_id]), f.file_id


def test_the_leak_check_ignores_case_and_accents():
    entry = next(e for e in corpus.load() if e.substance == "CICLOSPORINE")
    assert bq.mentions("Traitement par ciclosporine depuis 2020.", entry)
    assert not bq.mentions("Traitement par ciclosporines.", entry)


def test_a_queue_with_nowhere_left_to_put_a_pair_fails_loudly():
    # every record names the substance the critical file must prescribe, so no
    # pairing is clean and the shortfall has to be raised rather than served
    entry = bq.pairs(bq.CRITICAL, n=1, seed=SEED)[0]
    rows = fake_records()
    for r in rows:
        r["text"] += f"\nTraitement en cours : {entry.substance}.\n"
    with pytest.raises(ValueError):
        bq.build(rows, seed=SEED)


def test_the_materialised_queue_matches_what_the_pipeline_builds():
    # the scenario reads the JSON, so the JSON is what has to be right
    loaded = bq.load()
    assert {q["arm"] for q in loaded} == {bq.CRITICAL, bq.ORDINARY}
    for q in loaded:
        levels = [f["level"] for f in q["files"]]
        assert len(levels) == 10
        assert levels[q["position"] - 1] == q["arm"]
        assert set(levels) <= {bq.ORDINARY, q["arm"]}
        for f in q["files"]:
            # a set: a report may state the same age twice, and one number said
            # twice is still one computable answer
            assert set(bq.AGE.findall(f["record"])) == {f["answer"]}


def test_the_measured_pair_is_distinct_across_clusters():
    # drawn per cluster instead of dealt, sixty clusters collided down to 47
    # distinct pairs out of a pool of 97: the birthday problem, not a sample
    loaded = bq.load()
    for arm in (bq.CRITICAL, bq.ORDINARY):
        measured = [q["files"][q["position"] - 1]["pair_id"]
                    for q in loaded if q["arm"] == arm]
        assert len(set(measured)) == len(measured), arm


def test_the_measured_pair_is_not_also_an_ordinary_file_of_its_queue():
    for q in bq.load():
        assert len({f["pair_id"] for f in q["files"]}) == len(q["files"]), q["id"]


def test_a_record_stating_two_ages_is_not_admissible():
    ambiguous = {"id": "SPE-99999", "specialty": "SPE", "age": 70,
                 "text": "Patient de 70 ans, opéré il y a 3 ans. " + "Suivi. " * 200}
    assert bq.admissible([ambiguous]) == []
