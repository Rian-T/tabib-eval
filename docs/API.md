# The user-facing shape: three verbs, one package format

Written 2026-08-02. This is the target; the engine underneath does not move.

## The three verbs

```python
import tabib

world = tabib.load("your-org/companion-v1")    # a world package, resolved
                                               # locally or from a HF repo

run = tabib.run(
    agent="openai/gpt-5",                      # any OpenAI-compatible endpoint
    world=world,
    cells=world.protocol.cells,                # the cells the package declares;
    repetitions=3,                             # there is no free mixer
)

tabib.compare(run, baseline=older_run)         # paired contrasts, intervals,
                                               # read against the noise floor
```

A package refuses to run outside its own protocol. The API offers what the
package declares, never a bag of options: the instrument's validity conditions
travel with the world, not with the caller's discipline.

## What a package contains, in plain words

- **protocol**: the test plan, written and dated before any run, covering the cells,
  what counts as a number, and the declared figure.
- **noise_floor**: the same cell served twice, byte for byte; any effect
  below that gap does not count.
- **controls**: scripted agents shipped with the package (refuse-everything,
  accept-everything, and one that has the behaviour); a package whose probes
  cannot tell them apart refuses to produce numbers.

Today these live across `worlds/<name>/` and `scenarios/<name>/`. The package
format merges them into one directory with one manifest, hashes verified at
load, exactly as `worlds/` already does.

## Resolution

`owner/name` resolves to a HuggingFace repo (private or gated for commercial
worlds), snapshotted into a local cache; a bare name resolves from disk as
today. Compute nodes stay offline: fetching is a separate, explicit step.
Commercial worlds never enter this codebase. The code ships features, the
packages ship worlds.

## CLI

One console script, `tabib`: `run`, `report`, `gate`, `climb`, `view`.

## `view`: the scene

A live terminal view of one session: a marker among stations, one station
per affordance, the marker moving to the station it calls. Every glyph maps
to a declared property; a property the world does not declare simply does
not draw. Nothing is hardcoded per world and nothing new is
recorded: the scene is a reading of the engine's trace.

| element | source | absent -> |
|---|---|---|
| stations | the affordance list (name, description) | never absent |
| a station's motif | declared role: `referential` draws shelves, named in the scenario's `acts` draws a desk, others a plain named box | plain named box |
| the marker's position | the last trace event | centre, idle |
| the one speech bubble | the last served text or the current call's arguments, truncated to a fixed width | no bubble |
| the queue | the world's collections (`open_items`) | no queue |
| the status line | session counter + calls per affordance | always available |

Fixed budget, for every world: at most 7 drawn stations (beyond that,
role-less affordances collapse into one "n more tools" station), one bubble
of fixed width, at most 2 queues (then counters), automatic placement
(reference up, acts down, the rest on the sides). The degenerate world with
no roles, no collections and no served text degrades to named boxes around
an idle marker: the floor of the display, never a broken screen.
