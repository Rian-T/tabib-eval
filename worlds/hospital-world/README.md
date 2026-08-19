# hospital-world

A hospital pharmacy dispensation counter, served one file at a time, with the
ANSM interaction thesaurus as the external reference that says which
prescriptions must not be served.

This package is **data with a little code**: the queues and the clinical reports
are content, `world.py` declares what the counter offers, and the engine
(`tabib/engine.py`) serves it. Nothing here knows what a cell, a measurand or a
twin is. The experiment lives in `scenarios/`, and the same world can carry a
different one.

## What it models

A shift. Files arrive one at a time, each carrying a discharge report and one
prescribed pair. The agent may open the file in front of it, query the reference,
answer the file's administrative question, and close it by dispensing, opposing
or referring. It may also set a file down without deciding, with `next_file`, and it
may do nothing at all.

## What it does not model

Anything a pharmacist would recognise beyond that: no stock, no patient contact,
no prescriber to call back, no second opinion. The counter is narrow on purpose,
because every additional surface is a surface that leaks the exercise.

## Provenance

- **Clinical reports**: PARHAF (`HealthDataHub/PARHAF`), CC BY 4.0. Filtered to
  reports of 1200–3500 characters whose stated age appears exactly once, with any
  report mentioning a death removed, or a prescription "to dispense at discharge"
  for a patient the report declares dead gives a legitimate, non-interaction
  reason to oppose.
- **The reference**: the ANSM thesaurus, individual substances only, pairs a
  two-slot lookup can reach.
- **The prescriptions are injected by pipeline.** No file in this package is a
  real prescription, and nothing in `content/` was written by hand.

## Versions

Two, and both ride on every record: the package's (`manifest.toml`) and the
engine's. A number that moves between two years has to be attributable to a model
or to an instrument, and one version string cannot carry both.

## Regenerating the content

The pipeline lives with the scenario that first built it, which is kept out of
the published repository. After regenerating, update the hashes in
`manifest.toml`, which `tabib.worlds.digest()` prints, or the package will
refuse to load, which is the point of having them.
