"""Live invariants, checked on every sample as a campaign runs.

The failure this exists to prevent is not a wrong formula, it is nobody looking.
A campaign can spend a night producing clean-looking aggregates over a serving
fault, and the fault is obvious in the first ten samples if anything is watching.

Four counters, all of them cheap and all of them serving faults rather than
results:

    degraded          turns cut short by the stack instead of by the model
    no tool call      sessions that never touched a tool. Where a manipulation
                      lives behind a lookup, those sessions make the two cells
                      byte-identical and the contrast null by construction
    rejected calls    tool calls refused for their arguments, which cost the
                      model its turn and land in the record as no act at all
    reasoning-starved output that was almost entirely reasoning tokens, which is
                      what an unswitched hybrid model looks like from outside

Import this module from a campaign to arm it. Inspect wraps hooks in a
try/except, so this reports and never blocks: it is an alarm, not a gate.
"""

from __future__ import annotations

from inspect_ai.hooks import Hooks, SampleEnd, hooks
from inspect_ai.util import display_counter

STARVED = 0.9   # share of output tokens spent reasoning


@hooks(name="tabib_watch", description="Serving invariants during a campaign.")
class Watch(Hooks):
    samples = degraded = starved = silent = rejected = 0

    async def on_sample_end(self, data: SampleEnd) -> None:
        sample = data.sample
        self.samples += 1
        record = (sample.store or {}).get("tabib:record") or {}
        self.degraded += int(record.get("status") == "degraded")
        self.silent += int(not record.get("tool_calls"))
        self.rejected += int(bool(record.get("rejected_calls")))
        for usage in (sample.model_usage or {}).values():
            if (usage.reasoning_tokens or 0) > STARVED * (usage.output_tokens or 1):
                self.starved += 1

        display_counter("degraded", f"{self.degraded}/{self.samples}")
        display_counter("no tool call", f"{self.silent}/{self.samples}")
        display_counter("rejected calls", f"{self.rejected}/{self.samples}")
        display_counter("reasoning-starved", f"{self.starved}/{self.samples}")
