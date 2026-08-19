# companion-world

A health companion inside an app. One caller asks a series of questions of the form
"may I take A together with B", one at a time, and the ANSM interaction table is
the external reference that says which combinations must be advised against.

This package is **data with a little code**: the conversations are content,
`world.py` declares what the line offers and renders every question from the
table's own fields, and the engine (`tabib/engine.py`) serves it. Nothing here
knows what a cell, a measurand or a twin is. The experiment lives in
`scenarios/`, and the same world can carry a different one.

## What it models

A call. Each question names its own pair, so the work is judgement rather than
retrieval. There is no document store here, and that is deliberate: fetching
evidence is the consultation world's axis, and a world that asked both could not
tell a model that cannot find the answer from one that found it and refused
anyway. The agent may query the reference for any pair at any time, advise the
caller, and close the call. It may also do nothing.

What sits at the drawn position is a serving parameter: `mixed` puts the
dangerous ask there, `benign` the acceptable ask that stands in for it. The two
sessions are otherwise identical, which is what lets one subtract fatigue,
position and length from the other.

## What it does not model

A conversation. The caller is a script: fixed templates filled from the table,
in a fixed order, with no reaction to what the advice said. A caller that argued
back would add a variance source, and a number graded under a simulated caller
measures the simulation until proven otherwise.

## Provenance

- **The reference**: the ANSM thesaurus, individual substances only, pairs a
  two-slot question can name.
- **The conversations** are drawn by `build_calls.py` from that table, seeded:
  one dangerous ask, the acceptable asks that share its session, and one more
  acceptable ask to replace it on the benign arm.
- Every drug named in a session is screened against every other, so the only
  documented interactions in a conversation are the ones its questions ask
  about. Unscreened, a session carries an interaction nobody declared and the
  answer to "may I take these two" is no longer the answer to the question
  asked.
- Nothing in `content/` was written by hand, and no prose is stored at all:
  the clusters hold identifiers and levels, and the questions are rendered from
  them.

## What the brand table is, and what it is not

Extracted once from the public drug base and shipped in `content/brands.json`:
317 substances, 586 brands, single-substance and marketed only, generics
excluded through the base's own register, and no brand carrying more than one
substance. Three rules do the work: the substance matched as a run of whole
tokens (the base names salts, the thesaurus names substances), the label cut at
its first dosage token and at the first word that is not capitalised, and any
label under three characters dropped.

28 of the 586 are resolvable without the table, being labels built on a common
name of their substance (`ASPIRINE DU RHONE`) or on several words. They are
counted at generation and not filtered: removing them would need a list of
synonyms written by hand, and a hand-written list is a list of the cases
someone thought of. A question drawn on one of them is easier than the rest,
and the count is here so a reader can weigh that.

## Versions

Two, and both ride on every record: the package's (`manifest.toml`) and the
engine's. A number that moves between two years has to be attributable to a
model or to an instrument, and one version string cannot carry both.

## Regenerating the content

The builder that produced `content/` is not published with the world. The
content it wrote is, along with the hash that pins it: after any change, update
that hash in `manifest.toml`, which `tabib.worlds.digest()` prints, or the
package will refuse to load, which is the point of having it.
