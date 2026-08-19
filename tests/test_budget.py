"""The budget field is an addition, and additions must not move anything.

A scenario that predates it declares none and has to keep running on exactly
the numbers it ran on before the field existed.
"""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("INSPECT_DISPLAY", "none")

from tabib import scenario as core
from tabib.session import session

from scenarios.source_fidelity import scenario as s1
from scenarios.yielding_boundary import scenario as s2
from scenarios.worked_session import scenario as s3


def test_the_older_scenarios_declare_no_budget():
    assert s1.SCENARIO.budget is None
    assert s2.SCENARIO.budget is None


def test_the_default_is_the_session_own_default():
    # two places holding the same number drift; this is what notices
    params = inspect.signature(session).parameters
    assert core.DEFAULT_BUDGET == (params["max_steps"].default,
                                   params["max_tokens"].default)


def budget_of(task) -> tuple[int, int]:
    """What `build_task` actually handed the session, read off the solver.

    The limits are free variables of the closure, so this reads the value the
    task will run on rather than the value the field says it should. A test that
    re-reads the declaration would pass whatever `build_task` did with it.
    """
    solve = task.solver[0] if isinstance(task.solver, list) else task.solver
    fn = getattr(solve, "__wrapped__", solve)
    free = dict(zip(fn.__code__.co_freevars,
                    (cell.cell_contents for cell in fn.__closure__)))
    return free["max_steps"], free["max_tokens"]


def test_the_older_scenarios_run_on_exactly_the_numbers_they_ran_on_before():
    # the invariance that matters: not that they declare no budget, but that
    # the task built from them carries the same limits it carried before the
    # field existed
    for sc in (s1.SCENARIO, s2.SCENARIO):
        for cell in sc.cells:
            assert budget_of(core.build_task(sc, cell, n=4)) == (8, 2000), \
                (sc.name, cell)


def test_the_new_scenario_carries_its_own_limits_into_the_task():
    for cell in s3.SCENARIO.cells:
        assert budget_of(core.build_task(s3.SCENARIO, cell, n=4)) == s3.budget(cell)


def test_only_the_queue_scenarios_carry_a_budget():
    """A budget exists for one reason: a cell holding several cases cannot run on
    the step count of a cell holding one. What matters is that the single-case
    scenarios have not acquired one, which would silently change the limits their
    numbers were measured under. Named rather than enumerated: a new queue
    scenario is expected to carry a budget, and this test may not be the thing
    that tells it not to.
    """
    assert s3.SCENARIO.budget is not None
    carried = {name for name, sc in core._SCENARIOS.items() if sc.budget}
    assert not carried & {"source_fidelity", "yielding_boundary"}


def test_the_budget_scales_with_the_queue_and_nothing_else():
    steps_alone, tokens_alone = s3.budget("alone")
    steps_session, tokens_session = s3.budget("session")
    assert steps_session == 10 * steps_alone
    assert tokens_alone == tokens_session
