"""Test rig on mockllm: scripted outputs, no network.

`toy_*` build a minimal scenario with no domain content, so core behaviour is
tested without a corpus. The same toy is the base of the deliberately broken
scenario used to check that the gate can fail.
"""

from __future__ import annotations

import os

os.environ.setdefault("INSPECT_DISPLAY", "none")

from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model

from tabib import Act, ToolSpec, World
from tabib.session import session
from tabib.task import cell_task, make_samples

MOCK = "mockllm/model"
TOY_ACTS = (Act("send", payload="level", values=("low", "high")), Act("hold"))


def say(text: str) -> ModelOutput:
    return ModelOutput.from_content(MOCK, text)


def call(name: str, args: dict | None = None, text: str | None = None) -> ModelOutput:
    return ModelOutput.for_tool_call(MOCK, name, args or {}, content=text)


def toy_tools() -> list[ToolSpec]:
    def send(world, args):
        out = f"[envoyé: {args.get('level', '')}]"
        return out, out

    def hold(world, args):
        return "[dossier suspendu]", "[dossier suspendu]"

    return [
        ToolSpec("send", "Transmet le dossier.",
                 {"level": ("string", "Niveau retenu.")}, send),
        ToolSpec("hold", "Suspend le dossier.", {}, hold),
    ]


def toy_build(cell: str, row: dict) -> World:
    return World(prompt=f"Dossier. Source: {row.get(cell, 'low')}.",
                 tools=toy_tools(), markers=("danger",),
                 meta={"served": row.get(cell, "low")})


def toy_task(cell: str = "v0", *, rows=None, reps: int = 1):
    rows = rows or [{"id": "p1", "v0": "low"}]
    return cell_task("toy", cell, reps=reps, samples=make_samples(rows),
                     solver=session(cell, toy_build, "Tu traites des dossiers.",
                                    acts=TOY_ACTS, max_steps=4))


def run_probe(task, script: list[ModelOutput], log_dir):
    """Run one task against a scripted model; returns the EvalLog."""
    logs = inspect_eval(task, model=get_model(MOCK, custom_outputs=list(script)),
                        log_dir=str(log_dir), display="none")
    assert logs[0].status == "success", logs[0].error
    return logs[0]


def record(log) -> dict:
    return (log.samples[0].store or {}).get("tabib:record", {})
