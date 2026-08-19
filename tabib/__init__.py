"""TABIB: an instrument for measuring how language models behave in
high-stakes settings, built on Inspect AI.

Inspect runs the evaluation. TABIB decides what counts as a measurement: a
publishable number is a change score inside one cluster, so a policy that
ignores the manipulation scores exactly zero and cannot produce an effect.

A scenario needs these six names and nothing else from the core.
"""

from .measurand import Measurand
from .nulls import Act
from .scenario import Scenario, get, register
from .world import ToolSpec, World

__all__ = ["Act", "Measurand", "Scenario", "ToolSpec", "World", "get", "register",
           "compare", "load", "run"]


def __getattr__(name: str):
    """`tabib.load` and its two siblings, imported on use.

    The façade reaches the campaign and the analysis, which pull Inspect's
    evaluation stack; a scenario importing this package must not pay for that
    at import time.
    """
    if name in ("compare", "load", "run"):
        from . import api
        return getattr(api, name)
    raise AttributeError(name)
