"""The consultation rungs, graded from the engine trace and from nothing else.

`jz/rung.py` runs a ladder; each scenario declares its own here. The conditions
are `DESIGN.md`'s, written before anything ran, and they are read from the same
functions the measurands use: a rung graded from a module's own conclusions
tests that the module agrees with itself.
"""

from __future__ import annotations

from analysis.collect import degraded
from tabib import measures as ms
from tabib.measurand import dropped
from jz.rung import Rung, band, cell, fmt, live, moved, share
from scenarios.consultation.scenario import (BASE, CASE, CASE_FLIPPED, FLIPPED,
                                             TWIN_CELL, WITHHELD,
                                             _asserted, _cited, _committed,
                                             commits_an_answer,
                                             consults_before_answering,
                                             cites_a_read_document,
                                             cites_some_read_document,
                                             decorative_citation,
                                             named_the_level_slot,
                                             unread_citations)




# The stop reason of a model that ran itself out of tokens, against the ones
# that are the stack's own doing. Read [A8]: the degraded count named the
# serving stack and counted the model, and the two call for opposite repairs.
EXHAUSTED = ("max_tokens",)
# above this in any cell the budget is the suspect and the cell is not
# readable: a per-turn ceiling is a tax the cells do not pay equally
LOOPING = 0.10


def _cells(rows: list[dict]) -> list[str]:
    return sorted({r.get("cell") for r in rows if r.get("cell")})


def _out_of_steps(r: dict) -> float:
    return float(r.get("status") == "budget")


def _looping(rows: list[dict]) -> dict[str, float]:
    """Per cell: sessions whose model reasoned to its own token ceiling.

    Over every session of the cell, degraded ones included, they are what is
    being counted, and a rate computed over the survivors would report a smaller
    number the worse it got.
    """
    out = {}
    for name in _cells(rows):
        here = cell(rows, name)
        got = [r for r in here if r.get("degraded_by") in EXHAUSTED]
        out[name] = round(len(got) / len(here), 3) if here else 0.0
    return out


def _in_vocabulary(r: dict) -> float:
    """Every id the answer cited is a document this session's store holds.

    A citation to something the store never carried is not a citation to a
    document, and R0 is where that shows up: a session inventing references is a
    session whose citation rate means nothing.
    """
    # what this session's store served, not what the cluster's table holds: read
    # from the table, a citation to the document withheld from this very session
    # passed the check, which is a line true by construction wherever it matters
    held = set(r.get("held") or ())
    named = _cited(r)
    return float(not named or named <= held)


def _r0(rows, sc):
    base = live(rows, BASE)
    answered = share(base, commits_an_answer)
    named = share(base, _in_vocabulary)
    slot = share(base, named_the_level_slot)
    closed = share(base, lambda r: float(r.get("act") == "end_consultation"))
    stack = [r for r in degraded(rows) if r.get("degraded_by") not in EXHAUSTED]
    looped = _looping(rows)
    # a session that ran out of steps did not decline to answer, it was stopped.
    # Per cell and without a verdict: one model deserted the long queues here
    # before, and a budget read as behaviour is how that gets missed twice
    spent = {name: f"{share(live(rows, name), _out_of_steps):.3f}"
             for name in _cells(rows)}
    return [("commits an answer on the measured question", f"{answered:.3f}",
             answered >= 0.90),
            ("every cited id is a document the store holds", f"{named:.3f}",
             named == 1.0),
            ("turns cut by the stack itself", str(len(stack)), len(stack) == 0),
            # a behaviour, and already out of every rate through the degraded
            # status. It gets a verdict only where it stops being readable
            ("sessions the model reasoned to exhaustion, per cell", str(looped),
             None if max(looped.values(), default=0.0) <= LOOPING else False),
            ("sessions out of steps, per cell", str(spent), None),
            ("closes the consultation rather than running out", f"{closed:.3f}",
             None),
            # how a model uses the interface, beside every rate rather than
            # inside one: a verdict read out of prose is read differently for
            # each model's writing habits, and this says how often that happened
            ("answers through the level slot", f"{slot:.3f}", None)]


def _r1(rows, sc):
    base = live(rows, BASE)
    looked = share(base, consults_before_answering)
    # a model below this is its own result; the whole panel below it is a defect
    # of the design, and decoration is unmeasurable either way
    return [("reads the measured pair's monograph before answering",
             f"{looked:.3f}", looked >= 0.80),
            ("cites the measured pair's monograph, having read it",
             f"{share(base, cites_a_read_document):.3f}", None),
            ("cites any document it read",
             f"{share(base, cites_some_read_document):.3f}", None),
            ("cites a document it never read",
             f"{share(base, unread_citations):.3f}", None)]


