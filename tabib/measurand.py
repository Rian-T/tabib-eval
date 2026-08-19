"""How a publishable number is defined.

A contrast is a change score inside one cluster: the mean of
`y(cells[0]) - y(cells[1])` over units that saw both. It is a structural
constraint, not a check run afterwards. A policy whose output does not depend on
the manipulation contributes exactly zero to every cluster, so it cannot produce
an effect. It also rules out comparing two arms whose correct answers differ:
there are no longer two arms with two answer keys, there is one cluster, two
served versions, and a difference.

Name two cells and you have a contrast; name one and you have a rate. A rate is
still worth printing but it is not identified, so it never gets an interval and
is never reported with the authority of a contrast.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import fmean
from typing import Callable

MOVES = ("up", "down", "none", "unscripted")


@dataclass(frozen=True)
class Measurand:
    """`y` maps one collected record to a number, usually 0/1.

    `cells` names the served versions: two of them, in the order (manipulated,
    reference), make a contrast. `oracle_moves` is what the gate requires of the
    scenario's oracle, which is not the same as what a model is expected to do:
    `none` marks a channel where even a perfect reader must find nothing.
    `where` selects the records that count at all.
    """
    name: str
    y: Callable[[dict], float]
    cells: tuple[str, ...] = ()
    where: Callable[[dict], bool] | None = None
    oracle_moves: str = "up"
    separates: float = 0.5      # how far the oracle must move this one
    # What an axis says on a figure read outside this repo. It lives beside the
    # definition rather than in the renderer: a second list of names for the
    # same quantities drifts from the first, silently, and the name a reader
    # sees is then not the thing that was computed. Empty falls back to the
    # identifier, which is right for a channel that only appears in a table.
    label: str = ""

    def __post_init__(self):
        if self.oracle_moves not in MOVES:
            raise ValueError(f"oracle_moves must be one of {MOVES}, got "
                             f"{self.oracle_moves!r}")
        if len(self.cells) > 2:
            raise ValueError(
                f"measurand {self.name!r}: at most two cells, got {self.cells!r}")

    @property
    def contrast(self) -> bool:
        return len(self.cells) == 2


def _per_run(m: Measurand, rows: list[dict], cell: str | None) -> dict[tuple, float]:
    """{(cluster, repetition): mean y} over one cell.

    The repetition is part of the key rather than averaged away, because both
    cells draw the same seed for the same (cluster, repetition): differencing
    there is what makes a blind policy score exactly zero. Averaging each cell
    first loses that as soon as one repetition goes missing, to an API error or a
    timeout, and a null policy then reports an effect of arbitrary sign.
    """
    seen: dict[tuple, list[float]] = {}
    for r in rows:
        if cell is not None and r.get("cell") != cell:
            continue
        if m.where and not m.where(r):
            continue
        seen.setdefault((r["cluster"], r.get("epoch", 1)), []).append(float(m.y(r)))
    return {k: fmean(v) for k, v in seen.items()}


def values(m: Measurand, rows: list[dict]) -> list[tuple[str, float]]:
    """[(cluster, value)] ready for `stats`.

    For a contrast, each repetition is differenced against its counterpart in
    the other cell and the differences are averaged within the cluster, so the
    cluster stays the unit. A repetition seen on one side only is dropped.
    """
    if not m.contrast:
        per: dict[str, list[float]] = {}
        for (cluster, _), v in _per_run(m, rows, m.cells[0] if m.cells else None).items():
            per.setdefault(cluster, []).append(v)
        return [(c, fmean(v)) for c, v in sorted(per.items())]
    hi = _per_run(m, rows, m.cells[0])
    lo = _per_run(m, rows, m.cells[1])
    paired: dict[str, list[float]] = {}
    for key in hi.keys() & lo.keys():
        paired.setdefault(key[0], []).append(hi[key] - lo[key])
    return [(c, fmean(v)) for c, v in sorted(paired.items())]


def difference(a: Measurand, b: Measurand, rows: list[dict]
               ) -> tuple[str, list[tuple[str, float]], list[tuple[str, float]]]:
    """Two contrasts compared, and how they may be compared.

    An experiment of this shape claims that one movement is larger than
    another, so that comparison is the result and it gets its own number and
    its own interval. Printing two contrasts side by side and leaving the
    reader to compare them by eye is the same mistake as printing a rate
    without an interval.

    Two contrasts can share their clusters or partition them, and the estimator
    is not the same. Two served versions of the same units are *paired*: each
    cluster gives one difference and the unit's own level cancels. Two subgroups
    of units (those a model already knew against those it did not) are
    *disjoint*: no cluster appears on both sides, pairing them yields nothing,
    and the comparison is a difference of two means over different units.

    Returns the kind and the two sides, so the caller resamples accordingly:
    paired gives one list and an empty one, disjoint gives both.
    """
    left, right = dict(values(a, rows)), dict(values(b, rows))
    shared = left.keys() & right.keys()
    if shared:
        return "paired", [(c, left[c] - right[c]) for c in sorted(shared)], []
    return "disjoint", sorted(left.items()), sorted(right.items())


def dropped(m: Measurand, rows: list[dict]) -> int:
    """Repetitions seen on one side of a contrast only. Report it: silent pair
    loss is how a contrast stops covering the corpus it claims to cover, and a
    lost repetition is also how a null policy stops scoring zero."""
    if not m.contrast:
        return 0
    hi = _per_run(m, rows, m.cells[0])
    lo = _per_run(m, rows, m.cells[1])
    return len(set(hi) ^ set(lo))


def gap(left: list[tuple[str, float]], right: list[tuple[str, float]], *,
        n_boot: int = 2000, seed: int = 20260725,
        alpha: float = 0.05) -> tuple[float, float, float]:
    """(difference of means, lo, hi) for two disjoint sets of clusters.

    Each side is resampled independently, because the units are not the same
    units: there is no pairing to exploit and pretending there is would report
    a precision the design does not have.
    """
    xs, ys = [v for _, v in left], [v for _, v in right]
    if not xs or not ys:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    draw = lambda zs: sum(zs[rng.randrange(len(zs))] for _ in zs) / len(zs)
    boots = sorted(draw(xs) - draw(ys) for _ in range(n_boot))
    return (sum(xs) / len(xs) - sum(ys) / len(ys),
            boots[int(alpha / 2 * (len(boots) - 1))],
            boots[int((1 - alpha / 2) * (len(boots) - 1))])


def interval(values_: list[tuple[str, float]], *, n_boot: int = 2000,
             seed: int = 20260725, alpha: float = 0.05) -> tuple[float, float, float]:
    """(mean, lo, hi) over one value per cluster, resampling clusters.

    The cluster is the unit, so repetitions already averaged into its value do
    not inflate the precision. Only a contrast gets one of these; a rate is not
    identified and is printed without.
    """
    if not values_:
        return float("nan"), float("nan"), float("nan")
    xs = [v for _, v in values_]
    rng = random.Random(seed)
    boots = sorted(sum(xs[rng.randrange(len(xs))] for _ in xs) / len(xs)
                   for _ in range(n_boot))
    lo = boots[int(alpha / 2 * (len(boots) - 1))]
    hi = boots[int((1 - alpha / 2) * (len(boots) - 1))]
    return sum(xs) / len(xs), lo, hi
