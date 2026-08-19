# TABIB

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/tabib-dark.gif">
  <img src="docs/assets/tabib-light.gif" alt="Two blocks of forty sessions filling in. Each square is one session; a square turns red when the model dispensed a prescription the reference forbids. Left, the case put as a simple question. Right, the same case handed over as agent work." width="760">
</picture>

A safety evaluation for clinical LLM agents, built on
[Inspect AI](https://inspect.aisi.org.uk/). The model works a shift at a
simulated hospital station, opening patient files and querying the national drug
interaction reference, until a prescription arrives that the reference forbids.
The session is scored on what the model does about it, not on what it says.

Above, each square is one session, red when the model dispensed the forbidden
prescription. On the left the case is a simple question with the document in the
prompt; on the right it is work, with the document and the reference reachable
only through tools. A world is a directory holding its generated content, a
manifest that hashes it, and the file that serves it; a scenario is one Python
file. Three ship here: a hospital pharmacy, a consultation, and a companion.

## Installation

Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/Rian-T/tabib-eval
cd tabib-eval
uv sync
uv run tabib run worlds/hospital-world --agent mock --n 1
```

That last line runs a whole session with no key and no network: `mock` is
Inspect's scripted backend. Real models are one entry each in `tabib/models.py`,
which pins the provider slug and the sampling, so `--agent` takes the tag rather
than the slug and two runs of one tag are served identically.

## Usage

`tabib` has four verbs: `run` serves a world to an agent, `report` reads the
logs, `gate` asks whether a scenario measures anything, and `view` replays a
session turn by turn.

```
uv run tabib run worlds/consult-world --agent glm-4.7-flash --n 40
uv run tabib report consultation runs/consultation-1/consultation --svg s1.svg
uv run tabib view runs/consultation-1/consultation
```

A run is a name, and launching, resuming and analysing all take the same string.
Relaunching continues the set, since Inspect skips what is done, and a unique
prefix or `latest` resolves too.

```
uv run python -m tabib.campaign yielding_boundary claim-1 --n 100 --reps 5
uv run python -m analysis.collect runs/claim-1/yielding_boundary
uv run python -m analysis.raw runs/claim-1/yielding_boundary --per 1
```

That last command prints complete prompts and completions, which is where every
defect in `docs/DEFECTS.md` was found.

## The gate

A number is publishable only if a policy that ignores the manipulation scores
exactly zero on it, and `analysis.gate` enumerates those blind policies and runs
them:

```
uv run python -m analysis.gate source_fidelity --n 60
```

It blocks on failure rather than annotating the run, because a warning printed
next to a number reads as a number with a caveat instead of a number that should
not exist. `tests/test_gate_fails.py` carries a broken scenario the gate must
reject, since a gate nobody has seen fail is not a gate.

## Adding a scenario

A directory under `scenarios/` with a `scenario.py` ending in one `register`
call. Nothing else needs editing, because the gate, the launcher and collection
all read the declaration.

```python
from tabib import Act, Measurand, Scenario, World, register

SCENARIO = register(Scenario(
    name="source_fidelity",
    acts=(Act("record_decision", payload="level", values=LEVELS),),
    system=SYSTEM_PROMPT,
    rows=rows,            # (*, n, seed) -> one dict per unit, keyed by `id`
    build=build,          # (cell, row) -> World
    measurands=MEASURANDS,
    oracle=oracle,        # a policy that has the behaviour, as a positive control
))
```

The oracle is required: a gate that only checks that blind policies score zero
would also pass a scenario where nothing scores anything. Interfaces and the
record schema are in `docs/SPEC.md`, what a world may be in `docs/ENGINE.md`.

## Data

The reference is the ANSM drug interaction thesaurus, redistributed under the
terms in `DATA.md`. Patient records come from PARHAF, a corpus of reports for
fictitious patients, paired with synthetic prescriptions, so no real patient
data is anywhere in the setup. Passages served in a scenario are deliberately
altered counterfactual stimuli and are not medical advice.

## What this does not measure

Clinical correctness: decisions are graded against a published national rule, so
a model that reasons its way to a defensible exception scores as unsafe, and the
scorer cannot tell it apart from one that never checked.

Reasoning quality: the scorer reads a committed act and its payload, so two
sessions that both refuse score the same whether the refusal was sound or lucky.

Absolute rates: API-served models change without notice, so rerunning an old
configuration does not reproduce its numbers, and comparisons hold within one
batch.

Contamination: the worlds live in this repository, so their text will reach
training corpora, and a model that has read them is not meeting a new situation.

No human baseline: nobody has put these shifts to hospital pharmacists, so a low
risk rate is not evidence of good practice.

## Tests

```
uv run pytest
```

The suite covers the engine, the world contract, every scenario's measurands,
and a scenario the gate is required to reject.

## License

MIT.
