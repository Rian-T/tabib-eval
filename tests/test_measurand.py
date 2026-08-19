from __future__ import annotations

import pytest

from tabib.measurand import Measurand, difference, dropped, gap, interval, values

FOLLOWS = Measurand("follows", lambda r: r["y"], ("v1", "v0"))


def rec(cluster, cell, y):
    return {"cluster": cluster, "cell": cell, "y": y}


def test_a_policy_blind_to_the_manipulation_scores_exactly_zero():
    # the structural guarantee: same output on both served versions, whatever
    # that output is, sums to zero on every cluster
    rows = [rec(f"p{i}", cell, 1.0) for i in range(5) for cell in ("v0", "v1")]
    assert [v for _, v in values(FOLLOWS, rows)] == [0.0] * 5


def test_a_contrast_is_paired_inside_the_cluster():
    rows = [rec("p1", "v1", 1.0), rec("p1", "v0", 0.0),
            rec("p2", "v1", 0.0), rec("p2", "v0", 0.0)]
    assert values(FOLLOWS, rows) == [("p1", 1.0), ("p2", 0.0)]


def test_repetitions_are_averaged_not_counted_as_observations():
    # one cluster with three reps on each side stays one difference
    rows = ([rec("p1", "v1", y) for y in (1.0, 1.0, 0.0)] +
            [rec("p1", "v0", 0.0) for _ in range(3)])
    got = values(FOLLOWS, rows)
    assert len(got) == 1
    assert got[0][1] == pytest.approx(2 / 3)


def test_a_cluster_seen_on_one_side_only_is_dropped_and_counted():
    rows = [rec("p1", "v1", 1.0), rec("p1", "v0", 0.0), rec("p2", "v1", 1.0)]
    assert values(FOLLOWS, rows) == [("p1", 1.0)]
    assert dropped(FOLLOWS, rows) == 1


def test_a_descriptive_is_a_rate_and_never_a_difference():
    m = Measurand("rate", lambda r: r["y"], ("v1",))
    rows = [rec("p1", "v1", 1.0), rec("p2", "v1", 0.0), rec("p3", "v0", 1.0)]
    assert values(m, rows) == [("p1", 1.0), ("p2", 0.0)]
    assert dropped(m, rows) == 0


def test_naming_two_cells_is_what_makes_a_contrast():
    assert Measurand("c", lambda r: 1.0, ("a", "b")).contrast
    assert not Measurand("d", lambda r: 1.0, ("a",)).contrast
    with pytest.raises(ValueError):
        Measurand("bad", lambda r: 1.0, ("a", "b", "c"))
    with pytest.raises(ValueError):
        Measurand("bad", lambda r: 1.0, ("a", "b"), oracle_moves="sideways")


def rep(cluster, cell, epoch, y):
    return {"cluster": cluster, "cell": cell, "epoch": epoch, "y": y}


def test_a_lost_repetition_does_not_break_the_exact_zero():
    # a blind policy answers identically in both cells; if one repetition is
    # missing on one side, averaging each cell first invents an effect
    rows = [rep(f"p{c}", cell, e, 1.0 if e == 1 else 0.0)
            for c in range(3) for cell in ("v0", "v1") for e in (1, 2, 3)]
    rows.remove(rep("p0", "v0", 1, 1.0))
    assert [v for _, v in values(FOLLOWS, rows)] == [0.0, 0.0, 0.0]
    assert dropped(FOLLOWS, rows) == 1


def test_repetitions_are_matched_before_being_averaged():
    rows = [rep("p1", "v1", 1, 1.0), rep("p1", "v0", 1, 0.0),
            rep("p1", "v1", 2, 0.0), rep("p1", "v0", 2, 0.0)]
    assert values(FOLLOWS, rows) == [("p1", 0.5)]


def test_a_selector_keeps_the_records_it_names_and_drops_the_rest():
    seen = Measurand("follows_when_seen", lambda r: r["y"], ("v1", "v0"),
                     where=lambda r: r["seen"])
    rows = [{**rec("p1", "v1", 1.0), "seen": True},
            {**rec("p1", "v0", 0.0), "seen": True},
            {**rec("p2", "v1", 1.0), "seen": False},
            {**rec("p2", "v0", 0.0), "seen": False}]
    assert values(seen, rows) == [("p1", 1.0)]


