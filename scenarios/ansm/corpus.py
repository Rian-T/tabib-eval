"""The ANSM interaction table, shared by every scenario that reads it.

The reference belongs to no single scenario, so the loader lives beside the data
rather than inside whichever scenario needed it first.

Every passage served is official text, verbatim. A scenario may relabel an
entry's heading or serve only part of it, as long as it does the same thing in
every version it compares: what differs between two served versions is the
manipulation, and anything else that differs is a confound.

"""

from __future__ import annotations

import csv
import random
import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path

TRUTH = Path(__file__).parent / "truth" / "thesaurus_ansm.csv"

HEADING = {"CI": "CONTRE-INDICATION", "AD": "ASSOCIATION DÉCONSEILLÉE",
           "PE": "PRÉCAUTION D'EMPLOI", "APEC": "À PRENDRE EN COMPTE"}

def canon(name: str) -> str:
    """Comparable form of a substance name. Compare an identifier only through
    this function: a second normalisation written by hand beside it silently
    matches everything or nothing, and both look like a finding."""
    flat = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", flat.upper()).strip()


@dataclass(frozen=True)
class Entry:
    substance: str
    interactant: str
    level: str
    description: str
    conduite: str

    @property
    def pair_id(self) -> str:
        return "__".join(sorted((canon(self.substance), canon(self.interactant))))

    @property
    def keys(self) -> frozenset[str]:
        return frozenset((canon(self.substance), canon(self.interactant)))

    def passage(self, *, level: str | None = None, conduct: bool = True,
                heading: str | None = None, body: bool = True) -> str:
        """The entry as the reference prints it, optionally relabelled.

        `level` overrides the heading and nothing else, which is the whole
        manipulation a scenario needs to make a source state a level. `heading`
        overrides the same line with arbitrary text, so a placebo edits exactly
        where the manipulation edits and through the same builder.

        `body=False` keeps the pair and the heading and drops the prose. In this
        reference the heading **is** the level assignment and the description
        describes a mechanism, so a relabelled entry with its body left in is a
        document that asserts one level and describes another. That object does
        not exist in a real thesaurus, and serving it turns the question from
        "does the model follow this source" into "how does it resolve a
        self-contradiction". Dropping the body makes a relabelled entry a
        coherent claim, false or true, which is what a document can actually be.

        `conduct=False` drops only the conduct section, for the older reason:
        its mere presence predicts the level, 10% of contra-indications carry
        one against 100% of precautions.
        """
        lines = [f"{self.substance} + {self.interactant}",
                 heading or HEADING[level or self.level]]
        if body:
            lines.append(self.description)
            if conduct and self.conduite.strip():
                lines.append(f"Conduite à tenir : {self.conduite}")
        return "\n".join(lines)


def truncated(entry: "Entry") -> bool:
    """Text the extraction lost, usually across a page break.

    A passage cut mid-sentence is a malformed stimulus: whatever a model does
    with it measures the extraction rather than the model. These are excluded
    from the corpus rather than served, and `tests/test_corpus.py` holds the
    ceiling on how many the extraction is allowed to produce.
    """
    text = entry.description.strip()
    return bool(text) and (text[-1] not in '.!?)"' or text[0].islower())


@cache
def load() -> tuple[Entry, ...]:
    """Every well-formed entry, deduplicated on the pair. A pair listed twice at
    two levels has no single ground truth, so it is dropped rather than
    arbitrated."""
    rows = [Entry(r["substance"], r["interactant"], r["niveau"],
                  r["description"], r["conduite"])
            for r in csv.DictReader(TRUTH.open(encoding="utf-8"))]
    rows = [e for e in rows if not truncated(e)]
    levels: dict[str, set[str]] = {}
    for e in rows:
        levels.setdefault(e.pair_id, set()).add(e.level)
    seen, kept = set(), []
    for e in rows:
        if len(levels[e.pair_id]) > 1 or e.pair_id in seen:
            continue
        seen.add(e.pair_id)
        kept.append(e)
    return tuple(sorted(kept, key=lambda e: e.pair_id))


def sample(pool: tuple[Entry, ...], *, levels=("CI", "PE"), n: int,
           seed: int) -> list[Entry]:
    """A seeded draw, stratified by level. Taking the first n entries in corpus
    order would be a cluster sample: the table is alphabetical and international
    nonproprietary names share their roots by family."""
    out = []
    for level in levels:
        strat = sorted((e for e in pool if e.level == level), key=lambda e: e.pair_id)
        if len(strat) < n:
            raise ValueError(
                f"asked for {n} entries at level {level}, the corpus holds "
                f"{len(strat)}: a sample that quietly shrinks turns a declared "
                "sample size into a corpus ceiling nobody notices")
        rng = random.Random(f"{seed}:{level}")
        rng.shuffle(strat)
        out += strat[:n]
    return sorted(out, key=lambda e: e.pair_id)


# A class label names a family rather than a substance. The table lists 
# interactions against such families, so a pair of two concrete substances can be
# covered by an entry that names neither of them. Over-matching here is the safe
# direction: it only shrinks the set of pairs we are willing to call unlisted.
CLASS_LABEL = re.compile(
    r"\b(ANTI|INHIBITEURS|AGONISTES|ANTAGONISTES|MEDICAMENTS|MÉDICAMENTS|AUTRES|"
    r"SAUF|VACCINS|HORMONES|DERIVES|DÉRIVÉS|SUBSTRATS|INDUCTEURS|ALCALOIDES|"
    r"ALCALOÏDES|IMAO|AINS)\b|S\b")


def is_class_label(name: str) -> bool:
    return bool(CLASS_LABEL.search(name))


def one_term_each(entry: "Entry") -> bool:
    """Both names fit in one slot of a two-argument lookup.

    Some entries name a fixed combination, whose own name joins two substances
    with a plus, and some carry a parenthesised extrapolation clause. Rendered
    as `a + b`, the pair then shows three terms or a parenthesis, and no split
    into two slots reconstructs the key: the lookup returns nothing however
    correctly the caller spells it.

    Measured on a campaign that ran before this filter existed: 20% of the
    drawn pairs were unreachable this way, every failed lookup was one of them,
    and no simply-named pair ever failed. Those clusters entered a contrast
    delivered through the tool as a hard zero on the manipulated arm only.
    """
    return not any("+" in n or "(" in n
                   for n in (entry.substance, entry.interactant))


def names_individual(entry: "Entry") -> bool:
    """Both sides of the pair name a substance rather than a family.

    Weaker than `concrete_substances`, and deliberately so. To claim a pair is
    *absent* from the table one must rule out any family entry covering it. To
    use a pair the table *lists*, it is enough that a prescriber could submit
    it: an association between two therapeutic classes is not a dispensation.
    """
    return not (is_class_label(entry.substance) or is_class_label(entry.interactant))
