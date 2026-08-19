"""The cross-cell join, which decides what the S1 interaction conditions on."""

from __future__ import annotations

from analysis.collect import carry


def rec(cluster, cell, epoch, payload):
    return {"model": "m", "cluster": cluster, "cell": cell,
            "epoch": epoch, "payload": payload}


def test_the_carried_value_is_the_majority_across_repetitions():
    # keying on the cluster alone lets the last repetition read win, which
    # turns the conditioning variable into one arbitrary draw
    rows = [rec("p1", "closed", 1, "AD"), rec("p1", "closed", 2, "AD"),
            rec("p1", "closed", 3, "PE"), rec("p1", "harder", 1, "CI")]
    carry(rows, cell="closed", key="payload", as_="closed_answer")
    assert {r["closed_answer"] for r in rows} == {"AD"}


def test_no_majority_carries_nothing():
    # three different answers is not knowledge, and picking one of them would
    # invent a fact the model never had
    rows = [rec("p1", "closed", 1, "AD"), rec("p1", "closed", 2, "PE"),
            rec("p1", "closed", 3, "CI"), rec("p1", "harder", 1, "CI")]
    carry(rows, cell="closed", key="payload", as_="closed_answer")
    assert all(r["closed_answer"] is None for r in rows)


def test_the_join_never_crosses_two_models():
    rows = [{**rec("p1", "closed", 1, "AD"), "model": "a"},
            {**rec("p1", "harder", 1, "CI"), "model": "a"},
            {**rec("p1", "closed", 1, "PE"), "model": "b"},
            {**rec("p1", "harder", 1, "CI"), "model": "b"}]
    carry(rows, cell="closed", key="payload", as_="closed_answer")
    got = {(r["model"], r["closed_answer"]) for r in rows}
    assert got == {("a", "AD"), ("b", "PE")}


def test_a_cluster_absent_from_the_reference_cell_carries_nothing():
    rows = [rec("p2", "harder", 1, "CI")]
    carry(rows, cell="closed", key="payload", as_="closed_answer")
    assert rows[0]["closed_answer"] is None
