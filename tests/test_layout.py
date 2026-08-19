"""The boundary the layout rests on.

Entry points import a scenario by name; core modules never do. Stated in
`docs/SPEC.md` and `CONTRIBUTING.md`, and until now held by discipline alone,
which is how a core slowly learns the name of one scenario and stops being an
instrument.
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "tabib"


def test_no_core_module_imports_a_scenario():
    # a dynamic import by name is the declared entry-point mechanism; what is
    # forbidden is a core module naming a scenario at import time
    bad = []
    for path in sorted(CORE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                bad += [(path.name, a.name) for a in node.names
                        if a.name.split(".")[0] == "scenarios"]
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == "scenarios":
                    bad.append((path.name, node.module))
    assert bad == []
