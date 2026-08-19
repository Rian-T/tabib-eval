"""The engine's size ceiling, computed rather than asserted by hand.

`docs/ENGINE.md` used to print the numbers. It got them wrong three times, and
every time in the direction that flattered the engine, subtracting blank lines
inside docstrings twice, comparing non-blank lines on one side against raw lines
on the other, and quoting a replaced-code figure that was 184 lines stale. A
budget kept by hand is a budget that drifts towards whoever is spending it.

So the count lives here, it runs on every commit, and the page cites the test.
Counting is by `tokenize`, which is the tokenizer the interpreter uses: a
docstring is a string expression statement, a comment is a comment token, and
neither is code. Nothing about that is a judgement call, which is the point.
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# What the engine is. VAGABOND and the loader are in it: the engine ships them
# and every world submits to them, which outweighs their never running during a
# campaign. The perimeter is not renegotiable after a count, redefining it a
# third time would retire the guard more thoroughly than any overrun.
ENGINE = ("tabib/engine.py", "tabib/vagabond.py", "tabib/measures.py",
          "tabib/worlds.py")

# What it replaces: one world's worth of scenario, as it stood before. It lives
# in `archive/`, which is kept out of the published repository: the comparison
# is a guard for whoever works on the engine, and it cannot run without the code
# it measures against. Absent, the whole module skips rather than fails, because
# a red test on a fresh clone says the instrument is broken when it is not.
REPLACED = ("archive/scenarios_v2_20260801/long_shift/scenario.py",
            "archive/scenarios_v2_20260801/long_shift/build_queue.py")

pytestmark = pytest.mark.skipif(
    not all((ROOT / name).exists() for name in REPLACED),
    reason="archive/ is not part of the published repository",
)

# Raised from 350 to 380 to 420, each time naming the demonstrated defects that
# pushed it: the review's first repair round (a world writing the engine's
# records, a world where nothing can be done, `WHERE` shipped with `GENERIC`, a
# rate above 1.0), then its second (a consultation credited to the wrong item, a
# trace protected against appends but not rewrites). A ceiling raised for comfort
# is dead where it stands; raised for a proven guard, it has done its work.
CEILING = 420


def executable(path: Path) -> int:
    """Lines carrying code: not blank, not a comment, not inside a docstring."""
    src = path.read_text(encoding="utf-8")
    code: set[int] = set()
    docs: set[int] = set()
    # a string is a docstring when it *opens* a statement. Tracking that means
    # remembering the last token including the ones we do not count, which the
    # first version of this function did not: so every docstring after a
    # newline read as code and the engine measured 583 instead of 402. A counter
    # that has never been checked against a second method is a number, not a
    # measurement, hence `test_the_counter_matches_a_second_method` below.
    opening = True
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        # NEWLINE ends a statement; NL is a line break that does not, inside
        # brackets, between the parts of a wrapped call. Treating NL as a
        # statement boundary made every continuation string look like a
        # docstring, which is how the first counter reported 583 and the second
        # 386 for the same files. Only the three that really open a statement.
        if tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            opening = True
            continue
        if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.ENDMARKER,
                        tokenize.ENCODING):
            continue
        span = range(tok.start[0], tok.end[0] + 1)
        if tok.type == tokenize.STRING and opening:
            docs.update(span)
        else:
            code.update(span)
        opening = False
    return len(code - docs)


def total(paths) -> int:
    return sum(executable(ROOT / p) for p in paths)


def test_the_engine_fits_under_its_ceiling():
    got = total(ENGINE)
    assert got <= CEILING, (
        f"the engine is {got} executable lines against a ceiling of {CEILING}. "
        "Do not trim a guard to fit: raise the ceiling and name the demonstrated "
        "defect the extra lines repair, or stop.")


def test_the_engine_is_smaller_than_what_it_replaces():
    """The clause that carries the intention, and the one that matters.

    The ceiling is a proxy; this is the thing the proxy stands for, and it is
    measured in one unit on both sides, which is what went wrong every time this
    was done by hand.
    """
    engine, replaced = total(ENGINE), total(REPLACED)
    assert engine < replaced, (
        f"engine {engine} against replaced {replaced}: an abstraction that costs "
        "more than the code it carries is a failed abstraction")


def test_a_world_costs_a_fraction_of_a_scenario():
    """The promise the engine was built on, checked rather than asserted: the
    second world is where it pays for itself."""
    world = total(["worlds/hospital-world/world.py"])
    assert world < total(REPLACED) / 3


@pytest.mark.parametrize("path", ENGINE + REPLACED)
def test_the_counter_matches_a_second_method(path):
    """Checked against an independent count, because this counter has been wrong.

    The second method is AST: from the non-blank non-comment lines, subtract each
    docstring's own **non-blank** lines. That word is the whole exercise, the
    hand count that produced the numbers in `docs/ENGINE.md` subtracted the
    docstring's full span from a total that had already dropped blank lines, so
    every empty line inside a docstring was taken off twice and the engine
    measured smaller than it was, three times running, always in its own favour.
    """
    import ast

    src = (ROOT / path).read_text(encoding="utf-8")
    rows = src.splitlines()
    tree = ast.parse(src)
    doc = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False):
                first = node.body[0]
                doc += len([r for r in rows[first.lineno - 1:first.end_lineno]
                            if r.strip()])
    live = len([r for r in rows if r.strip() and not r.strip().startswith("#")])
    assert abs(executable(ROOT / path) - (live - doc)) <= 2
