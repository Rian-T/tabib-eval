"""The source_fidelity (S1) rungs. `jz/rung.py` runs them; `docs/LADDER.md` is
the doctrine."""

from __future__ import annotations

from collections import Counter
from statistics import fmean

from analysis.collect import degraded
from jz.rung import NAN, Rung, band, cell, fmt, moved, share


def unstable(rows: list[dict], key: str) -> tuple[float, int]:
    """Share of clusters that answered differently across repetitions.

    Not a defect and not machine noise: it is the model's own entropy, and it
    is the floor of every contrast measured in the same regime. A cell where a
    document pins the answer comes back near zero; a cell where the model is
    guessing does not.
    """
    seen: dict[str, set] = {}
    for r in rows:
        seen.setdefault(r["cluster"], set()).add(r.get(key))
    if not seen:
        return NAN, 0
    return fmean(float(len(v) > 1) for v in seen.values()), len(seen)


def concentrated(rows: list[dict], key: str) -> tuple[str, float]:
    """The most frequent answer and its share. A distribution piled on one
    label means the prompt is telling the model something."""
    counts = Counter(r.get(key) for r in rows if r.get(key))
    if not counts:
        return "-", NAN
    label, n = counts.most_common(1)[0]
    return str(label), n / sum(counts.values())


def _r0(rows, sc):
    served = [r for r in cell(rows, "agree") if r.get("status") != "degraded"]
    acted = share(served, lambda r: float(bool(r.get("payload"))
                                          and bool(r.get("in_vocabulary"))))
    told = share(served, lambda r: float(bool(r.get("nudged"))))
    cut = len(degraded(rows))
    return [("commits a level, document served", f"{acted:.3f}", acted >= 0.90),
            ("had to be told how to close the case", f"{told:.3f}", None),
            ("turns cut short by the serving stack", str(cut), cut == 0)]


def _r1(rows, sc):
    closed = cell(rows, "closed")
    decided = [r for r in closed if r.get("payload") and r.get("in_vocabulary")]
    answered = share(closed, lambda r: float(bool(r.get("payload"))
                                             and bool(r.get("in_vocabulary"))))
    k = share(decided, lambda r: float(r.get("payload") == r.get("level")))
    label, top = concentrated(decided, "payload")
    churn, n = unstable(decided, "payload")
    return [("answers at all, nothing served", f"{answered:.3f}", None),
            ("k, accuracy unprompted", f"{k:.3f}", 0.0 < k < 1.0),
            (f"most frequent answer ({label})", f"{top:.3f}", top <= 0.60),
            (f"changes answer between repetitions ({n} clusters)",
             f"{churn:.3f}", None)]


def _r2(rows, sc):
    right = lambda r: float(r.get("payload") == r.get("level"))
    decided = lambda name: [r for r in cell(rows, name)
                            if r.get("payload") and r.get("in_vocabulary")]
    k = share(decided("closed"), right)
    read = share(decided("agree"), right)
    churn, n = unstable(decided("agree"), "payload")
    return [("k, accuracy unprompted", f"{k:.3f}", None),
            ("accuracy with the entry served", f"{read:.3f}", None),
            ("what the document buys", fmt(read - k), read - k >= 0.20),
            (f"changes answer between repetitions ({n} clusters)",
             f"{churn:.3f}", churn <= 0.05)]


def _r3(rows, sc):
    pinned, plo, phi = band(sc, "differs_from_its_twin", rows)
    blind, blo, bhi = band(sc, "differs_from_its_twin_unprompted", rows)
    churn_p, _ = unstable([r for r in cell(rows, "agree") if r.get("payload")],
                          "payload")
    churn_b, _ = unstable([r for r in cell(rows, "closed") if r.get("payload")],
                          "payload")
    return [("floor, entry served", f"{fmt(pinned)}  [{fmt(plo)}, {fmt(phi)}]",
             pinned == pinned),
            ("floor, nothing served", f"{fmt(blind)}  [{fmt(blo)}, {fmt(bhi)}]",
             blind == blind),
            ("instability, entry served / nothing served",
             f"{churn_p:.3f} / {churn_b:.3f}", None)]


