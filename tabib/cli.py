"""One console script over the three verbs and the two readers.

    tabib run <package> --agent dev --n 2
    tabib report <scenario> <log dir> [--svg out.svg]
    tabib gate <scenario> [--n 30]
    tabib view <log dir> [--sample 0] [--delay 0.6]

Each subcommand is a thin call on what already exists. The ladder (`climb`) is
not here: its runner is not part of the published package, and a subcommand
that only prints where the runner is not would be worse than its absence.
"""

from __future__ import annotations

import sys

USAGE = __doc__.split("\n\n")[1]


def _run(argv: list[str]) -> int:
    import argparse

    from . import api

    p = argparse.ArgumentParser(prog="tabib run")
    p.add_argument("package", help="a world package: a name, owner/name, or a path")
    p.add_argument("--agent", default="dev", help="model tags, comma separated")
    p.add_argument("--cells", default="", help="cells to serve; the protocol's own by default")
    p.add_argument("--n", type=int, default=150)
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--mode", choices=("pilot", "claim"), default="pilot")
    p.add_argument("--name", default=None, help="run name; resuming takes the same one")
    args = p.parse_args(argv)

    world = api.load(args.package)
    result = api.run(agent=args.agent.split(","), world=world,
                     cells=tuple(c for c in args.cells.split(",") if c) or None,
                     repetitions=args.reps, n=args.n, mode=args.mode,
                     name=args.name)
    return 0 if result["complete"] else 1


def _view(argv: list[str]) -> int:
    import argparse

    from . import scene

    p = argparse.ArgumentParser(prog="tabib view")
    p.add_argument("log_dir")
    p.add_argument("--sample", type=int, default=0)
    p.add_argument("--delay", type=float, default=0.6)
    args = p.parse_args(argv)
    return scene.play(args.log_dir, index=args.sample, delay=args.delay)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else ""
    if command == "run":
        return _run(argv[1:])
    if command == "view":
        return _view(argv[1:])
    if command in ("report", "gate"):
        # the two readers own their own argument handling, and duplicating it
        # here is how the script and the module start disagreeing
        module = __import__(f"analysis.{command}", fromlist=["main"])
        return module.main(argv[1:])
    print(USAGE)
    return 0 if command in ("", "-h", "--help") else 2


if __name__ == "__main__":
    raise SystemExit(main())
