"""Scenario cell -> Inspect Task.

Repetitions are Inspect epochs, which resume per (sample, epoch) rather than per
row. The generation seed derives from the sample id and the epoch, never from
the served text: that is what lets two cells of one contrast draw identically,
and it is why a blind policy differences to exactly zero rather than to zero in
expectation.

The scorer here produces a dashboard count only. Publishable statistics live in
`analysis/` and are computed from the logs, so nothing downstream re-scores.
"""

from __future__ import annotations

from inspect_ai import Epochs, Task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import TaskState

from .util import sample_seed


@scorer(metrics=[mean()])
def acted_scorer():
    """A dashboard count of cases that produced a usable decision.

    Not "was it right": correctness against an answer key is what a measurand
    may not read, and it would come back through the viewer. Committing an act
    is not enough either: a payload outside the declared vocabulary, or a turn
    the serving stack cut short, is an absent measurement, and the measurands
    drop both. Counting them here would show a healthy run over a broken one.
    """
    async def score(state: TaskState, target: Target) -> Score:
        record = state.store.get("tabib:record", {})
        usable = (record.get("status") != "degraded"
                  and bool(record.get("payload"))
                  and bool(record.get("in_vocabulary")))
        return Score(value=float(usable), answer=record.get("payload"),
                     explanation=None if usable else record.get("status"),
                     metadata=record)
    return score


def make_samples(rows: list[dict], *, campaign_seed: int = 20260725) -> list[Sample]:
    """One dict per unit from the scenario, at least an `id`, carried whole into
    sample metadata for `build`."""
    return [Sample(id=str(row["id"]), input=str(row["id"]),
                   metadata={**row, "campaign_seed": campaign_seed})
            for row in rows]


def seed_of(state: TaskState) -> int:
    """Two cells of one contrast share a sample id and an epoch, so they share
    this seed and a blind policy draws identically in both."""
    return sample_seed(int(state.metadata["campaign_seed"]),
                       f"{state.sample_id}:r{state.epoch}")


def cell_task(scenario_name: str, cell: str, *, samples: list[Sample], solver,
              reps: int = 1, mode: str = "pilot") -> Task:
    return Task(dataset=samples, solver=solver, scorer=acted_scorer(),
                epochs=Epochs(reps, "mean"),
                name=f"{scenario_name}-{cell}",
                metadata={"scenario": scenario_name, "cell": cell, "mode": mode})
