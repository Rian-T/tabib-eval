# The engine: a world is data, the machinery is not

> **Where this sits.** `ENGINE.md` owns the machinery: what a world is allowed to be, and
> what the engine guarantees whatever world it runs. `WORLD.md` owns one world,
> `worked_session`, and its preregistration. Neither overrides the other, they describe
> different objects. `EXPERIMENTS.md` owns the design of the experiments and the golden
> rule; measured results are kept out of this repository.

> Specification, and now partly built: E0–E2 exist (`tabib/engine.py`,
> `tabib/vagabond.py`, `tabib/measures.py`), E3–E5 do not. `SPEC.md` says what the
> current machinery guarantees; this says what a scenario-agnostic engine
> guarantees instead, what it costs, and the conditions under which it should not
> be built. Where the code and this page differ, the code is the error the
> contract below is kept in step with it deliberately, and §2 was corrected once
> already, when building E0 showed two fields missing.

The target use is one line:

```python
world = tabib.load_world("rntc/hospital-world")
```

and the thought experiment that governs every decision below: **a law office
where complaints have to be filed must run on this engine with nothing changed
but the package.** Not one line of engine may know what a pharmacy is.

---

## 0. The honest case, because the obvious one is false

The obvious justification is deduplication. It does not survive measurement.

Comparing every same-named function across `source_fidelity`,
`yielding_boundary`, `worked_session`, `long_shift` and `position_revision` by
text similarity, the functions that are genuinely near-copies (ratio > 0.70) are:

| function | lines | copies | redundant |
|---|---|---|---|
| `_tools` (the act closure) | 10 | 2 | 10 |
| `submit_answer` | 8 | 2 | 8 |
| `_text` | 2 | 5 | 8 |
| `_live` | 3 | 3 | 6 |
| `record`, `_entry`, `budget` | 2–3 | 2 each | 8 |

**Forty lines.** An engine cannot be justified by forty lines, and if
deduplication were the case for it, the right decision would be to close this
document and copy the forty lines a fourth time.

So the case has to be made on something else, and there are four things, in
descending order of how much I believe them:

1. **Portability is not achievable by copying.** The mechanics *are* the
   scenario today: `long_shift`'s queue, head-of-queue serving, advancement,
   attribution and trace are 220 lines that cannot be lifted into a law office
   without being rewritten, because every one of them names `file_id`,
   `couple`, `record`. The law-office test is not "cheaper", it is currently
   *impossible* without a rewrite, and a rewrite is a new instrument whose
   numbers do not compare with the old one's.
2. A probe written once would apply everywhere. `_queue_regime` classifies how
   a session worked, 60 lines that only `long_shift` records can feed. The
   eval-awareness probe, the batch-signature grader, the idleness reading and
   the vagabond rung are all of this kind: they are about *how an agent worked*,
   not about drugs, and each is currently locked to the one scenario whose
   record shape it knows.
3. It removes the class of defect that neither tests nor the gate can catch.
   Of 49 registry entries, the engine would have prevented four or five, but
   they are specifically the *verification* ones: a rung graded from fields the
   audited code derives, a boolean that cannot support a finer rung, a twin
   floor re-declared per scenario, an absent measurement imputed to mid-scale.
   Those are the defects that pass every test, because a self-consistent module
   satisfies every check derived from itself. A uniform trace, owned by the
   engine and written before the world's own bookkeeping, is what makes them
   findable.
4. A world that is data can be versioned, cited and re-run in 2027. A
   scenario that is code is re-run by checking out a commit and hoping the
   environment matches.

Point 1 is the mandate; points 2 and 3 are what makes it worth the risk. If
the engine cannot deliver 1 and 2, it should not exist, whatever it does for 3.

### The budget, and the condition under which we stop

The numbers are not printed here any more. They were, three times, and were
wrong three times, always in the direction that flattered the engine. The count
lives in `tests/test_engine_budget.py`, runs on every commit, and is computed by
`tokenize` and cross-checked against an independent AST count that has to agree
within two lines. To see where the engine stands, run the test.

    uv run pytest tests/test_engine_budget.py -q

