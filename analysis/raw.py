"""Print complete raw records, one per cell.

Aggregates hide what matters. A passage builder that drops a section, a model
returning empty strings, an outcome label naming the opposite of what it
measures: none of these show up in a clean summary table, and all of them are
obvious in one full prompt and one full completion.

This prints the whole thing on purpose, with no truncation and no highlighting. Reading
it is the gate; a tool that pre-digests the record defeats the point.

Usage: uv run python -m analysis.raw <log dir> [--cell v1] [--per 1]
"""

from __future__ import annotations

import sys
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

RULE = "=" * 78


def show(sample, cell: str) -> None:
    print(f"\n{RULE}\ncell {cell}   sample {sample.id}   "
          f"epoch {sample.epoch}   limit {sample.limit}\n{RULE}")
    for message in sample.messages:
        print(f"\n--- {message.role} " + "-" * 60)
        print(message.text or "[pas de texte]")
        for call in (getattr(message, "tool_calls", None) or []):
            print(f"    -> {call.function}({call.arguments})")
    record = (sample.store or {}).get("tabib:record")
    if record:
        print(f"\n    record: {record}")
    for name, usage in (sample.model_usage or {}).items():
        print(f"    tokens: {name} out={usage.output_tokens} "
              f"reasoning={usage.reasoning_tokens}")


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    opt = lambda flag, default: (argv[argv.index(flag) + 1] if flag in argv else default)
    want, per = opt("--cell", None), int(opt("--per", 1))
    if not args:
        print("usage: raw <log dir> [--cell v1] [--per 1]")
        return 2

    seen: dict[str, int] = {}
    for info in list_eval_logs(str(Path(args[0]))):
        log = read_eval_log(info)
        cell = (log.eval.metadata or {}).get("cell", "?")
        if (want and cell != want) or not log.samples:
            continue
        for sample in log.samples:
            if seen.get(cell, 0) >= per:
                break
            seen[cell] = seen.get(cell, 0) + 1
            show(sample, cell)
    print(f"\n{sum(seen.values())} records over cells {sorted(seen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
