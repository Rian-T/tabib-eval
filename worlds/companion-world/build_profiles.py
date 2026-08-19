"""The profiles of the companion world, drawn from the ANSM table and written once.

One cluster is one user: a current treatment of a few drugs, and k additions the
user asks about. Each addition forms a documented pair with **exactly one** drug
of that treatment, which is the judgement the world asks for: the assistant is
told what the user takes and has to find which of it the new drug meets.

Everything else is screened out. No two profile drugs form a documented pair, no
addition meets a second profile drug, no two additions meet each other. A session
carries exactly as many documented interactions as it asks questions, and the
answer to "can I take this" is the answer to the question that was asked.

Feasibility, measured before this was written: with a profile of three drugs, 96
of the 97 usable contra-indicated pairs can carry a full session; with four, 97
of 97. The draw needs 40.

    uv run python worlds/companion-world/build_profiles.py

Then update the hash in `manifest.toml`, `tabib.worlds.digest()` prints it.
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scenarios.ansm import corpus

CONTENT = Path(__file__).parent / "content"
SEED = 20260801

DANGEROUS, ACCEPTABLE = "CI", "APEC"
CLUSTERS = 40
ASKS = 6               # k, fixed
PROFILE = 4            # drugs in the current treatment
TRIES = 60             # draws per cluster before this pair is given up on
# [A1] the two middle slots only, so every session has at least two acceptable
# additions on each side of the dangerous one
POSITIONS = (2, 3)


def brands() -> dict[str, list[str]]:
    """The frozen brand table, as `build_brands.py` wrote it."""
    return json.loads((CONTENT / "brands.json").read_text(encoding="utf-8"))


def table() -> tuple[dict, dict, set]:
    """Neighbours by level, display names, and every pair the reference lists.

    The graph is keyed on `canon` and the display name kept beside it: an
    identifier is compared through one function, and what the user reads is the
    reference's own spelling.
    """
    usable = [e for e in corpus.load()
              if corpus.one_term_each(e) and corpus.names_individual(e)]
    neighbours = defaultdict(lambda: defaultdict(set))
    names = {}
    for entry in usable:
        a, b = corpus.canon(entry.substance), corpus.canon(entry.interactant)
        neighbours[a][entry.level].add(b)
        neighbours[b][entry.level].add(a)
        names.setdefault(a, entry.substance)
        names.setdefault(b, entry.interactant)
    return neighbours, names, {e.keys for e in corpus.load()}


def positions(rng: random.Random) -> list[int]:
    if CLUSTERS % len(POSITIONS):
        raise ValueError(f"{CLUSTERS} clusters over {len(POSITIONS)} positions "
                         "does not divide: a short stratum is a position seen "
                         "less often than the design says it is")
    out = [p for p in POSITIONS for _ in range(CLUSTERS // len(POSITIONS))]
    rng.shuffle(out)
    return out


def draw(carrier: str, danger: str, graph: dict, listed: set, named: set,
         rng: random.Random):
    """One profile and its acceptable additions, or None if this draw failed.

    `carrier` is the profile drug the dangerous addition meets. The profile
    grows with drugs that meet nothing already in it, then the additions come
    from its neighbourhood, each kept only if it meets exactly one profile drug
    and none of the additions already drawn.
    """
    def linked(x, y):
        return frozenset((x, y)) in listed

    if danger not in named:
        return None                    # the member names a box, or nothing
    profile = [carrier]
    pool = [k for k in graph if k not in (carrier, danger) and graph[k][ACCEPTABLE]]
    rng.shuffle(pool)
    for candidate in pool:
        if len(profile) >= PROFILE:
            break
        if linked(candidate, danger) or any(linked(candidate, p) for p in profile):
            continue
        profile.append(candidate)
    if len(profile) < PROFILE:
        return None

    adds, carried = [], defaultdict(int)
    carried[carrier] = 1                       # the dangerous addition meets it
    candidates = sorted({c for p in profile for c in graph[p][ACCEPTABLE]})
    rng.shuffle(candidates)
    # spread over the profile, one carrier at a time before any takes a second.
    # Left to the neighbourhood sizes, five of six additions met the same drug,
    # and the identification the world asks for would be "find it once, then
    # answer with it" rather than a judgement made per question
    for cap in range(1, ASKS + 1):
        for candidate in candidates:
            if len(adds) >= ASKS:
                break
            if candidate in profile or candidate == danger:
                continue
            if candidate not in named or any(candidate == a for a, _ in adds):
                # every question of the member is in brand form, the measured
                # one included: a single brand-named question among
                # substance-named ones would mark the measured item by its
                # register, and a sample whose structure carries signal is a
                # defect of its own
                continue
            met = [p for p in profile if linked(candidate, p)]
            if len(met) != 1 or carried[met[0]] >= cap:
                continue
            # against the dangerous addition too: it is in the session even
            # though it is not in `adds` yet, and an acceptable addition that
            # meets it puts a second documented pair in the conversation. The
            # independent check on the shipped content is what found this
            if linked(candidate, danger) or any(linked(candidate, a)
                                                for a, _ in adds):
                continue
            adds.append((candidate, met[0]))
            carried[met[0]] += 1
        if len(adds) >= ASKS:
            break
    return (profile, adds) if len(adds) >= ASKS else None


def pick(substance: str, table_: dict, rng: random.Random) -> str:
    """One brand for a substance, drawn once and written into the content.

    Chosen here rather than at serve time: a world that picked a brand while
    serving would serve a different question on a re-run, and the twin cell
    would not be a twin.
    """
    got = table_[substance]
    return got[rng.randrange(len(got))]


def mentioned(taken: set, graph: dict, listed: set, named: set,
              rng: random.Random):
    """[A6] a drug the member mentions, and the addition it forbids.

    The aside is never a question: it names a drug the member was given, and a
    later question asks about something that meets it. Neither may meet anything
    else in the session, so the only interaction the aside creates is the one
    the design declares.
    """
    def linked(x, y):
        return frozenset((x, y)) in listed

    pool = [k for k in graph if graph[k][DANGEROUS]]
    rng.shuffle(pool)
    for aside in pool:
        if aside in taken or aside not in named or any(linked(aside, t)
                                                       for t in taken):
            continue
        for hidden in sorted(graph[aside][DANGEROUS]):
            if hidden in taken or hidden not in named:
                continue
            if any(linked(hidden, t) for t in taken):
                continue
            return aside, hidden
    return None


def build() -> list[dict]:
    graph, names, listed = table()
    by_canon = {corpus.canon(k): v for k, v in brands().items()}
    # keyed on canon, like the graph: the brand table is written under the
    # thesaurus's own spelling and compared through one function
    named = {corpus.canon(s) for s in brands()}
    dangerous = sorted({(corpus.canon(e.substance), corpus.canon(e.interactant))
                        for e in corpus.load()
                        if e.level == DANGEROUS and corpus.one_term_each(e)
                        and corpus.names_individual(e)})
    rng = random.Random(f"{SEED}:{DANGEROUS}")
    rng.shuffle(dangerous)
    where, out, failed = positions(rng), [], 0

    for pair in dangerous:
        if len(out) == CLUSTERS:
            break
        here = random.Random(f"{SEED}:{len(out)}")
        got = None
        # either side of the pair may be the drug the user already takes
        for carrier, danger in (pair, pair[::-1]):
            for _ in range(TRIES):
                got = draw(carrier, danger, graph, listed, named, here)
                if got:
                    break
            if got:
                break
        if not got:
            failed += 1
            continue
        profile, adds = got
        at = where[len(out)]
        asks = [{"addition": names[a], "with": names[p], "level": ACCEPTABLE,
                  "brand": pick(a, by_canon, here)} for a, p in adds[:ASKS - 1]]
        asks.insert(at, {"addition": names[danger], "with": names[carrier],
                         "level": DANGEROUS,
                         "brand": pick(danger, by_canon, here)})
        # drawn before the aside touches the generator: the [A5] cells must come
        # out of a re-run byte for byte, or adding a cell would silently move
        # the campaign that is already running
        spare = {"addition": names[adds[-1][0]], "with": names[adds[-1][1]],
                 "level": ACCEPTABLE, "brand": pick(adds[-1][0], by_canon, here)}
        taken = {corpus.canon(p) for p in profile} | {a for a, _ in adds}
        taken |= {corpus.canon(danger)}
        got_aside = mentioned(taken, graph, listed, named, here)
        if not got_aside:
            failed += 1
            continue
        aside, hidden = got_aside
        out.append({"cluster": f"C-{len(out):02d}", "at": at,
                    # [A6] the drug said in passing, and the addition that meets
                    # it. `aside_at` carries the mention, `hidden_at` the
                    # innocent question, with a question between them
                    "aside": {"drug": names[aside],
                              "brand": pick(aside, by_canon, here),
                              "addition": names[hidden],
                              "brand_addition": pick(hidden, by_canon, here)},
                    "aside_at": 0, "hidden_at": 2 if at != 2 else 3,
                    "profile": [names[p] for p in profile], "asks": asks,
                    "replacement": spare})
    if len(out) < CLUSTERS:
        raise ValueError(
            f"only {len(out)} of {CLUSTERS} clusters could be drawn: the table "
            f"cannot carry a profile of {PROFILE} drugs with {ASKS} additions "
            "each meeting exactly one of them. A campaign that quietly runs "
            "fewer clusters is not the campaign the design declares")
    print(f"{failed} contra-indicated pairs could not carry a session")
    return out


if __name__ == "__main__":
    CONTENT.mkdir(exist_ok=True)
    blob = CONTENT / "profiles.json"
    rows = build()
    blob.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"{blob}: {len(rows)} clusters")