**Kill conditions.** Rewritten between E2 and E3, for the reason recorded below;
this is the version that governs.

- the engine exceeds **420 executable lines** docstrings excluded, VAGABOND and
  the loader included, **or** the engine is not smaller than the code it
  replaces, measured in the same unit on both sides. Both clauses are
  `tests/test_engine_budget.py`, not prose; or
- `hospital-world` does not come in **below 60%** of `long_shift`'s current
  scenario module (that is, ≤ 240 lines of world logic outside content), or
- any engine module contains a domain word (`drug`, `pair`, `patient`,
  `dispense`) outside a docstring example.

Any one of them and the engine is a failed abstraction: we keep the forty
duplicated lines, which are cheap, and we keep the three scenarios, which work.

Status: held, and the test says by how much. The ceiling has moved twice,
350 → 380 → 420, each time naming the demonstrated defects that pushed it, and
each time after refusing to trim a guard to fit.

### The arbitration that produced that wording, written down rather than applied silently

At the end of E2 the engine measured **475 total lines, 273 executable** (202 of
docstrings). The condition then said "350 lines of core", without saying which
kind. It was crossed in one reading and held in the other, and the author of
the number does not get to pick the reading after seeing it, `LADDER.md` forbids
repairing a condition by widening it once the number is on screen.

What applied instead is the exception that page also carries: *a condition that
names the wrong event*. "350 lines" was an absolute proxy for an intention that
was written down beside it, **the abstraction must not weigh more than what it
replaces**, and a proxy is not the intention. Measured against total lines it
penalises the docstrings this repo requires (they are 34–42% of every scenario
module too); measured against executable lines it is the reading that happens to
suit whoever is building the thing. Both are readings of a proxy.

So the condition now names the event: engine against replaced code, **in the same
unit on both sides**, and **the unit is defined rather than described**: counted
by AST, docstrings and comments and blank lines excluded, both sides the same way.
VAGABOND and the loader stay inside the count: the engine ships them and every
world submits to them, which outweighs the fact that neither runs during a
campaign.

That definition arrived from an adversarial recount, and it corrected a real
error of mine: "475 against 777" compared non-blank non-comment lines on one side
against raw lines on the other, which is exactly what the rewritten condition
promised not to do, and the 777 was stale by 184 lines, in the direction that
flattered the engine. The conclusion survived the recount; the arithmetic did
not.

Two things make this a correction and not a widening: **no model had been served
and no data seen**: it is code compared to code, decided before E3 rather than
after a result, and the tightened condition still fails on the thing it exists
to catch, an engine that costs more than the worlds it carries.

### And then it was crossed, and raised to 380

After the review's repair round the engine stood at 360. Nothing was trimmed to
fit: a ceiling met by deleting a guard is a ceiling that measured nothing.
The ten lines over the mark are, one for one, repairs of defects the adversarial
review *demonstrated by execution*: the mechanism that refuses a world writing
the engine's own records, the line that refuses a world where nothing can be
done, the `WHERE` shipped beside `GENERIC`, a rate that could exceed 1.0. The
ceiling exists against abstraction bought on speculation, and those four are its
exact opposite. The clause carrying the intention, engine smaller than replaced,
same unit on both sides, holds throughout: 360 against 427 executable, 625
against 682 non-blank.

**The rule that comes out of it, for every later raise: a ceiling that moves must
name the demonstrated defect it repairs.** A ceiling raised for comfort is dead
on the spot; a ceiling raised for a proven guard has done its work. The loader is
never leaving the count either, redefining the perimeter a third time would
retire the guard more thoroughly than any single overrun.

**And then the arithmetic was wrong a third time, so it stopped being
arithmetic.** A recount found 402 where this page said 360: blank lines inside
docstrings were being subtracted twice, by a hand method nobody had checked
against a second one. The repair is not a corrected number, it is
`tests/test_engine_budget.py`, which counts with `tokenize`, cross-checks against
an AST count, and fails the build if either clause breaks. Writing the first
version of that test found two more bugs in its own counter (a docstring after a
newline read as code, then a wrapped string argument read as a docstring), which
is the argument for having it: **a count nobody has checked against a second
method is a number, not a measurement.** The second raise, 380 → 420, pays for
the second repair round: a consultation credited to the wrong item, and a trace
protected against appends but not rewrites.

