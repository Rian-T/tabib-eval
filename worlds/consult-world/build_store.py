"""The document store's clusters, drawn from the ANSM table and written once.

One cluster is one measured pair plus the decor pairs a session also asks about.
The measured pairs are drawn from the two arms the corpus carries and never
pooled; the decor is drawn from the other two levels, so no decor question is a
second observation of the contrast.

Nothing here writes prose. The clusters hold identifiers and levels, and
`world.py` renders every monograph from them: a document that no hand ever
touched cannot disagree with the table it comes from.

    uv run python worlds/consult-world/build_store.py

Then update the hashes in `manifest.toml`, `tabib.worlds.digest()` prints them.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scenarios.ansm import corpus

CONTENT = Path(__file__).parent / "content"
SEED = 20260801

ARMS = ("CI", "APEC")
DECOR = ("AD", "PE")
CLUSTERS = 40          # per arm; 24 was first built and is too few for R4
QUESTIONS = 4          # k, fixed and small; the horizon sweep is future work


def pool(levels: tuple[str, ...]) -> list[corpus.Entry]:
    """Entries a two-slot lookup can reach and a prescriber could submit."""
    return [e for e in corpus.load()
            if e.level in levels and corpus.one_term_each(e)
            and corpus.names_individual(e)]


def documented() -> set[frozenset]:
    """Every pair the reference lists, whichever way round it is written.

    The whole table, not the drawable subset: a pair we would never serve as a
    question is still an interaction a vignette must not put on the same
    patient.
    """
    return {e.keys for e in corpus.load()}


def interacts(substance: str, other: str, table: set[frozenset]) -> bool:
    return frozenset((corpus.canon(substance), corpus.canon(other))) in table


def doc(entry: corpus.Entry, index: int) -> dict:
    return {"id": f"MON-{index:04d}", "substance": entry.substance,
            "interactant": entry.interactant, "level": entry.level}


def positions(rng: random.Random) -> list[int]:
    """Where the measured question sits, the same number of times per position.

    Drawn per cluster, the position came out 10/7/15/8 on one arm against
    12/6/7/15 on the other, so position and arm were confounded on an axis read
    per arm. Stratified, the marginal is flat by construction and the shuffle
    keeps the position from tracking the order pairs were drawn in.
    """
    if CLUSTERS % QUESTIONS:
        raise ValueError(f"{CLUSTERS} clusters over {QUESTIONS} positions does "
                         "not divide: a stratum that is short is a position "
                         "under-represented on one arm and nowhere else")
    out = [i for i in range(QUESTIONS) for _ in range(CLUSTERS // QUESTIONS)]
    rng.shuffle(out)
    return out


def decor_for(entry: corpus.Entry, decor: list[corpus.Entry],
              rng: random.Random, table: set[frozenset]) -> tuple[list, int]:
    """The decor pairs of one cluster, none of them interacting with the addition.

    In the case form the decor's substances are the patient's current treatment,
    beside the measured pair's own substance, and the measured interactant is
    the drug being added. Two documented interactions must not meet on one
    patient:

    - a decor substance paired with the drug being added leaves "this pair"
      without a single answer, and the question stops being well posed;
    - two drugs of the treatment paired with each other distract unequally from
      one cluster to the next, which lands in the naked-against-case comparison
      as a difference between clusters rather than between forms.

    The measured pair itself is the one documented interaction the vignette
    carries, and it is why the question has an answer.

    Returns the drawn decor and how many candidates were skipped, so the count
    is printed rather than assumed to be zero.
    """
    order = list(decor)
    rng.shuffle(order)
    treatment, added = [entry.substance], entry.interactant
    out, skipped = [], 0
    for candidate in order:
        if len(out) == QUESTIONS - 1:
            break
        name = candidate.substance
        # a drug listed twice on one patient reads as a mistake in the vignette
        # rather than as a treatment, so a repeat is skipped like an interaction
        if (corpus.canon(name) in {corpus.canon(t) for t in treatment}
                or interacts(name, added, table)
                or any(interacts(name, t, table) for t in treatment)):
            skipped += 1
            continue
        out.append(candidate)
        treatment.append(name)
    if len(out) < QUESTIONS - 1:
        raise ValueError(
            f"{entry.substance} + {added}: the decor pool cannot fill a "
            f"vignette without a second documented interaction ({len(out)} of "
            f"{QUESTIONS - 1}). A draw that quietly returns fewer questions is "
            "a cluster that is not the cluster the design declares")
    return out, skipped


def build() -> list[dict]:
    ids = {e.pair_id: i for i, e in enumerate(corpus.load())}
    decor, table = pool(DECOR), documented()
    out, redrawn = [], 0
    for arm in ARMS:
        measured = pool((arm,))
        rng = random.Random(f"{SEED}:{arm}")
        rng.shuffle(measured)
        where = positions(rng)
        for n, entry in enumerate(measured[:CLUSTERS]):
            here = random.Random(f"{SEED}:{arm}:{n}")
            others, skipped = decor_for(entry, decor, here, table)
            redrawn += skipped
            docs = [doc(e, ids[e.pair_id]) for e in others]
            at = where[n]
            docs.insert(at, doc(entry, ids[entry.pair_id]))
            out.append({"cluster": f"{arm}-{n:02d}", "arm": arm,
                        "measured": docs[at]["id"], "docs": docs})
    print(f"{redrawn} decor candidates skipped: they interact with the drug "
          "their cluster adds, or with another drug of the same treatment")
    return out


if __name__ == "__main__":
    CONTENT.mkdir(exist_ok=True)
    blob = CONTENT / "clusters.json"
    rows = build()
    blob.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"{blob}: {len(rows)} clusters")
