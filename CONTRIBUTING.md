# Contributing

Thanks for looking. TABIB is a measurement instrument, so the bar is not "does
it work" but "would a reviewer believe the number". A few rules follow from
that; everything else is negotiable.

## Before a pull request

```sh
uv sync
uv run pytest          # green, always
```

The core (`tabib/`) imports nothing from `scenarios/`. If a change makes the
core aware of a scenario, it belongs in the scenario instead. `docs/SPEC.md` holds the
interfaces and the record schema, `docs/EXPERIMENTS.md` the experiments and the
rule they answer to.

## Five things a review will reject

**Ground truth we invented.** Danger comes from an external authority,
verbatim, never from our judgment. A scenario that hardcodes what counts as
unsafe is not measuring anything.

**A score computed from prose.** Outcomes come from terminal actions. Scoring
the final text measures verbalisation, not behaviour. An LLM judge is a last
resort, documented at the call site, never a default.

No cell where being permissive is right. A scenario needs one, or a model
that refuses everything passes it. Averaging risk and utility into a single
score hides exactly the failure the instrument exists to find.

A measurand defined against the answer key. `y` reads what the model did,
never whether it was right. Scoring "was the model correct" across two served
versions that disagree on what correct means inverts the instrument: a constant
answer collects the whole effect and a policy that reads the source perfectly
collects none. `tests/test_gate_fails.py` carries that mistake as a toy so it
stays visible.

**The wrong interval.** Name one cell and you have a rate: it is not identified
and gets no interval. Name two and you have a contrast, whose interval comes
from `measurand.interval`, resampling clusters. Repetitions of a unit pair
before they average and are never counted as independent observations.

**A number without its control.** A rate means nothing without the noise channel
that bounds it, and an effect under manipulation means nothing without the
placebo showing the manipulation itself is not the cause. Declare one with
`oracle_moves="none"`: the gate then requires that even a perfect reader finds
nothing there.

## Read the raw records before you believe a number

Aggregates hide everything that matters. Before any number leaves the repo,
read a handful of complete prompts and complete completions from **every**
cell, including the controls and the cells that look fine. This is a gate, not
a courtesy: on this instrument it has caught a passage builder that silently
dropped a section on a quarter of entries, a model returning empty strings
that looked like a parsing failure, a manipulated variable collinear with
document structure, an outcome label that named the opposite of what it
measured, and a refusal metric that counted answered questions as refusals.
None of it was visible in a clean summary table.

```sh
uv run python -m analysis.raw runs/<name>/<scenario> --cell <cell>
```

What to look at, per cell: does the served text read the way you intended, does
the completion parse for the reason you think, and does the recorded outcome
match what the transcript shows the model actually did. `docs/DEFECTS.md` lists
what this has caught so far, with mechanisms.

One rule from those: an identifier built by a function is only ever compared
through that function. Hand-rolling a second normalisation next to `canon()`
has silently produced a no-op and an everything-op here, both of which looked
like findings.

Another, paid for twice in one day: **one record shows a mechanism, never its
frequency.** A single transcript is enough to see how something goes wrong and
never enough to say how often. Read one to form the hypothesis, then count.

Half of this gate needs no reading at all and is worth running first:

```sh
uv run python -m analysis.shape runs/<name>/<scenario>
```

It prints shapes rather than content: served length per cell, turns per session,
statuses, tool-call sequences. The number worth the command on its own is the
served length. Two cells of a contrast must differ in what they state and in
nothing else, and a cell systematically longer than the one it is differenced
against carries a cue no measurand can see.

## The ladder

Nothing is built end to end. Each rung asks **one** question, has a **pass
condition written before it runs**, and is cheap; a rung that fails is repaired
before the next is attempted. `docs/LADDER.md` holds the doctrine, each scenario holds its conditions in
`scenarios/<name>/ladder.py`, and `jz/rung.py` runs them, so a threshold
cannot widen by exactly the amount needed once the number is on screen.

```sh
uv run python jz/rung.py <scenario>                           # list the rungs
uv run python jz/rung.py <scenario> climb <model>             # to the first failure
uv run python jz/rung.py <scenario> spread --from <dirs...>   # the golden rule
```

Two rules came out of using it, and both are about who is at fault.

**A rung that fails on every model is a defect of the instrument; a rung that
fails on some is the result.** So the ladder is climbed by a panel, never by one
model, and a first climb is worth more than a large sample on any one rung.

A rung that passes is permission to build the next one, never a finding.

The one thing a condition may be corrected for is asking a question the
quantities cannot answer. A channel is compared to the instrument's own floor by
their intervals, never by two point estimates: no finite sample lands exactly on
another, and comparing means once failed a model at +0.008 against a floor of
exactly 0.000, on a channel whose own interval covered zero.

## Running things

A run is a name; launch, resume and analyse all take the same string. See the
Runs section of the README. One process per log directory: two campaigns
pointed at the same one race, and the loser exits without writing anything.

Before a scenario runs against a paid model, it passes the gate:

```sh
uv run python -m analysis.gate <scenario> --n 60
```

The gate runs every blind policy the core derives from your declared acts and
requires each contrast to come out at exactly zero; then it runs your oracle and
requires the same contrast to move away from zero, in the direction you
declared. It blocks on failure rather than annotating the run.

If you know a policy that would game your scenario and the core does not derive
it, say so in the pull request rather than adding it yourself. Enumerating the
blind policies is the core's job precisely so that a scenario's blind spot
cannot quietly become its calibration's, and if a policy that reads the wrong
part of your material can reproduce your effect, the answer is usually to change
the design until it cannot, not to measure how much it reproduces.

## Style

Short modules, plain functions, no framework. Comments explain why a
non-obvious choice was made, not what the next line does. If a docstring needs
three paragraphs, the function is doing too much.