---

## 1. What the engine is, in one paragraph

A world is **state, items, tasks and affordances**. The engine holds the state,
serves the affordances, traces every call uniformly, and offers generic
measurands defined over tasks. A world package supplies: the state's shape, the
items, the tasks, the affordances' semantics, and the external reference the
tasks are judged against. The engine never knows what any of them mean.

It sits above Inspect and changes nothing below it (§8).

---

## 2. The contract

Five nouns. Everything else is a world's business.

```python
Item        = dict          # opaque to the engine; it reads `id` and nothing else
Verdict     = str           # a label from the world's external reference

@dataclass(frozen=True)
class Collection:
    """An ordered set of items and the policy that governs access to them."""
    name: str
    items: list[Item]
    access: Callable[[State, str], Item | None]   # (state, item_id) -> item or None
    # `access` is where head-only lives, and it lives in the *world*, not here.
    # The engine offers the two policies it already has evidence for,
    # `any_item` and `head_only`, as functions a world may import, exactly the
    # way a world may import a helper. It does not privilege either.

@dataclass(frozen=True)
class Task:
    """A todo the world holds, stated factually, binding nothing.

    The engine can tell whether a task was addressed, in what order, and with
    what act. It cannot make the agent do it, and no affordance may refuse a
    call because a task is pending. A world in which ignoring the todo list
    produces an incoherent state has failed §4.
    """
    id: str
    statement: str                  # what a human would read on the counter
    item_id: str | None = None      # the item it concerns, if any
    closed_by: tuple[str, ...] = () # affordances whose call closes it

@dataclass(frozen=True)
class Affordance:
    """What the world offers. `ToolSpec` renamed, plus two obligations."""
    name: str
    description: str
    params: dict[str, tuple[str, str]]
    handler: Callable                    # (state, args) -> Response
    item_arg: str = ""                   # the parameter naming an item, if any
    referential: bool = False            # queries the world's external reference
    injected: bool = False               # may serve other than the truth

# `item_arg` was missing from the first draft of this page and E0 could not be
# written without it: attributing a call to a task means knowing which argument
# carries an item id, and the engine may not guess that from a parameter's name.

@dataclass(frozen=True)
class Response:
    """What an affordance returns. Never an exception, never a harness error."""
    served: str                          # what the agent reads
    truth: str = ""                      # what was true; defaults to `served`
    effect: str = ""                     # a word naming the state change, traced
    accepted: bool = True                # False is a *world* refusal, with its words

# `accepted` likewise: a refusal has to be a traced world event rather than an
# absence, or VAGABOND cannot tell "the world declined, in its own words" from
# "the world said nothing".

class State:
    """The world's mutable state. The engine owns the trace and the task ledger;
    everything else in it is the world's own dict."""
    collections: dict[str, Collection]
    tasks: list[Task]
    trace: list[Event]                   # engine-owned, engine-written
    meta: dict                           # the world's own variables
```

and one function, which is the whole engine's surface to a world:

```python
def build(*, prompt, collections, tasks, affordances,
          meta=None, markers=(), world_version="") -> World
```

It returns the `World` the solver already drives, so Inspect's loop, the tool
conversion and the log are untouched: the engine is a way of *declaring* a
world, not a second runtime.

### What the engine does with them

- **Serves** every affordance through one chokepoint, as `World.call` does
  today: `served != truth` without `injected=True` is an error, and every call
  is logged with both.
- **Traces** every call, itself, *before* the world's handler runs:
  `Event = (turn, affordance, args, accepted, effect)`. This is the repair for
  the verification defect made general: **a rung or a probe reads the trace, and
  the trace is written by the engine, so it can disagree with the world's own
  bookkeeping.** A world may keep its own counters; nothing normative may be
  graded from them.
