# TABIB spec

> Interfaces, record schema, invariants. `EXPERIMENTS.md` says what the
> experiments are; this says what the machinery guarantees.

## 1. Architecture

Built on [Inspect AI](https://inspect.aisi.org.uk/): the `.eval` log is the
primary datum, replayable with `inspect view`, and the per-sample store carries
the record. Nothing downstream re-scores a case.

Inspect owns the eval runtime, model providers, tool calling, resume and
provenance. TABIB owns what counts as a measurement.

```
tabib/
  scenario.py     Scenario + register/get + build_task, the declaration
  world.py        ToolSpec + World: one case, its tools, the served/truth chokepoint
  session.py      the solver: one prompt, a tool loop, one record
  measurand.py    Measurand + values/dropped/interval, what a number is
  nulls.py        Act + the policies the core derives from the declared acts
  task.py         (scenario, cell) -> Inspect Task: seeds, epochs
  models.py       the panel      run.py  run names      campaign.py  entry point
analysis/
  collect.py      logs -> one row per case, plus the cross-cell join
  gate.py         blind policies == 0, oracle away from 0
  report.py       per model: contrast, interval, saturation, and the figure
  raw.py          complete prompts and completions, one per cell
  watch.py        live serving invariants during a campaign
  by_arm.py       every movement split by the arm it happened on, the S2 protocol
  shape.py        structural half of the reading gate: lengths, turns, statuses
```

Content versus logic versus truth: logic in code, content in files under
`scenarios/`, truth in the log. Entry points import a scenario by name; core
modules never do.

## 2. One case

A scenario builds a world for one served version of one unit: the prompt, and
the tools. `World.call` is the only way a tool runs.

- **One chokepoint.** Every call logs `served` next to `truth`. Serving anything
  else without `injected=True` raises.
- The first terminal act closes the case. Which tools are terminal is not
  declared on the tool: the session marks the ones the scenario registered as
  acts, so the two cannot drift apart. A queue scenario inverts this locally:
  its per-file acts are ordinary tools carrying a `file_id`, one closing act
  (`end_shift`) is the only registered act, and the measurand reads the first
  act per file out of `meta`; `worked_session` is the model.
- An argument that is not part of the measurement goes in `optional`. A
  rejected call costs the model its whole turn and lands in the record as no act
  at all, which is a measurement error rather than a behaviour.
- `referential` marks the channel that queries the external reference. Querying
  it and finding danger in it are recorded separately, and both hold when the
  channel serves a manipulated version.

## 3. Interfaces

```python
Act(name, payload="", values=())                  # a terminal act
ToolSpec(name, description, params, handler, optional=(),
         injected=False, referential=False)        # handler(world, args) -> (served, truth)
World(prompt=..., tools=[...], meta={...}, markers=(...))
Measurand(name, y, cells=(), where=None, oracle_moves="up")
Scenario(name, acts, system, rows, build, measurands, oracle,
         budget=None)   # budget(cell) -> (max_steps, max_tokens); None = DEFAULT_BUDGET (8, 2000)
```

`rows(*, n, seed)` returns one dict per unit, with at least `id`. That id is
the cluster. `build(cell, row)` returns the World for one served version. A cell
is an opaque string; the set served is derived from what the measurands name.

## 4. The record

One flat dict per case, written by the solver into `tabib:record`:

```jsonc
{"act": "record_decision",   // the act committed, or "none"
 "payload": "PE",            // what the act's declared argument carried
 "args": {...},              // every argument, for reading and for scenario checks
 "status": "acted",          // acted | answered | budget | degraded
 "in_vocabulary": true,      // payload is one of the act's declared values
 "rejected_calls": 0,        // tool calls refused for their arguments
 "tool_calls": 2,            // a case with none never met a manipulation behind a tool
 "consulted": true,          // the reference channel was queried
 "warned": true}             // that query returned one of the declared markers
```

`world.meta` is merged in first, so a scenario adds its stratification variables
without the core knowing them. `status == "degraded"` means the turn was cut
short by the serving stack, not by the model; it is never an outcome.

`analysis/collect.py` adds `cluster` (the sample id), `epoch`, `model`,
`scenario` and `cell`. Two cells of one contrast run the same rows, so the same
id appears on both sides and pairs without a heuristic.

## 5. Invariants, each with its test

- A publishable number is a within-cluster contrast. Name two cells and you
  have one; name one and you have a rate, which gets no interval.
- **Repetitions pair before they average.** The key is (cluster, epoch), so a
  lost repetition cannot make a blind policy report an effect.
- Blind policies are enumerated by the core from the declared acts, and must
  score exactly zero. One of them consults first: where a manipulation sits
  behind a tool call, a policy that commits immediately never meets it, and its
  zero would be true by construction rather than by measurement.
- **The oracle must move each contrast** by at least 0.5, in the declared
  direction. An oracle producing the effect backwards is a scenario wired the
  wrong way round.
- `y` reads what the model did, never whether it was right. A measurand
  defined against the answer key rewards a constant answer;
  `tests/test_gate_fails.py` keeps that mistake as a toy the gate must reject.
- Seeds derive from the sample id and the epoch, never from the served text.
- The core imports nothing from `scenarios/`.
