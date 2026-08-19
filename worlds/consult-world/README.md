# consult-world

A consultation session. A practitioner asks about drug pairs, one question at a
time, and a store of monographs is reachable through three affordances: search,
read, answer. The ANSM interaction table is the external reference, and every
monograph states the level that table holds for its pair.

This package is **data with a little code**: the clusters are content,
`world.py` declares what the session offers and renders each monograph from the
table's own fields, and the engine (`tabib/engine.py`) serves it. Nothing here
knows what a cell, a measurand or a twin is. The experiment lives in
`scenarios/`, and the same world can carry a different one.

## What it models

A series of questions and an open store. The agent may search the store, read
any document at any moment, and answer the question on the table; answering is
what brings the next question. It may answer without reading, read without
answering, or do nothing at all, and the session ends in a state the world can
describe either way.

The measured pair of a cluster can be served three ways, and which one is a
parameter of `serve`, not a cell: `true` serves its own monograph, `flipped`
serves the monograph stating the twin level, `withheld` holds no document for it
at all. On `flipped` the affordance is `injected`, so the trace carries the
served body next to the true one.

## What it does not model

A conversation. The practitioner is a script: fixed templates filled from the
cluster, in a fixed order, with no reaction to what the answer said. A
language-model interlocutor adds a variance source, and a number graded under a
simulated practitioner measures the simulation until proven otherwise.

Nor does it model a monograph. Each document states a pair and a level and stops
there: an entry relabelled with its description left in asserts one level and
describes another, which is not an object a reference contains.

## Provenance

- **The reference**: the ANSM thesaurus, individual substances only, pairs a
  two-slot lookup can reach.
- **The clusters** are drawn by `build_store.py` from that table, seeded: the
  measured pairs from the two arms the corpus carries, the decor pairs from the
  other two levels, so no decor question is a second observation of the
  contrast.
- Nothing in `content/` was written by hand, and no prose is stored at all:
  the clusters hold identifiers and levels, and the text is rendered from them.

## Versions

Two, and both ride on every record: the package's (`manifest.toml`) and the
engine's. A number that moves between two years has to be attributable to a
model or to an instrument, and one version string cannot carry both.

## Regenerating the content

```sh
uv run python worlds/consult-world/build_store.py
```

Then update the hashes in `manifest.toml`, which `tabib.worlds.digest()` prints,
or the package will refuse to load, which is the point of having them.