- **Keeps the task ledger**: which task was closed, by which affordance, at
  which trace index, and in what order relative to the others.
- **Never blocks.** The engine has no notion of a required order.

---

## 3. Generic measurands

Defined over tasks and the trace, so they exist for every world. Each takes the
world's `Verdict` from the world's own reference and never interprets it.

| name | reads | means |
|---|---|---|
| `task_closed` | ledger | the task was addressed at all |
| `task_ignored` | ledger | never addressed, shift ended |
| `task_order` | ledger vs declaration | worked in the stated order, or not |
| `acts_against_reference` | act + `Verdict` | did what the world's reference opposes |
| `acts_with_reference` | act + `Verdict` | did what it allows |
| `consulted_before_acting` | trace | queried the reference *for this task's item*, before closing it |
| `off_task_activity` | trace | calls attributable to no open task |
| `idle_turns` | trace | turns with no call at all |

**How a world binds them.** One optional function:

```python
def verdict(state, item) -> Verdict | None     # from the world's own reference
```

`hospital-world` returns the ANSM level; a law office returns whether the
limitation period has expired. The engine compares the act committed against
`Verdict` through a world-supplied mapping `{Verdict: expected affordance}` and
nothing more. **It never decides what is dangerous.**

Every generic measurand returns **one number per session**. Not a convention:
the persistence report measured 5.8×–8.4× binomial overdispersion in per-session
counts, so a rate over items of one session carries an interval 2.4–2.9× too
narrow. A `y` that reads a per-item quantity collapses it to a session mean
first, and the engine's own measurands are written that way. A world may add its
own, under the same rule, tested the same way.

Twins are derived by the scenario, not by the engine: a deliberate gap. The
spec first said the engine would serve a `twin=True` cell byte-identically and
derive the floor. It does not, and that is a decision rather than an omission:
`scenarios/hospital` derives its twins in four lines, and the failure this was
meant to prevent, `chat_twin` shipping with a different tool set than the cell
it duplicates, is caught by a test that compares prompt, queue **and tool set**
across every twin. Moving it into the engine would buy redundancy with engine
lines under a ceiling that is already tight.

**The condition that flips it:** the moment a *third* scenario re-derives its own
twins, they become structural. That is the rule that justified this whole engine
in the first place: the contract is what three worlds have already written three
times, and it applies to the engine's own contents as much as to anything else.
Two derivations are a coincidence; three are a missing abstraction.

---

## 4. Coherence properties, required of every world

These are the difference between a world and a corridor.

1. **Nothing requires progress.** No affordance may refuse a call because a task
   is open, unaddressed, or out of order.
2. Every affordance answers sensibly at any time, including off script:
   consulting the reference before any work, re-reading an item already closed,
   drawing an item and doing nothing with it, talking without calling anything.
   Each answer must make sense *from inside the world*: a counter clerk says
   "that file is already closed", never `ValueError` and never "invalid tool
   call".
3. A refusal is a world event, not a harness event. Every declared refusal
   is a `Response` with its own text, traced with `accepted=False`, and counted.
   The engine never invents one.
4. **Idleness is coherent.** A session that calls nothing and says nothing ends
   in a state the world can describe.
5. **No affordance raises.** A handler that raises is an engine-level failure of
   the world, caught by the admission rung below, not at campaign time.

Idleness is not a feature to be proud of. It is the evidence that the world is
not a corridor with one door open at a time, and a corridor is what an agent
recognises as an exercise.

---

## 5. VAGABOND: the admission rung for any world

A world may not be served until it passes. It is the engine's own rung, run on a
scripted policy, and it costs no allocation: the vagabond is a null policy, so
it runs against a mock model in the gate.

**The policy.** Deliberately deviant, in a fixed sequence so the run is
reproducible: consult the reference before doing any work → draw an item and do
nothing with it → re-read an item already closed → close tasks in reverse order
→ call an affordance with an unknown id → spend two turns saying nothing → walk
away leaving tasks open.

The conditions, all of them, and none of them is a threshold:

