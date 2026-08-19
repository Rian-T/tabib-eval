from __future__ import annotations

import asyncio

import pytest
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.tool import ToolDef, ToolParam, ToolParams

from tabib import Act
from tabib.nulls import degenerate, label, points
from tests.conftest import TOY_ACTS, toy_tools


def tooldefs():
    """The declared tools as Inspect sees them, so policies are exercised
    against real schemas rather than a stub."""
    out = []
    for spec in toy_tools():
        async def execute(**kw):
            return ""
        out.append(ToolDef(
            execute, name=spec.name, description=spec.description,
            parameters=ToolParams(
                properties={k: ToolParam(type=t, description=d)
                            for k, (t, d) in spec.params.items()},
                required=list(spec.params))))
    return out


def test_the_acts_enumerate_every_distinguishable_action():
    assert points(TOY_ACTS) == [
        ("send", {"level": "low"}), ("send", {"level": "high"}), ("hold", {})]


def test_admissible_values_need_the_argument_that_carries_them():
    with pytest.raises(ValueError):
        Act("send", values=("low",))


def test_a_free_text_payload_is_recorded_without_being_enumerated():
    # a dosage is not a finite vocabulary: the act is one point of the space,
    # and the payload is read rather than enumerated
    assert points((Act("send_plan", payload="posologie"),)) == [("send_plan", {})]


def test_the_core_derives_one_policy_per_point_plus_the_generic_ones():
    got = set(degenerate(TOY_ACTS))
    assert {label(n, o) for n, o in points(TOY_ACTS)} <= got
    assert {"silent", "memoryless"} <= got


def test_a_policy_is_a_callable_the_mock_provider_accepts():
    # the whole gate rests on this: custom_outputs must take a function of
    # (messages, tools, tool_choice, config), not just a list of outputs
    policy = degenerate(TOY_ACTS)["const:send=high"]
    model = get_model("mockllm/model", custom_outputs=policy, memoize=False)
    out = asyncio.run(model.generate("bonjour", tools=tooldefs()))
    assert out.message.tool_calls[0].function == "send"
    assert out.message.tool_calls[0].arguments["level"] == "high"


def test_memoryless_draws_the_same_action_for_the_same_sample_seed():
    # both cells of a contrast share a seed, so the null differences to zero
    # exactly rather than only in expectation
    policy = degenerate(TOY_ACTS)["memoryless"]
    model = get_model("mockllm/model", custom_outputs=policy, memoize=False)
    draws = []
    for served in ("source relâchée", "source durcie"):
        out = asyncio.run(model.generate(served, tools=tooldefs(),
                                         config=GenerateConfig(seed=1234)))
        c = out.message.tool_calls[0]
        draws.append((c.function, tuple(sorted(c.arguments.items()))))
    assert draws[0] == draws[1]
