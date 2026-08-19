"""One session, drawn: a marker moving among the stations it may call.

    uv run tabib view runs/<name>/<scenario> --sample 0

Every glyph comes from a property the world declares. The affordances are the
stations, the role each one carries decides its motif, the engine's trace says
where the marker stands and what is open, and the served text is the one speech
bubble. A property a world does not declare simply does not draw, so a world
with no roles, no collections and no served text degrades to named boxes around
an idle marker rather than to a broken screen.

Nothing new is recorded. This reads the trace the engine already writes and the
events Inspect already logs, which is also why it works on a finished run: the
replay is the reading tool for a session someone wants to watch happen.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# The budget, the same for every world. A scene that grows with the world is a
# scene that is unreadable on the world that needed it most.
STATIONS = 7        # beyond that, role-less affordances collapse into one
BUBBLE = 46         # characters of served text, one line
SIDE = 24           # the two side columns; a station panel is 22 wide
QUEUES = 2          # open items drawn; the rest is a counter

MOTIF = {"referential": "▤", "act": "▭", "tool": "□", "more": "…"}


@dataclass(frozen=True)
class Station:
    name: str
    role: str       # referential | act | tool | more


@dataclass(frozen=True)
class Frame:
    """One call: where the marker went, what it said, what was open."""
    turn: int
    at: str
    bubble: str
    open: tuple[str, ...]
    accepted: bool
    effect: str


def _record(sample) -> dict:
    return (sample.store or {}).get("tabib:record") or {}


def _acts(scenario: str | None) -> set[str]:
    """The names the scenario declares as acts, or nothing if it cannot be read.

    A station whose role cannot be established is drawn as a plain box, which is
    the floor of the display and not an error.
    """
    if not scenario:
        return set()
    try:
        module = importlib.import_module(f"scenarios.{scenario}.scenario")
    except Exception:
        return set()
    return {a.name for a in module.SCENARIO.acts}


def stations(sample, scenario: str | None) -> tuple[Station, ...]:
    """The affordances offered in this session, with the role each declares.

    The list comes from what the model was actually served, so a tool the world
    withheld is not drawn. Over the budget, role-less affordances collapse into
    one station: the reference and the acts are what the scene is read for.
    """
    offered: dict[str, None] = {}
    for event in sample.events:
        for tool in (getattr(event, "tools", None) or []):
            offered.setdefault(tool.name, None)
    record = _record(sample)
    referential = set(record.get("referential") or [])
    acts = _acts(scenario)
    role = lambda n: ("referential" if n in referential
                      else "act" if n in acts else "tool")
    drawn = [Station(n, role(n)) for n in offered]
    plain = [s for s in drawn if s.role == "tool"]
    if len(drawn) > STATIONS:
        keep = [s for s in drawn if s.role != "tool"]
        room = max(STATIONS - len(keep) - 1, 0)
        hidden = len(plain) - room
        drawn = keep + plain[:room] + [Station(f"{hidden} more tools", "more")]
    return tuple(drawn)


def frames(sample) -> list[Frame]:
    """One frame per tool call, in order.

    The engine's trace carries what a call concerned and what was open when it
    was made; Inspect's own tool event carries what came back. A call the trace
    does not hold, such as a world built without the engine or a name the world
    rejected, still draws, without the parts that do not exist.
    """
    trace = _record(sample).get("trace") or []
    out: list[Frame] = []
    for event in sample.events:
        if event.event != "tool":
            continue
        i = len(out)
        # paired by position, and only while the names agree: a skew between
        # the two lists must lose the extra detail, never move it onto the
        # wrong call
        row = trace[i] if i < len(trace) and trace[i][1] == event.function else None
        served = str(event.result or "").strip().replace("\n", " ")
        args = ", ".join(f"{k}={v}" for k, v in (event.arguments or {}).items())
        out.append(Frame(
            turn=row[0] if row else i + 1,
            at=event.function,
            bubble=(served or args)[:BUBBLE],
            open=tuple(row[5]) if row else (),
            accepted=bool(row[3]) if row else not event.error,
            effect=str(row[4]) if row else ""))
    return out


def _panel(station: Station, here: bool) -> Panel:
    body = Text(f"{MOTIF[station.role]}\n{station.name}", justify="center",
                style="bold" if here else "")
    return Panel(body, border_style="green" if here else "grey42", width=22)


def _cluster(items: list[Panel], per_row: int = 2) -> Group:
    """Panels laid out a couple to the line, so a row stays inside its column."""
    lines = []
    for start in range(0, len(items), per_row):
        grid = Table.grid(padding=(0, 1))
        row = items[start:start + per_row]
        for _ in row:
            grid.add_column()
        grid.add_row(*row)
        lines.append(grid)
    return Group(*lines) if lines else Group(Text(""))


def render(drawn: tuple[Station, ...], shots: list[Frame], k: int,
           header: str = "") -> Group:
    """The scene at frame `k`: reference above, acts below, the rest on the sides.

    Three columns of fixed width and three rows, so the centre stays the centre
    whatever a world declares. Placement follows the role alone: no world is
    laid out by hand, and a world with only plain boxes still gets a scene.
    """
    now = shots[k] if 0 <= k < len(shots) else None
    at = now.at if now else ""
    panel = lambda s: _panel(s, s.name == at)
    top = [panel(s) for s in drawn if s.role == "referential"]
    bottom = [panel(s) for s in drawn if s.role == "act"]
    rest = [s for s in drawn if s.role not in ("referential", "act")]
    half = (len(rest) + 1) // 2

    # a marker, not a character: it sits at the station of the current call and
    # in the centre before the session starts. The movement between stations is
    # what the scene says; drawing someone to do the moving says nothing more
    marker = Text(f"\n●\n{at or 'idle'}", justify="center", style="bold green")
    bubble = Text(now.bubble if now and now.bubble else "", style="italic")
    centre = Group(marker, Panel(bubble, width=BUBBLE + 4, border_style="grey42")
                   if now and now.bubble else Text(""))

    scene = Table.grid(padding=(0, 1))
    scene.add_column(width=SIDE, justify="center")
    scene.add_column(width=BUBBLE + 6, justify="center")
    scene.add_column(width=SIDE, justify="center")
    scene.add_row("", _cluster(top), "")
    scene.add_row(_cluster([panel(s) for s in rest[:half]], 1), centre,
                  _cluster([panel(s) for s in rest[half:]], 1))
    scene.add_row("", _cluster(bottom), "")

    opened = list(now.open) if now else []
    queue = ("open " + ", ".join(opened[:QUEUES])
             + (f" (+{len(opened) - QUEUES})" if len(opened) > QUEUES else "")
             if opened else "")
    counts: dict[str, int] = {}
    for shot in shots[:k + 1]:
        counts[shot.at] = counts.get(shot.at, 0) + 1
    status = Text(
        f"{header}  turn {now.turn if now else 0}  call {min(k + 1, len(shots))}"
        f"/{len(shots)}  {queue}\n"
        + "  ".join(f"{name} {n}" for name, n in counts.items()), style="grey62")
    return Group(scene, status)


def read(log_dir: str, index: int = 0):
    """(sample, scenario, model) for one session of a run directory or file."""
    from inspect_ai.log import list_eval_logs, read_eval_log

    logs = [str(log_dir)] if str(log_dir).endswith(".eval") else [
        info for info in list_eval_logs(str(log_dir))]
    for info in logs:
        log = read_eval_log(info)
        if log.samples:
            sample = log.samples[index % len(log.samples)]
            return (sample, (log.eval.metadata or {}).get("scenario"),
                    log.eval.model)
    raise SystemExit(f"no session to draw under {log_dir}")


def play(log_dir: str, *, index: int = 0, delay: float = 0.6) -> int:
    """Replay one finished session, one frame per call."""
    import time

    sample, scenario, model = read(log_dir, index)
    drawn, shots = stations(sample, scenario), frames(sample)
    # a part the log does not carry is left out, never filled with a literal
    header = " · ".join(p for p in (scenario, str(sample.id), model) if p)
    if not shots:
        print(render(drawn, shots, 0, header))
        return 0
    with Live(render(drawn, shots, 0, header), refresh_per_second=8) as live:
        for k in range(len(shots)):
            live.update(render(drawn, shots, k, header))
            time.sleep(delay)
    return 0
