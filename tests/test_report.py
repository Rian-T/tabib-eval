"""The reporting half of the rule: a number, its interval, and what would make
it uninterpretable.

`gate.py` says a number is not an artefact; nothing here can say that. What
these tests hold is the other half, that the table and the figure cannot
quietly turn no data into a finding, or one model's records into another
model's counterparts.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from analysis.report import main, measure, plane, svg, table
from tabib.measurand import Measurand

FOLLOWS = Measurand("follows", lambda r: r["y"], ("harder", "softer"))
RATE = Measurand("rate", lambda r: r["y"], ("softer",))


def sc(*measurands):
    return SimpleNamespace(measurands=measurands)


def rec(model, cluster, cell, y):
    return {"model": model, "cluster": cluster, "cell": cell, "y": y}


def test_one_line_per_measurand_and_model_in_a_stable_order():
    rows = [rec(m, "p1", cell, 1.0)
            for m in ("b/two", "a/one") for cell in ("harder", "softer")]
    got = measure(sc(FOLLOWS, RATE), rows)
    assert [(x["measurand"], x["model"]) for x in got] == [
        ("follows", "a/one"), ("follows", "b/two"),
        ("rate", "a/one"), ("rate", "b/two")]


def test_a_blind_policy_reports_zero_with_an_interval_that_contains_it():
    rows = [rec("m", f"p{i}", cell, 1.0)
            for i in range(6) for cell in ("harder", "softer")]
    line, = measure(sc(FOLLOWS), rows)
    assert (line["point"], line["lo"], line["hi"]) == (0.0, 0.0, 0.0)
    assert line["clusters"] == 6


def test_a_rate_carries_an_interval_like_everything_else():
    # it used to be reported bare. Both axes of the S2 figure are rates, so the
    # dots were drawn with no width at all, and the ratio between two of them
    # was quoted to two digits. Resampling is over clusters whether the value
    # is a rate or a difference, so there was never a reason to withhold it.
    rows = [rec("m", "p1", "softer", 1.0), rec("m", "p2", "softer", 0.0)]
    line, = measure(sc(RATE), rows)
    assert line["point"] == 0.5
    assert not line["contrast"]
    assert line["lo"] <= line["point"] <= line["hi"]


def test_pair_loss_is_counted_inside_one_model_and_never_across_two():
    # each model saw both cells of its own pair: pooling the models first would
    # let one model's record stand in as the other's counterpart
    paired = [rec("a", "p1", "harder", 1.0), rec("a", "p1", "softer", 0.0),
              rec("b", "p1", "harder", 1.0), rec("b", "p1", "softer", 0.0)]
    assert [x["dropped"] for x in measure(sc(FOLLOWS), paired)] == [0, 0]

    halves = [rec("a", "p1", "harder", 1.0), rec("b", "p1", "softer", 0.0)]
    got = measure(sc(FOLLOWS), halves)
    assert [x["dropped"] for x in got] == [1, 1]
    assert all(x["clusters"] == 0 for x in got)


def test_a_channel_pinned_against_the_floor_on_every_model_is_flagged():
    rows = [rec(m, f"p{i}", cell, 0.0)
            for m in ("a", "b") for i in range(4) for cell in ("harder", "softer")]
    assert all(x["pinned"] for x in measure(sc(FOLLOWS), rows))


def test_a_cell_that_moves_is_not_flagged_as_saturated():
    rows = [rec("a", f"p{i}", cell, float(i % 2))
            for i in range(4) for cell in ("harder", "softer")]
    line, = measure(sc(FOLLOWS), rows)
    assert not line["pinned"]


def test_a_measurand_that_never_ran_is_not_called_saturated():
    # a cell declared and never executed is the defect this instrument already
    # shipped once; "saturated" is the one thing a reader must not conclude
    # from an absence of records
    never = Measurand("never_ran", lambda r: r["y"], ("absent", "gone"))
    line, = measure(sc(never), [rec("a", "p1", "softer", 1.0)])
    assert line["clusters"] == 0
    assert line["point"] != line["point"]
    assert not line["pinned"]


def test_the_table_prints_the_spread_between_the_models(capsys):
    # neither model sits at zero, so the spread cannot come out right by
    # accident the way it does when the smaller of the two is 0
    rows = ([rec("a", f"p{i}", "harder", 1.0) for i in range(4)] +
            [rec("a", f"p{i}", "softer", 0.0) for i in range(4)] +
            [rec("b", f"p{i}", "harder", 1.0 if i < 2 else 0.0) for i in range(4)] +
            [rec("b", f"p{i}", "softer", 0.0) for i in range(4)])
    table(measure(sc(FOLLOWS), rows))
    out = capsys.readouterr().out
    assert "spread across models +0.500" in out
    assert "4 clusters" in out


def test_the_figure_marks_zero_and_carries_one_point_per_model(tmp_path):
    rows = [rec(m, f"p{i}", cell, 1.0 if cell == "harder" else 0.0)
            for m in ("vendor/a", "vendor/b") for i in range(3)
            for cell in ("harder", "softer")]
    out = tmp_path / "f.svg"
    svg(measure(sc(FOLLOWS), rows), out)
    text = out.read_text(encoding="utf-8")
    assert text.count("<circle") == 2
    assert ">0</text>" in text
    assert ">a</text>" in text and ">b</text>" in text


def test_no_figure_is_written_when_no_contrast_produced_a_number(tmp_path, capsys):
    out = tmp_path / "f.svg"
    svg(measure(sc(RATE), [rec("a", "p1", "softer", 1.0)]), out)
    assert not out.exists()
    assert "no figure" in capsys.readouterr().out


def test_the_saturation_band_is_closed_at_its_edge():
    edge = [rec("a", f"p{i}", cell, 0.05)
            for i in range(4) for cell in ("harder", "softer")]
    assert all(x["pinned"] for x in measure(sc(FOLLOWS), edge))
    inside = [rec("a", f"p{i}", cell, 0.06)
              for i in range(4) for cell in ("harder", "softer")]
    assert not any(x["pinned"] for x in measure(sc(FOLLOWS), inside))

    # and the same edge at the ceiling, which is a separate comparison
    ceiling = [rec("a", f"p{i}", cell, 0.95)
               for i in range(4) for cell in ("harder", "softer")]
    assert all(x["pinned"] for x in measure(sc(FOLLOWS), ceiling))
    below = [rec("a", f"p{i}", cell, 0.94)
             for i in range(4) for cell in ("harder", "softer")]
    assert not any(x["pinned"] for x in measure(sc(FOLLOWS), below))


def test_the_figure_puts_zero_and_the_span_where_the_axis_says(tmp_path):
    # the figure is the claim, so a point drawn at the wrong x is a wrong
    # result that reads as a clean one
    rows = ([rec("m", f"p{i}", "harder", 1.0) for i in range(3)] +
            [rec("m", f"p{i}", "softer", 0.0) for i in range(3)])
    out = tmp_path / "f.svg"
    svg(measure(sc(FOLLOWS), rows), out)
    text = out.read_text(encoding="utf-8")
    # the contrast is +1.0, so the axis runs -1 to +1 across the 430px between
    # x=250 and x=680: zero falls at the middle, the point at the right edge
    assert 'x1="465.0"' in text and 'x2="465.0"' in text
    assert 'cx="680.0"' in text


def test_a_report_names_a_scenario_and_a_directory():
    assert main([]) == 2
    assert main(["source_fidelity"]) == 2


def test_the_plane_puts_a_model_on_the_diagonal_when_its_two_movements_match(tmp_path):
    # the diagonal is the null: equal movements means the distinction the
    # experiment claims to measure did not happen, and that has to be visible
    # as a position rather than inferred from two numbers
    claims = [{"claim": "a - b", "y": "a", "x": "b", "model": "v/same",
               "point": 0.0, "lo": 0.0, "hi": 0.0, "clusters": 5,
               "vx": 0.4, "vy": 0.4},
              {"claim": "a - b", "y": "a", "x": "b", "model": "v/above",
               "point": 0.4, "lo": 0.3, "hi": 0.5, "clusters": 5,
               "vx": 0.0, "vy": 0.4}]
    out = tmp_path / "p.svg"
    plane(claims, out)
    text = out.read_text(encoding="utf-8")
    circles = re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)"', text)
    assert len(circles) == 2
    (sx, sy), (ax, ay) = ((float(a), float(b)) for a, b in circles)
    # the panel is square, so a point sits on the diagonal exactly when its
    # distance from the left edge equals its height above the base
    on_line = lambda x, y: (x - 54) - (44 + 300 - y)
    assert abs(on_line(sx, sy)) < 0.5
    # the model that moved only on the y axis is above the line, not on it
    assert on_line(ax, ay) < -0.5


def test_the_plane_writes_nothing_when_no_comparison_produced_a_number(tmp_path):
    out = tmp_path / "p.svg"
    plane([], out)
    assert not out.exists()


def test_a_model_with_nothing_to_compare_is_named_not_dropped(tmp_path):
    # a channel defined by what a model knew: having no comparison is a fact
    # about the model, and the one place it must not go is off the figure
    claims = [{"claim": "a - b", "y": "a", "x": "b", "model": "v/placed",
               "point": 0.2, "lo": 0.1, "hi": 0.3, "clusters": 40,
               "vx": 0.2, "vy": 0.4},
              {"claim": "a - b", "y": "a", "x": "b", "model": "v/empty",
               "point": float("nan"), "lo": float("nan"), "hi": float("nan"),
               "clusters": 0, "vx": 0.2, "vy": float("nan")}]
    out = tmp_path / "p.svg"
    plane(claims, out)
    text = out.read_text(encoding="utf-8")
    assert text.count("<circle") == 1
    assert "empty" in text and "rien à comparer" in text
    # deux axes et rien d'autre : tous les points ont le même rayon
    assert set(re.findall(r'<circle [^>]*r="([\d.]+)"', text)) == {"4"}
