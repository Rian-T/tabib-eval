"""What the campaign found: one table, one figure per scenario.

This is the other half of the rule the instrument answers to. `gate.py` says a
number is not an artefact; nothing here can say that, and nothing there can say
the number is worth having. A contrast that comes out at 0.02 on every model is
valid and teaches nothing, and the figure is what makes that visible in one
glance instead of in a paragraph.

So the figure shows the models side by side, with their intervals, on a shared
axis and a marked zero. Three readings are meant to be immediate: the effect is
there or it is not, the models differ or they do not, and a channel that should
show nothing shows nothing.

Saturation is printed rather than judged. A cell where every model sits against
the floor or the ceiling cannot teach anything at any sample size, and saying so
next to the number is more useful than a verdict that hides the number.

Usage: uv run python -m analysis.report <scenario> <log dir> [--svg out.svg]
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from analysis.collect import carry, degraded, records
from tabib import scenario as reg
from tabib.measurand import difference, dropped, gap, interval, values

PINNED = 0.05     # a cell this close to 0 or 1 on every model is saturated


def _pinned(m, rows: list[dict]) -> bool:
    """Every cell that ran sat against the floor or the ceiling on every model.

    Requires that something ran: a channel with no records is not a saturated
    channel, and printing it as one turns a control that was never executed
    into a finding about the models.
    """
    seen = False
    for cell in m.cells:
        for model in {r["model"] for r in rows}:
            ys = [float(m.y(r)) for r in rows
                  if r["model"] == model and r.get("cell") == cell
                  and (not m.where or m.where(r))]
            if not ys:
                continue
            seen = True
            if PINNED < sum(ys) / len(ys) < 1 - PINNED:
                return False
    return seen


def measure(sc, rows: list[dict]) -> list[dict]:
    """One line per (measurand, model): the number, its interval, and what
    would make it uninterpretable."""
    out = []
    for m in sc.measurands:
        for model in sorted({r["model"] for r in rows}):
            mine = [r for r in rows if r["model"] == model]
            got = values(m, mine)
            # rates get an interval too. They did not, and the two axes of the
            # figure are both rates: a dot drawn without one invites a ratio
            # between two models read to two digits, when a rate over fifty
            # clusters carries several hundredths of sampling error. The
            # resampling is over clusters either way, so nothing here is
            # specific to contrasts.
            point, lo, hi = interval(got) if got else (float("nan"),) * 3
            out.append({"measurand": m.name, "contrast": m.contrast, "model": model,
                        "point": point, "lo": lo, "hi": hi, "clusters": len(got),
                        "dropped": dropped(m, mine), "pinned": _pinned(m, mine)})
    return out


def compared(sc, rows: list[dict]) -> list[dict]:
    """The claim itself: one movement minus another, per model, with its band.

    A scenario that says "the tone moves the boundary as much as the fact" is
    claiming something about a difference, and a difference printed as two
    numbers in adjacent rows has no uncertainty attached to it.
    """
    by_name = {m.name: m for m in sc.measurands}
    out = []
    for left, right in sc.compares:
        for model in sorted({r["model"] for r in rows}):
            mine = [r for r in rows if r["model"] == model]
            kind, a, b = difference(by_name[left], by_name[right], mine)
            point, lo, hi = interval(a) if kind == "paired" else gap(a, b)
            out.append({"claim": f"{left} - {right}", "y": left, "x": right,
                        "model": model, "point": point, "lo": lo, "hi": hi,
                        "kind": kind, "clusters": len(a) + len(b),
                        "vy": interval(values(by_name[left], mine))[0],
                        "vx": interval(values(by_name[right], mine))[0]})
    return out


def differences(lines: list[dict]) -> None:
    for name in dict.fromkeys(x["claim"] for x in lines):
        kind = next(x["kind"] for x in lines if x["claim"] == name)
        print(f"\n{name}  (difference of two movements, {kind})")
        for x in (x for x in lines if x["claim"] == name):
            print(f"  {x['model'].split('/')[-1]:<28} {x['point']:+.3f}"
                  f"  [{x['lo']:+.3f}, {x['hi']:+.3f}]   {x['clusters']} clusters")


def positions(sc, rows: list[dict]) -> list[dict]:
    """Where each model sits on a declared pair of axes, and nothing more.

    The same panel as `compared`, without the difference: two rates that trade
    off against each other place a model, but their difference is partly a label
    prior and would carry an interval it has not earned.
    """
    by_name = {m.name: m for m in sc.measurands}
    rate = lambda m, mine: (sum(v for _, v in vs) / len(vs)
                            if (vs := values(m, mine)) else float("nan"))
    out = []
    for x, y in sc.plots:
        for model in sorted({r["model"] for r in rows}):
            mine = [r for r in rows if r["model"] == model]
            vx, vy = rate(by_name[x], mine), rate(by_name[y], mine)
            out.append({"claim": f"{y} against {x}",
                        "y": by_name[y].label or y,
                        "x": by_name[x].label or x,
                        "model": model, "point": vy, "vx": vx, "vy": vy,
                        "unit": True,
                        # No diagonal here. On two movements it is the null,
                        # where they are equal, and reading the figure is
                        # reading which side of it a model sits on. On two
                        # rates that trade off, x = y is not a null, not a
                        # frontier and not anything, and a dashed line drawn
                        # across the box is read as one of the three.
                        "diagonal": False,
                        "clusters": len(values(by_name[y], mine))})
    return out


def plane(claims: list[dict], path: Path) -> None:
    """One panel per declared comparison: each model a dot, the null a diagonal.

    The two movements go on the two axes, so the claim is a position rather than
    a number to hold in your head. The diagonal is where they are equal, where
    knowing the answer bought nothing, or where an unverifiable claim about the
    speaker moved the boundary as far as the clinical fact did. Distance from it
    is the difference reported above, and its sign is which side of the line the
    model sits on.

    Two axes and nothing else: how precise each position is lives in the table
    above, as the difference and its interval, and encoding it here again would
    buy a third channel on a figure whose whole point is having two.

    A model that produced no comparison at all is named under the panel rather
    than dropped. On a channel defined by what a model knew, having nothing to
    compare is a finding about that model (it never knew a pair) and it has
    no position on an axis that measures deference among pairs it knew. The one
    place it must not go is silently off the figure.
    """
    if not claims:
        return
    names = list(dict.fromkeys(c["claim"] for c in claims))
    side, pad, sep = 300, 54, 56
    # room for the longest label to the right of the last panel: a name clipped
    # at the edge of the image is a model the reader cannot identify
    room = 12 + 7 * max((len(c["model"].split("/")[-1]) for c in claims), default=0)
    w = pad + len(names) * (side + sep) + room
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{side + 120}" '
           f'font-family="system-ui,sans-serif" font-size="12">',
           f'<rect width="{w}" height="{side + 120}" fill="white"/>']
    for i, name in enumerate(names):
        mine = [c for c in claims if c["claim"] == name and c["point"] == c["point"]]
        absent = [c for c in claims if c["claim"] == name and c["point"] != c["point"]]
        if not mine:
            continue
        x0 = pad + i * (side + sep)
        top = 44
        # rates own their scale. Fitting the box to the models would make four
        # dots inside a tenth of a point look like a panel that separates them,
        # and separation is the one thing this figure is read for
        hi = 1.0 if mine[0].get("unit") else max(
            [0.2] + [abs(v) for c in mine for v in (c["vx"], c["vy"]) if v == v])
        px = lambda v: x0 + side * v / hi
        py = lambda v: top + side - side * v / hi
        out += [f'<text x="{x0}" y="{top - 24}" font-weight="600">{mine[0]["y"]}</text>',
                f'<text x="{x0}" y="{top - 8}" fill="#666">against {mine[0]["x"]}</text>',
                f'<rect x="{x0}" y="{top}" width="{side}" height="{side}" '
                f'fill="none" stroke="#ddd"/>',
                f'<text x="{x0 + side / 2:.0f}" y="{top + side + 34}" '
                f'text-anchor="middle" fill="#666">{mine[0]["x"]}</text>']
        if mine[0].get("diagonal", True):
            out += [f'<line x1="{px(0):.1f}" y1="{py(0):.1f}" x2="{px(hi):.1f}" '
                    f'y2="{py(hi):.1f}" stroke="#999" stroke-dasharray="4 3"/>']
        for t in (0.0, 0.5, 1.0) if mine[0].get("unit") else ():
            out += [f'<line x1="{px(t):.1f}" y1="{top + side}" x2="{px(t):.1f}" '
                    f'y2="{top + side + 4}" stroke="#999"/>',
                    f'<text x="{px(t):.1f}" y="{top + side + 16}" '
                    f'text-anchor="middle" fill="#666">{t:.1f}</text>',
                    f'<line x1="{x0 - 4}" y1="{py(t):.1f}" x2="{x0}" '
                    f'y2="{py(t):.1f}" stroke="#999"/>',
                    f'<text x="{x0 - 8}" y="{py(t) + 4:.1f}" text-anchor="end" '
                    f'fill="#666">{t:.1f}</text>']
        # labels are nudged apart when two models land close. Moving the dot
        # would move the result; moving the text only moves the text, and a
        # figure whose two closest models are the unreadable ones hides exactly
        # what it is read for
        placed: list[float] = []
        for c in sorted(mine, key=lambda c: c["vy"], reverse=True):
            cx, cy = px(c["vx"]), py(c["vy"])
            ty = cy + 4
            while any(abs(ty - p) < 13 for p in placed):
                ty += 13
            placed.append(ty)
            out += [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#0b6"/>',
                    f'<line x1="{cx + 5:.1f}" y1="{cy:.1f}" x2="{cx + 9:.1f}" '
                    f'y2="{ty - 4:.1f}" stroke="#bbb"/>',
                    f'<text x="{cx + 11:.1f}" y="{ty:.1f}" fill="#444">'
                    f'{c["model"].split("/")[-1]}</text>']
        for k, c in enumerate(absent):
            out.append(f'<text x="{x0}" y="{top + side + 36 + 14 * k}" fill="#b00">'
                       f'{c["model"].split("/")[-1]} : rien à comparer '
                       f'({c["clusters"]} clusters)</text>')
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path}")


def table(lines: list[dict]) -> None:
    for name in dict.fromkeys(x["measurand"] for x in lines):
        rows = [x for x in lines if x["measurand"] == name]
        kind = "contrast" if rows[0]["contrast"] else "rate"
        spread = max(x["point"] for x in rows) - min(x["point"] for x in rows)
        print(f"\n{name}  ({kind}, spread across models {spread:+.3f}"
              f"{', saturated' if all(x['pinned'] for x in rows) else ''})")
        for x in rows:
            band = f"  [{x['lo']:+.3f}, {x['hi']:+.3f}]"
            lost = f"  {x['dropped']} unpaired" if x["dropped"] else ""
            print(f"  {x['model'].split('/')[-1]:<28} {x['point']:+.3f}{band}"
                  f"   {x['clusters']} clusters{lost}")


def svg(lines: list[dict], path: Path) -> None:
    """A dot and interval per model, one panel per contrast, zero marked.

    Hand-written rather than plotted: one figure with no dependency is worth
    more to a reader cloning the repository than a prettier one they cannot run.
    """
    panels = [n for n in dict.fromkeys(x["measurand"] for x in lines)
              if any(x["contrast"] for x in lines if x["measurand"] == n)]
    rows = [x for x in lines if x["measurand"] in panels and x["point"] == x["point"]]
    if not rows:
        print("\nno figure: every contrast came back empty")
        return
    span = max([0.2] + [abs(v) for x in rows for v in (x["lo"], x["hi"], x["point"])
                        if v == v])
    w, left, lh, ph = 720, 250, 26, 34
    height = sum(lh * (1 + len([x for x in rows if x["measurand"] == p])) + ph
                 for p in panels) + 30

    def px(v):
        return left + (w - left - 40) * (v + span) / (2 * span)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{height}" '
           f'font-family="system-ui,sans-serif" font-size="13">',
           f'<rect width="{w}" height="{height}" fill="white"/>']
    y = 30
    for panel in panels:
        out.append(f'<text x="20" y="{y}" font-weight="600">{panel}</text>')
        y += 10
        mine = [x for x in rows if x["measurand"] == panel]
        top, bottom = y, y + lh * len(mine)
        out.append(f'<line x1="{px(0):.1f}" y1="{top}" x2="{px(0):.1f}" '
                   f'y2="{bottom}" stroke="#bbb"/>')
        for x in mine:
            y += lh
            name = x["model"].split("/")[-1]
            out.append(f'<text x="{left - 12}" y="{y + 4}" text-anchor="end" '
                       f'fill="#444">{name}</text>')
            if x["lo"] == x["lo"]:
                out.append(f'<line x1="{px(x["lo"]):.1f}" y1="{y}" '
                           f'x2="{px(x["hi"]):.1f}" y2="{y}" stroke="#333"/>')
            out.append(f'<circle cx="{px(x["point"]):.1f}" cy="{y}" r="4" '
                       f'fill="#0b6"/>')
            out.append(f'<text x="{w - 34}" y="{y + 4}" fill="#666">'
                       f'{x["point"]:+.2f}</text>')
        y += ph
    out.append(f'<text x="{px(0):.1f}" y="{height - 8}" text-anchor="middle" '
               f'fill="#888">0</text>')
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"\nwrote {path}")


def positional(argv: list[str]) -> list[str]:
    """Everything that is not a flag, nor the value of one.

    `--svg out.svg` puts a bare path in the argument list, and a bare path is
    indistinguishable from a log directory once several are allowed.
    """
    takes_value = {"--svg"}
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
        elif a.startswith("--"):
            skip = a in takes_value
        else:
            out.append(a)
    return out


def main(argv: list[str]) -> int:
    args = positional(argv)
    if len(args) < 2:
        print("usage: report <scenario> <log dir>... [--svg out.svg]")
        return 2
    importlib.import_module(f"scenarios.{args[0]}.scenario")
    sc = reg.get(args[0])
    # a run directory holds every scenario the campaign produced. The measurands
    # select by cell and the names are disjoint, so the numbers were right, but
    # anything counted over the whole file (cases, degraded, the act rate)
    # silently pooled two scenarios and one of them hid the other's attrition
    #
    # several directories, because a panel is one directory per model and the
    # parent that holds them also holds every other campaign ever run. Naming
    # each one is what keeps two campaigns from being averaged together.
    rows = [r for d in args[1:]
            for r in records(d, include_pilot="--pilot" in argv)
            if r.get("scenario") == args[0]]
    if not rows:
        print("no records: a claim run reports nothing until it has one")
        return 1
    for cell, key, name in sc.carries:
        carry(rows, cell=cell, key=key, as_=name)

    print(f"{len(rows)} cases, {len({r['cluster'] for r in rows})} clusters, "
          f"{len(degraded(rows))} degraded, "
          f"{sum(1 for r in rows if r.get("in_vocabulary") is False)} off-vocabulary")
    # a model that rarely commits an act is measured on the sessions where it
    # happened to follow the protocol, which is not a random subset of anything.
    # One model consults the reference and then answers in prose in 83% of its
    # sessions; its numbers came out on 15 clusters next to everyone else's 95,
    # and nothing on the line said so
    for model in sorted({r["model"] for r in rows}):
        mine = [r for r in rows if r["model"] == model]
        acted = sum(1 for r in mine if r.get("act") not in (None, "none"))
        flag = "   <- measured on a subset it selected itself" \
            if acted < 0.8 * len(mine) else ""
        print(f"  {model.split('/')[-1]:<28} commits an act "
              f"{acted / len(mine):.0%} of the time{flag}")
    lines = measure(sc, rows)
    table(lines)
    out = Path(argv[argv.index("--svg") + 1]) if "--svg" in argv else None
    if sc.compares:
        claims = compared(sc, rows)
        differences(claims)
        if out:
            plane(claims, out.with_suffix(".plane.svg"))
    if sc.plots and out:
        plane(positions(sc, rows), out.with_suffix(".axes.svg"))
    if "--svg" in argv:
        svg(lines, Path(argv[argv.index("--svg") + 1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