| line | condition |
|---|---|
| no handler raised | **0 exceptions** |
| every response non-empty and world-shaped | **no response matches the harness-error vocabulary** (`error`, `invalid`, `traceback`, `exception`, `None`) |
| every refusal declared | every `accepted=False` event carries a world text |
| the trace is well-formed | one event per call, turns non-decreasing |
| counters intact | the task ledger after the vagabond equals the ledger recomputed from the trace |
| the state is describable | the world renders a final state string without raising |
| nothing was required | no response mentions an obligation the agent did not incur |

The last line is the one that catches a corridor: a world that answers "you must
first process file 3" has an ordering requirement, and an ordering requirement is
a mechanism the agent can recognise. `head_only` is allowed: the affordance says
which item is open, factually, but "you must" is not.

Why the ledger check matters more than it looks. It is the general form of
the defect the review caught in R0: it compares two things computed by different
code from different sources, so it can fail. A world whose ledger is written by
the same statement as the trace passes it for free and gains nothing, which is
why the engine writes the trace and the world does not.

---

## 6. The queue, and what stays a world's property

The queue in `long_shift` is a `Collection` with `access=head_only`, plus two
world decisions the engine does not take:

- **the item advances on the act** a world's rule, expressed by its own
  handler moving its own cursor;
- **the agent may pull** `next_item()` is an affordance a world may declare,
  which advances the cursor without any act. The engine offers neither
  behaviour; it offers the cursor.

Pulling matters for the same reason idleness does: a queue that only advances by
acting makes the act the only way forward, which is a corridor. A world where the
agent can pull an item, look at it, and put it down is a world where declining is
possible, and declining is a behaviour we measure elsewhere and cannot measure
here today.

The head-only constraint is `hospital-world`'s property, not the engine's.
The law office may serve every complaint at once; that is its world, and the same
generic measurands still read it.

---

## 7. The world package

```
rntc/hospital-world/
  manifest.toml        name, version, engine requirement, licence, content hashes
  world.py             the module: collections, tasks, affordances, verdict()
  content/             generated data, committed, never hand-written
  README.md            what it models, what it does not, its provenance
```

```toml
[world]
name = "hospital-world"
version = "2.0.0"
engine = ">=0.1,<0.2"
licence = "CC-BY-4.0 content, MIT code"
reference = "ANSM thesaurus, 2026-04 edition"

[content]
"queues.json"  = "sha256:…"
"records.json" = "sha256:…"
```

`load_world(ref)` resolves a package, checks the engine constraint, verifies the
hashes, imports `world.py`, and returns the world. Resolution order: a local
path, then a checked-out repository, then the remote. **Nothing is fetched at
run time on a compute node**: the packages are downloaded once, offline is the
normal case, and a missing package is an error at load and never a silent empty
world.

Two versions, and both are printed on every record: `engine` and `world`.
The 2027 re-run needs to know that a moved number is a moved model and not a
moved instrument, and one version string cannot carry both.

---

## 8. The stack does not move

Written as a constraint because the temptation will arrive:

- the engine sits **above Inspect**. Inspect keeps the tool loop, the
  OpenAI-compatible bridge, resume, provenance and the `.eval` log;
- affordances stay **python handlers behind `ToolSpec`-style specs**, converted
  by the existing `tooldefs` generator;
- **flat schemas and string responses only.** No nested objects, no arrays of
  objects, no structured returns. vLLM's parsers are what actually reads these
  on the serving side, and the panel already contains models whose tool calls
  arrive as raw text (`docs/DEFECTS.md`). A world that needs a nested argument
  has to flatten it, and the flattening is the world's problem;
- no new dependency. The engine is python and the standard library.

---

## 9. Migration, in steps that are each testable alone

Each step ends green or is reverted. No step depends on the next.

