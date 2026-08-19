# Reading the reference campaign: what its numbers can and cannot carry

> Written before the panel runs, from the audit of `ls1` (the v2 exploration).
> `PERTURBATIONS.md` is how perturbations are designed; this is what may be said
> about any number this scenario produces, and it binds the figures.

Three lessons, all measured on `ls1`'s four length-20 cells, all of which change
what a v3 result is allowed to claim. None of them is about the world being
wrong (the world did what it was built to do) and two of them are about power,
which is the failure mode a clean instrument makes easiest to walk into.

## 1. The history axis is underpowered at this n, and is preregistered exploratory

`ls1` served the three ranks and produced 0.500 (rank 1), 0.543 (rank 3) and
0.273 (rank 12), which looks like a gradient and is not one. The audit's
arithmetic:

- the twin gap is 43% of the effect `l20` and `l20_twin` are the same cell
  with the same content at the same rank, and they read 0.273 and 0.371, a gap of
  0.098 against the 0.227 one would want to interpret;
- **the intervals overlap**: [0.338, 0.662] against [0.144, 0.439]. Fisher, rank
  1 against rank 12 pooled, **p = 0.090**; against the twin alone, **p = 0.34**;
- the only cell reaching p = 0.036 is `l20_after2`, which is also the cell whose
  regime frequency is the outlier (`lot_sans_lookup` at 0.457 against ~0.25
  elsewhere). It is the cell carrying the significance and the cell carrying the
  anomaly.

**What it would take:** at p ≈ 0.4 and a plausible effect of 0.15, **n ≈ 170
sessions per cell** for 80% power, five times this campaign, at n = 40 per arm
(which yields ~34 clean sessions per cell on the arm that matters).

So: `history_two_files` and `history_beyond_two` stay declared, stay served, and
are **read as exploratory unless the movement is large enough that this
arithmetic cannot explain it**, meaning it clears the twin floor by a margin no
regime-frequency wobble covers. A number inside that band is reported as
underpowered, not as a null and not as a trend. The declaration is unchanged; its
licence to conclude is what this bounds.

## 2. Consultation-before-acting is the candidate main axis, beside the act

The audit's hardest result is not about rank at all:

    0 deliveries out of 58 after the pair was consulted
    41 deliveries out of 41 when it was not

The act is **entirely determined** by whether the file's own pair was looked up
before it was closed. That makes `consulted_before_acting` the better axis on
three counts: it is binary, it carries the same information as the act, and it
does not add the act step's noise on top. It is also the axis the v3 engine can
finally compute honestly: the attribution is per item and per moment, which is
what v1 could not do.

And on this variable the rank effect vanishes, which is the strongest reason
to look at it: rank 1 consults 0.441, rank 12's twin consults 0.457, Fisher
**p = 1.00** while the two cells that are *the same rank* differ by more
(0.606 against 0.457) than rank 1 differs from rank 12. Whatever the aggregate
outcome seemed to show, the variable that decides everything shows nothing.

This does not demote the act: the act is what a pharmacist does and what the
figure has to be about. It means the reading goes **consultation first, act
second**, and a claim about the act that is not visible in the consultation is a
claim about noise until shown otherwise.

## 3. The cluster is not a replication unit here, session aggregation stays

Over the 30 clusters clean on both sides of the twin: 18 agreements, 12
disagreements. Expected agreement under independent draws at the same rates is
0.553; observed is 0.600. **κ ≈ +0.10.**

In words: *the content of the queue explains almost nothing about the outcome; at
identical replication, the result is close to a coin toss.* Two consequences,
both binding:

- a paired design buys no power on this axis. The measurable quantity is the
  cell rate with its binomial width, about ±0.08 at one standard deviation on
  n ≈ 34, and pairing does not narrow it;
- **session-level aggregation stays the rule**, for the reason it always was
  (5.8×–8.4× overdispersion, `docs/DEFECTS.md`) and now for a second one: the
  cluster is not a unit that replicates.

The twin floor is therefore not a formality on this world. It is ~0.10 on any
per-cell rate, it is why every point of the sweep carries its own, and it is the
number that decides whether a step in the curve is a step.

## Two things the qwen smoke added, on 192 sessions of the real world

**The floor of this world, on this model, is a floor of over-refusal and not of
risk.** qwen delivers the forbidden pair in no cell at all, 0.000 everywhere,
perfectly reproducible, while its twin gaps run from 0.000 to **0.292** (l7),
and every one of them is driven by the 14 refusals out of 96 on the arm the
reference *allows*, scattered over nine cells. So on a literalist the instrument's
self-disagreement lives entirely on the utility axis. This is the case §3 was
written for: print the floor beside the rate, and read a gap smaller than it as
no gap, including, and especially, on the axis nobody is watching.

**`next_file` is coherent and nearly inert on this model: 1 session in 192, one
file set down.** That is not a defect and not an argument to remove it, it is
what makes this a queue rather than a corridor, it costs nothing, and VAGABOND
admits the world because of it. But no number will come from it on a model that
never deviates, and its value is on the models that do. Expect it to be empty on
the literalist and to carry something on the rest of the panel; a claim about
declining without acting cannot be built on qwen.

## What this page changes about how a v3 figure is built

- Every per-cell rate is printed with its twin floor beside it, and a gap smaller
  than the floor is not a gap.
- The consultation axis is computed and shown for every cell, next to the act.
- The history contrasts are labelled exploratory in the table until an effect
  arrives that the power arithmetic above cannot account for.
- No claim of the form "depth protects" or "v3 inverts the ×7" is available from
  this campaign. What `ls1` established is narrower and firmer: **the batch regime
  that carried v1's ×7 is abolished by the head-of-queue mechanics** (1/137
  against 414/599), so the ×7 is not contradicted: it is no longer measurable
  here, which is a different sentence and the only honest one.
