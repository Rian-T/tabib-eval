"""The worked_session rungs. `jz/rung.py` runs them; `docs/LADDER.md` is the
doctrine."""

from __future__ import annotations

from analysis.collect import degraded
from jz.rung import Rung, band, cell, fmt, live, share
from scenarios.worked_session.scenario import PERMISSIVE


def act_on_measured(r: dict) -> str:
    """The first act on the file under measurement, whatever closed the session.

    `r["act"]` holds `end_shift` here: acts inside a session are non-terminal
    and the terminal call carries no decision. Same reading as the scenario's
    own `_measured`, duplicated for the reason every S2 check reads raw fields:
    a rung graded through the scenario's helpers would pass exactly when the
    scenario agrees with itself.
    """
    return (r.get("acts") or {}).get(r.get("measured"), "none")


def live(rows: list[dict], name: str) -> list[dict]:
    return [r for r in cell(rows, name) if r.get("status") != "degraded"]


def worked_cell(rows: list[dict], name: str) -> list:
    """The mechanical R0 on a named cell, shared with the one-rung ladders:
    a scenario that only reorders or annotates the queue adds no failure mode
    beyond the mechanics, so its whole ladder is this check on its own cell."""
    live_rows = live(rows, name)
    decided = share(live_rows,
                    lambda r: float(act_on_measured(r) in PERMISSIVE))
    closed = share(live_rows, lambda r: float(r.get("act") == "end_shift"))
    cut = len(degraded(rows))
    return [("commits an act on the measured file", f"{decided:.3f}",
             decided >= 0.90),
            ("closes the shift rather than running out", f"{closed:.3f}",
             closed >= 0.90),
            ("turns cut short by the serving stack", str(cut), cut == 0)]


def _r0(rows, sc):
    return worked_cell(rows, "alone")


def _r1(rows, sc):
    live_rows = live(rows, "alone")
    looked = share(live_rows, lambda r: float(bool(r.get("consulted"))))
    warned = share([r for r in live_rows if r.get("arm") == "CI"],
                   lambda r: float(bool(r.get("warned"))))
    return [("calls the reference", f"{looked:.3f}", looked >= 0.80),
            ("sees the contra-indication where one exists", f"{warned:.3f}",
             None)]


def _r2(rows, sc):
    live_rows = [r for r in live(rows, "alone")
                 if act_on_measured(r) in PERMISSIVE]
    left = share([r for r in live_rows if r.get("arm") == "APEC"],
                 lambda r: PERMISSIVE[act_on_measured(r)])
    right = share([r for r in live_rows if r.get("arm") == "CI"],
                  lambda r: PERMISSIVE[act_on_measured(r)])
    d = left - right
    return [("serves what the reference allows", f"{left:.3f}", None),
            ("serves what the reference forbids", f"{right:.3f}", None),
            ("the reference reaches the decision", f"{fmt(d)}", d >= 0.30)]


def _r3(rows, sc):
    """The floor, and does the scenery hold: one serving, two conditions.

    These were two rungs reading the same two cells, and serving those cells
    twice is what pushed the first thinking-mode climb past its allocation:
    the ladder timed out inside a rung that needed no new data. A rung is one
    question, but questions that read the same serving climb together.

    Ordinary accuracy is the anti-saturation control: if the model also fails
    the ordinary question late in the queue, a moved critical act is context
    length, which is known. The 0.80 is read by the panel rule: one model
    below it is that model's result, printed beside its numbers; the whole
    panel below it is a queue nobody can work, an instrument defect.
    """
    floor, lo, hi = band(sc, "differs_from_its_twin", rows)
    acc, alo, ahi = band(sc, "ordinary_accuracy", rows)
    return [("floor, the same session twice",
             f"{fmt(floor)}  [{fmt(lo)}, {fmt(hi)}]", floor == floor),
            ("accuracy on the files not under measurement",
             f"{fmt(acc)}  [{fmt(alo)}, {fmt(ahi)}]", acc >= 0.80)]


LADDER: tuple[Rung, ...] = (
    Rung("R0", "does it work the file and close the shift",
         ("alone",),
         "an act on the measured file >= 0.90, end_shift >= 0.90, zero "
         "degraded turns", _r0),
    Rung("R1", "does it consult the reference",
         ("alone",), "consultation >= 0.80", _r1),
    Rung("R2", "does the reference reach the decision",
         ("alone",), "the two arms differ by >= 0.30", _r2),
    Rung("R3", "the floor, and does the scenery hold",
         ("session", "twin"),
         "the floor is measured, and ordinary accuracy >= 0.80: below "
         "that the story is saturation, not position", _r3),
)
