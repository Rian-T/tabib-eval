"""The brand table this world serves, extracted once from the public drug base.

A member of an app names the box, not the substance. This turns the public
database (BDPM) into one frozen table, substance to the brands that carry it
alone, which ships in `content/` with its hash. The database itself is never
read at serve time and never modified: an extraction that ran once and is
versioned is re-runnable in 2027; a lookup against a moving base is not.

Three rules, and each of them was paid for:

**Salt-aware matching.** The base names salts and hydrates ("ATORVASTATINE
CALCIQUE TRIHYDRATÉE"), the thesaurus names the substance. Compared for
equality, four drugs as ordinary as atorvastatin and dabigatran came back
absent from the whole database. The substance must appear as a run of whole
tokens inside the base's label: whole tokens so CODEINE does not match
DIHYDROCODEINE, a run so the salts are caught.

**A brand that names its own substance asks nothing.** "PARACETAMOL MYLAN"
resolves itself, so it is not a brand for this world's purposes.

**The label is cut at its first dosage token.** A member says "du Solupred",
not "du Solupred 20 mg".

    uv run python worlds/companion-world/build_brands.py

Then update the hash in `manifest.toml`.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scenarios.ansm import corpus

CONTENT = Path(__file__).parent / "content"
# read-only, and outside this repository on purpose: the extraction is a manual
# step whose output is versioned here. Point TABIB_BDPM at your own copy of the
# public BDPM export.
BDPM = Path(os.environ.get("TABIB_BDPM", Path.home() / "bdpm/raw"))

SOLD = "Commercialisée"
ACTIVE = "SA"
GENERIC = "1"          # the base's own type code for a generic
DOSAGE = re.compile(r"\d|%")


def _rows(name: str):
    with open(BDPM / name, encoding="latin-1") as fh:
        yield from (r for r in csv.reader(fh, delimiter="\t") if r)


def names(substance: str, label: str) -> bool:
    """Does `label` name `substance`, salts and hydrates included."""
    want, got = corpus.canon(substance).split(), corpus.canon(label).split()
    return any(got[i:i + len(want)] == want
               for i in range(len(got) - len(want) + 1))


def cut(label: str) -> str:
    """The name on the box: the upper-case run before the dosage.

    The base writes the brand in capitals and the form in lower case, so the
    case is where the name ends: "AMBISOME liposomal" is a brand and a form, and
    a member says "de l'Ambisome".
    """
    kept = []
    for word in label.split(",")[0].split():
        if DOSAGE.search(word) or not word.isupper():
            break
        kept.append(word)
    return " ".join(kept).strip()


def generics() -> set[str]:
    """The codes the base files as generics.

    A generic is named after its substance and its maker, "VITAMINE C ARROW",
    so it resolves itself the way a substance-named brand does. The base knows
    which ones they are, which is better than a list of laboratory names
    written here.
    """
    return {row[2] for row in _rows("CIS_GENER_bdpm.txt")
            if len(row) > 3 and row[3].strip() == GENERIC}


def build() -> dict[str, list[str]]:
    """Substance to the brands carrying it alone, over the whole thesaurus."""
    composition, label, sold = defaultdict(set), {}, {}
    for row in _rows("CIS_COMPO_bdpm.txt"):
        if len(row) > 6 and row[6].strip() == ACTIVE:
            composition[row[0]].add(row[3])
    for row in _rows("CIS_bdpm.txt"):
        if len(row) > 6:
            label[row[0]], sold[row[0]] = row[1].strip(), row[6].strip()

    wanted = {e.substance for e in corpus.load()} | {e.interactant
                                                     for e in corpus.load()}
    copies, out = generics(), defaultdict(set)
    for code, active in composition.items():
        if len(active) != 1 or sold.get(code) != SOLD or code in copies:
            continue
        brand, carried = cut(label.get(code, "")), next(iter(active))
        # a name of one or two characters is what the cut leaves of a label like
        # "A 313 200 000 UI POUR CENT": nothing a member could say
        if len(brand) < 3:
            continue
        for substance in wanted:
            if names(substance, carried) and not names(substance, brand):
                out[substance].add(brand)

    # a brand that resolves to two substances resolves to neither, and the rule
    # is written rather than the names: the first version excluded one label by
    # hand and two more survived it. A list of exceptions is a list of the cases
    # someone thought of
    owners = defaultdict(set)
    for substance, got in out.items():
        for brand in got:
            owners[brand].add(substance)
    shared = {b for b, s in owners.items() if len(s) > 1}
    print(f"{len(shared)} brands dropped for carrying more than one substance")
    # what survives that a model resolves for free: a label of one word-plus-a-
    # letter, or one built on a common name of the substance. Counted rather
    # than described, and not filtered: no hand-written synonym list
    trivial = sorted({b for got in out.values() for b in got
                      if b not in shared and (len(b.split()) > 2
                                              or any(len(w) == 1 for w in b.split()))})
    print(f"{len(trivial)} brands a reader may resolve without the table, e.g. "
          f"{trivial[:3]}")
    return {k: sorted(v - shared) for k, v in sorted(out.items())
            if v - shared}


if __name__ == "__main__":
    CONTENT.mkdir(exist_ok=True)
    blob = CONTENT / "brands.json"
    table = build()
    blob.write_text(json.dumps(table, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"{blob}: {len(table)} substances, "
          f"{sum(len(v) for v in table.values())} brands")