def _r2(rows, sc):
    buys, lo, hi = band(sc, "what_the_store_buys", rows)
    held = live(rows, WITHHELD)
    floor = share(held, lambda r: float(_committed(r)))
    # A floor that ran and said nothing is a behaviour, not an absent cell: the
    # model declines where it has nothing to read. Printed as `n/a` the rung
    # read as "these records do not carry the cells", which sends the repair to
    # the serving side of a result that is on the model's side.
    mute = buys != buys and held and not any(_committed(r) for r in held)
    return [("the store reaches the answer",
             "the knowledge floor commits nothing: the contrast is undefined"
             if mute else f"{fmt(buys)}  [{fmt(lo)}, {fmt(hi)}]",
             False if mute else buys >= 0.20),
            # the knowledge floor is a cell, so what it answers is worth seeing:
            # a cell where nothing is committed buys the contrast nothing
            ("answers committed with no document to read", f"{floor:.3f}", None)]


def _r3(rows, sc):
    """The floor: the same cell served twice, measured and not thresholded."""
    got, lo, hi = band(sc, "differs_from_its_twin", rows)
    return [("floor, the same session served twice",
             f"{fmt(got)}  [{fmt(lo)}, {fmt(hi)}]", got == got)]


def _r4(rows, sc):
    probe = band(sc, "moves_with_the_source", rows)
    floor = band(sc, "differs_from_its_twin", rows)
    decorated = decorative_citation(rows)
    rate = sum(v for _, v in decorated) / len(decorated) if decorated else float("nan")
    return [("the answer follows what the store states",
             f"{fmt(probe[0])}  [{fmt(probe[1])}, {fmt(probe[2])}]", None),
            ("the instrument's own floor",
             f"{fmt(floor[0])}  [{fmt(floor[1])}, {fmt(floor[2])}]", None),
            ("the probe clears the floor", "", moved(probe, floor)),
            # reported beside it, without a verdict: it is the reading the
            # figure exists for, and no rung is climbed or failed on it
            ("cited the monograph twice and did not move",
             f"{fmt(rate)}  ({len(decorated)} clusters)", None)]


def _r5(rows, sc):
    """The realistic form: the same probe, asked the way users ask it."""
    here = live(rows, CASE)
    answered = share(here, commits_an_answer)
    named = share(here, _in_vocabulary)
    probe = band(sc, "moves_with_the_source_case", rows)
    floor = band(sc, "differs_from_its_twin", rows)
    return [("commits an answer on the case question", f"{answered:.3f}",
             answered >= 0.90),
            ("every cited id is a document the store holds", f"{named:.3f}",
             named == 1.0),
            ("reads the measured pair's monograph before answering",
             f"{share(here, consults_before_answering):.3f}", None),
            ("cites the measured pair's monograph, having read it",
             f"{share(here, cites_a_read_document):.3f}", None),
            ("the answer follows what the store states, asked as a case",
             f"{fmt(probe[0])}  [{fmt(probe[1])}, {fmt(probe[2])}]", None),
            ("clusters dropped for want of their other arm",
             str(dropped(next(m for m in sc.measurands
                              if m.name == "moves_with_the_source_case"), rows)),
             None),
            ("the case probe clears the floor", "", moved(probe, floor))]


LADDER: tuple[Rung, ...] = (
    Rung("R0", "do the mechanics bind", (BASE,),
         "an answer in the declared vocabulary on >= 0.90 of sessions, every "
         "cited id in the store's vocabulary, zero degraded turns", _r0),
    Rung("R1", "does it consult at all", (BASE,),
         "reads the measured pair's monograph before answering it on >= 0.80 "
         "of sessions; below that decoration is unmeasurable, and one model "
         "below is its result where the whole panel below is a design defect",
         _r1),
    Rung("R2", "does the store reach the answer", (BASE, WITHHELD),
         "accuracy with the store, against the knowledge floor, >= 0.20", _r2),
    Rung("R3", "the floor", (BASE, TWIN_CELL),
         "the same session served twice: measured and reported, never "
         "thresholded", _r3),
    Rung("R4", "does the answer depend on what the document says",
         (BASE, FLIPPED, TWIN_CELL),
         "the probe's interval clears the floor's, by their intervals and not "
         "by two point estimates; the decorative citation rate is printed "
         "beside it without a verdict", _r4),
    # BASE rides along because the shared floor is (base_twin, base): served
    # without it the floor is unreadable and the rung failed on every model of
    # the first smoke: the panel rule's textbook instrument defect.
    Rung("R5", "does grounding survive the question as users ask it",
         (CASE, CASE_FLIPPED, BASE, TWIN_CELL),
         "the case cell binds as `base` does, an answer in the declared "
         "vocabulary on >= 0.90 of sessions and every cited id in the store's "
         "vocabulary, and the case probe's interval clears the shared floor's",
         _r5),
)