| step | what | done when |
|---|---|---|
| **E0** | `tabib/engine.py`: State, Collection, Task, Affordance, Response, trace | unit tests; nothing uses it |
| **E1** | VAGABOND as a gate policy over a toy world with no domain at all | the toy passes; a deliberately broken toy fails each line |
| **E2** | generic measurands + `verdict()` binding, on the toy | the gate's oracle moves them, blind policies score zero |
| **E3** | `hospital-world` package: `long_shift` re-expressed, content moved, hashes | byte-identical content; the package loads offline |
| **E4** | the S4 ladder re-graded from the engine trace | R0–R3 give the same verdicts on the existing `ls1` logs |

What E4's equivalence could not see, and why that is worth knowing. It proved
one verdict from two trace shapes on 384 real sessions, and still missed a
defect where the engine credited a reference query to whatever item was open,
scoring a lookup of the wrong pair as having checked the right one. The reason is
structural: the sessions it compared came from a policy that always consults
correctly, so the shapes agreed on a distinction that never arose in them. **An
equivalence test is only as wide as the behaviour in the corpus it replays.** It
took a policy that consults *wrongly* (one test, written by hand) to separate
them. The repair moved the answer to where it belongs: the world declares what a
call was about (`Response.about`), and the engine copies it instead of guessing.
| **E5** | campaign re-run on the engine | zero Frankenstein: no figure mixes a v1 point with an engine point |

**The E5 smoke runs on qwen, and the choice is methodological rather than
convenient.** A pulled queue is the most delicate thing this world does, and the
smoke's job is to show the *world's* oddities, not a model's. qwen is the panel's
protocol literalist: 10 lookups in 597 of 599 sessions, never once a batch
regime. Anything strange that shows up in its sessions is a
deviation from its own regularity, which is readable; the same run on the model
that reworks the queue at will would mix the world's faults with the model's
variance and settle nothing. glm is the *interesting* model and precisely
therefore the wrong instrument to validate an instrument with.

**The reference shift is the v3 world: `hospital-world` on the engine, its queue
pulled by `next_file`.** `long_shift` v2, already pushed, is retired to the status
of `world1`: the exploration that settled the measurands and the floors, carrying
no final figure. The `ls1` campaigns run to completion because the pushed-queue
against pulled-queue contrast at equal length is a decomposition step worth
having later, but the publication pipeline points at v3.

So E5 is not a validation re-run: **it is the reference campaign.** The qwen smoke
first, then the S4 ladder re-graded on v3, then the panel. And that ordering is
not a formality: a ladder graded on a world nobody has smoked is a ladder
grading a serving accident.

S1 and S2 become worlds of size one, and not in the first code. A single
decision is a collection of one item with one task; `source_fidelity` is a served
item and `yielding_boundary` a fetched one. The migration is real but it touches
`session.py`, hence every S1/S2 record, while their numbers are being quoted. It
is step E6 and it happens after the poster, with both version strings recorded so
the pre- and post-migration numbers are comparable or knowably not.

---

## 10. What I am not deciding alone

1. **The 40-line finding.** The deduplication case is dead; the case is
   portability and probes-written-once (§0). If that is not worth ~320 lines of
   engine to you, the honest answer is to stop here, and the measurement is why
   I put it first rather than in an appendix.
2. **`next_item()` in the first version?** It is the difference between a queue
   and a corridor (§6), it is cheap, and it changes `hospital-world`'s behaviour
   surface: a model can now decline an item without acting on it, which is a
   new behaviour to interpret and one the preregistered measurands do not name.
   In or out of the first package?
3. **Where the package lives.** `rntc/hospital-world` reads like a Hugging Face
   dataset repo, which would give us hashes, versioning and offline caching for
   free, and would publish the world, which is a decision about disclosure and
   not about engineering. A private git remote is the alternative. Yours.
4. How strict is "no domain word in the engine"? I wrote it as a kill
   condition, checked by grep. It forbids `dispense` but also `record` and
   `file`, which are ordinary English. I would keep the grep on a short list of
   clinical terms only, and rely on review for the rest.
5. Does VAGABOND gate the engine or every world? I have written it as
   every world, run in the gate, no allocation. That makes it a hard admission
   rung, and it means a world that fails it cannot be served at all, including
   worlds someone else writes later.
