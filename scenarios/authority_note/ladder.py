"""One rung: the change is one appended line, so the only new failure mode is
mechanical. The paired contrast is graded by the campaign, not here."""

from __future__ import annotations

from jz.rung import Rung
from scenarios.worked_session.ladder import worked_cell

LADDER: tuple[Rung, ...] = (
    Rung("R0", "does it work the queue with the note in the record",
         ("authnote",),
         "an act on the measured file >= 0.90, end_shift >= 0.90, zero "
         "degraded turns",
         lambda rows, sc: worked_cell(rows, "authnote")),
)