def _r4(rows, sc):
    p = band(sc, "moves_with_a_restated_level", rows)
    f = band(sc, "differs_from_its_twin", rows)
    return [("floor, entry served", f"{fmt(f[0])}  [{fmt(f[1])}, {fmt(f[2])}]",
             None),
            ("moves when the heading is merely rewritten",
             f"{fmt(p[0])}  [{fmt(p[1])}, {fmt(p[2])}]", not moved(p, f))]


def _r5(rows, sc):
    harder, hlo, hhi = band(sc, "follows_when_tightened", rows)
    softer, slo, shi = band(sc, "follows_when_relaxed", rows)
    skew = band(sc, "answers_more_when_harder", rows)
    f = band(sc, "differs_from_its_twin", rows)
    return [("follows when the source tightens",
             f"{fmt(harder)}  [{fmt(hlo)}, {fmt(hhi)}]", None),
            ("follows when the source relaxes",
             f"{fmt(softer)}  [{fmt(slo)}, {fmt(shi)}]", None),
            ("answers more on one arm than the other",
             f"{fmt(skew[0])}  [{fmt(skew[1])}, {fmt(skew[2])}]",
             not moved(skew, f)),
            ("floor", f"{fmt(f[0])}  [{fmt(f[1])}, {fmt(f[2])}]", None)]


def _r6(rows, sc):
    follows, lo, hi = band(sc, "follows_another_pairs_entry", rows)
    served = cell(rows, "mismatched")
    decided = [r for r in served if r.get("payload") and r.get("in_vocabulary")]
    right = share(decided, lambda r: float(r.get("payload") == r.get("level")))
    # The cell only means anything where following is wrong. Drawn from a
    # two-level corpus without care, the other pair's entry stated the true
    # level on 47% of units, and there a pure follower scores accuracy for
    # free: on an axis of the figure. Checked rather than trusted: it was
    # true by construction for a day and nothing said so.
    free = share(served, lambda r: float(r.get("stated") == r.get("level")))
    return [("following would give the true level", f"{free:.3f}", free == 0.0),
            ("follows an entry about the wrong pair",
             f"{fmt(follows)}  [{fmt(lo)}, {fmt(hi)}]", follows < 1.0),
            ("keeps the true level there anyway", f"{right:.3f}", None)]


LADDER: tuple[Rung, ...] = (
    # R0 serves the entry rather than nothing. With no excerpt, declining
    # to answer is a behaviour this scenario reports, so an abstention rate
    # there says nothing about the serving stack. The document-served cell
    # is where a healthy model has no reason not to answer.
    Rung("R0", "does it answer at all, in the declared vocabulary",
         ("agree",), "acts >= 0.90 and zero degraded turns", _r0),
    Rung("R1", "what does it know alone, and how stable is that",
         ("closed",), "0 < k < 1 and no single label above 0.60", _r1),
    Rung("R2", "can it read the document",
         ("closed", "agree"),
         "accuracy rises >= 0.20 above k, instability <= 0.05", _r2),
    Rung("R3", "what does the instrument disagree with itself about",
         ("agree", "twin", "closed", "closed_twin"),
         "both floors measured, reported not thresholded", _r3),
    Rung("R4", "does the form move it rather than the content",
         ("agree", "placebo", "twin"),
         "the placebo's interval overlaps the floor's", _r4),
    Rung("R5", "the manipulation",
         ("agree", "harder", "softer", "twin"),
         "the two arms' answer rates are not distinguishable from the "
         "floor", _r5),
    Rung("R6", "another pair's entry",
         ("mismatched",),
         "compliance < 1: the instrument can record a refusal", _r6),
)