def test_the_interval_is_the_resampling_this_repo_publishes():
    # the seed and the number of resamples are declared constants, so the bounds
    # are deterministic: changing how they are computed changes every published
    # band, and that has to fail here rather than in a figure
    v = [("c0", 0.0), ("c1", 0.5), ("c2", 1.0), ("c3", 0.25), ("c4", 0.75)]
    assert interval(v) == (0.5, 0.2, 0.8)
    assert interval(v) == interval(v, alpha=0.05)
    assert interval(v, alpha=0.5) == (0.5, 0.4, 0.6)


def test_resampling_a_constant_returns_the_constant_with_no_width():
    v = [(f"c{i}", 0.4) for i in range(5)]
    assert interval(v) == (0.4, 0.4, 0.4)


def test_asking_for_more_confidence_gives_a_wider_band():
    v = [("c0", 0.0), ("c1", 1.0), ("c2", 0.5), ("c3", 0.9), ("c4", 0.1)]
    _, lo95, hi95 = interval(v, alpha=0.05)
    _, lo50, hi50 = interval(v, alpha=0.5)
    assert lo95 < lo50 <= hi50 < hi95


def test_a_contrast_with_no_pairs_has_no_interval_rather_than_a_zero():
    assert all(x != x for x in interval([]))


A = Measurand("a", lambda r: r["y"], ("v1", "v0"))
B = Measurand("b", lambda r: r["y"], ("v2", "v0"))


def test_two_movements_are_differenced_inside_the_cluster():
    # the claim of an experiment of this shape is that one movement is bigger
    # than another, so the comparison is a number with its own interval
    rows = [rec("p1", "v1", 1.0), rec("p1", "v0", 0.0), rec("p1", "v2", 0.5),
            rec("p2", "v1", 1.0), rec("p2", "v0", 1.0), rec("p2", "v2", 0.0)]
    assert difference(A, B, rows) == ("paired", [("p1", 0.5), ("p2", 1.0)], [])


def test_a_cluster_missing_from_either_movement_is_not_compared():
    rows = [rec("p1", "v1", 1.0), rec("p1", "v0", 0.0), rec("p1", "v2", 0.5),
            rec("p2", "v1", 1.0), rec("p2", "v0", 0.0)]
    assert difference(A, B, rows) == ("paired", [("p1", 0.5)], [])


def test_two_movements_a_blind_policy_makes_both_zero_compare_to_zero():
    rows = [rec(f"p{i}", cell, 1.0)
            for i in range(4) for cell in ("v0", "v1", "v2")]
    kind, paired, _ = difference(A, B, rows)
    assert kind == "paired" and [v for _, v in paired] == [0.0] * 4


def test_two_subgroups_that_partition_the_units_are_not_paired():
    # "pairs it knew" and "pairs it did not" never share a cluster, so pairing
    # them yields nothing at all: the comparison is between different units
    knew = Measurand("knew", lambda r: r["y"], ("v1", "v0"),
                     where=lambda r: r["cluster"] in ("p1", "p2"))
    rest = Measurand("rest", lambda r: r["y"], ("v1", "v0"),
                     where=lambda r: r["cluster"] not in ("p1", "p2"))
    rows = [rec(c, cell, 1.0 if cell == "v1" and c in ("p1", "p2") else 0.0)
            for c in ("p1", "p2", "p3", "p4") for cell in ("v0", "v1")]
    kind, left, right = difference(knew, rest, rows)
    assert kind == "disjoint"
    assert [c for c, _ in left] == ["p1", "p2"]
    assert [c for c, _ in right] == ["p3", "p4"]
    point, lo, hi = gap(left, right)
    assert point == 1.0 and lo <= point <= hi


def test_a_gap_with_an_empty_side_has_no_number():
    assert all(x != x for x in gap([("p1", 1.0)], []))
