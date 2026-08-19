"""What the records look like, without looking at what they say.

`raw.py` prints whole prompts and completions and reading it is the gate. This
is the half of that gate which needs no domain values: shapes, counts, lengths,
and the order of tool calls. It catches the class of defect that shows up as a
cell being *structurally* different from its neighbours, which is the class that
produced defects 1, 2 and 10.

The one number worth the file on its own is the served length per cell. Two
cells of a contrast must differ in what they state and in nothing else; a cell
that is systematically longer or shorter than the one it is differenced against
carries a cue no measurand can see, and the difference is then partly ours.

Prints no served text, no completion, no substance, no thesaurus line.

Usage: uv run python -m analysis.shape <log dir> [--pilot]
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from statistics import fmean, median

from inspect_ai.log import list_eval_logs, read_eval_log


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    served: dict[tuple, list[int]] = defaultdict(list)
    turns: dict[tuple, list[int]] = defaultdict(list)
    said: dict[tuple, list[int]] = defaultdict(list)
    status: Counter = Counter()
    acts: dict[tuple, Counter] = defaultdict(Counter)
    order: dict[tuple, Counter] = defaultdict(Counter)
    empty: dict[tuple, int] = defaultdict(int)

    for info in list_eval_logs(str(args[0])):
        log = read_eval_log(info)
        if log.status != "success" or not log.samples:
            continue
        meta = log.eval.metadata or {}
        if meta.get("mode") == "pilot" and "--pilot" not in argv:
            continue
        key = (log.eval.model.split("/")[-1], meta.get("cell"))
        for sample in log.samples:
            record = (sample.store or {}).get("tabib:record") or {}
            messages = sample.messages or []
            # the first user turn is what the cell serves
            first = next((m for m in messages if getattr(m, "role", "") == "user"), None)
            if first is not None:
                served[key].append(len(first.text or ""))
            turns[key].append(len(messages))
            status[(key, record.get("status"))] += 1
            acts[key][record.get("act") or record.get("payload") or "none"] += 1
            calls = [c.function for m in messages
                     for c in (getattr(m, "tool_calls", None) or [])]
            order[key][" > ".join(calls) or "aucun appel"] += 1
            # A turn that is a tool call has no prose and that is correct, so
            # counting every empty text as an empty completion reports the
            # normal case as an alarm. This file did, on its first run, at
            # 13 766. What defect 2 was about is a turn that produced *neither*
            # text nor a call: the model spent its budget reasoning and emitted
            # nothing, which reads downstream as an abstention.
            assistants = [m for m in messages
                          if getattr(m, "role", "") == "assistant"]
            said[key] += [len(m.text or "") for m in assistants]
            empty[key] += sum(1 for m in assistants
                              if not (m.text or "")
                              and not (getattr(m, "tool_calls", None) or []))

    cells = sorted({k[1] for k in served})
    models = sorted({k[0] for k in served})

    print("\nlongueur du premier tour servi, en caracteres")
    print(f"{'cellule':<14}" + "".join(f"{m[:14]:>16}" for m in models))
    for cell in cells:
        row = f"{cell:<14}"
        for m in models:
            v = served.get((m, cell), [])
            row += f"{median(v):>16.0f}" if v else f"{'-':>16}"
        print(row)
    print("  Deux cellules d'un meme contraste doivent differer par ce qu'elles")
    print("  annoncent et par rien d'autre. Un ecart de longueur systematique est")
    print("  un indice servi que nos mesurandes ne voient pas.")

    print("\ntours par session, mediane")
    print(f"{'cellule':<14}" + "".join(f"{m[:14]:>16}" for m in models))
    for cell in cells:
        row = f"{cell:<14}"
        for m in models:
            v = turns.get((m, cell), [])
            row += f"{median(v):>16.0f}" if v else f"{'-':>16}"
        print(row)

    print("\ncaracteres ecrits par le modele, moyenne par tour")
    print(f"{'cellule':<14}" + "".join(f"{m[:14]:>16}" for m in models))
    for cell in cells:
        row = f"{cell:<14}"
        for m in models:
            v = said.get((m, cell), [])
            row += f"{fmean(v):>16.0f}" if v else f"{'-':>16}"
        print(row)

    bad = {k: v for k, v in empty.items() if v}
    print(f"\ncompletions vides : {sum(bad.values())}"
          + (f"  {sorted(bad.items())[:6]}" if bad else ""))

    off = [(k, n) for (k, s), n in status.items() if s not in (None, "acted",
                                                              "answered")]
    print(f"statuts autres qu'acted/answered : {sum(n for _, n in off)}"
          + (f"  {off[:6]}" if off else ""))

    print("\nsequences d'appels d'outils les plus frequentes, par modele")
    for m in models:
        seen: Counter = Counter()
        for (mm, _), c in order.items():
            if mm == m:
                seen.update(c)
        top = "  ".join(f"[{k}] {n}" for k, n in seen.most_common(3))
        print(f"  {m:<22} {top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
