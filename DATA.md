# Data provenance and reuse

## Source

Ground truth comes from the **Thésaurus des interactions médicamenteuses**
published by the **ANSM** (Agence nationale de sécurité du médicament et des
produits de santé), edition of **August 2023**, retrieved from
<https://ansm.sante.fr/documents/reference/thesaurus-des-interactions-medicamenteuses-1>.

`scenarios/ansm/truth/thesaurus_ansm.csv` is a mechanical
extraction of that PDF, produced by `truth/extract_thesaurus.py`. Interaction
levels, descriptions and conduct text are reproduced verbatim; no clinical
content was authored, summarised or edited by this project.

## Reuse terms

ANSM does not publish this document under an open licence. Its legal notice
places reuse under articles L. 321-1 and following of the French *code des
relations entre le public et l'administration*: the information must not be
altered, its meaning must not be distorted, and its source and last update
date must be cited. This file is that citation.

## Deliberately falsified variants: read this before using any output

TABIB measures whether a model's decision depends on the source it is given.
To do that it **serves altered passages on purpose**: severity headers are
swapped, and whole blocks are transplanted between entries. These variants are
generated at run time and are never stored in this repository, but they do
appear inside published `.eval` logs.

Any passage in a TABIB log carrying a version other than `A` or `A_copy` is a
counterfactual stimulus. **It is false by construction and must never be read
as medical reference.** The unmodified table is the file named above; nothing
else in this repository or in its logs is authoritative.

This alteration exists solely to measure model behaviour, is labelled as such
in every record, and is not a representation of ANSM's position.
