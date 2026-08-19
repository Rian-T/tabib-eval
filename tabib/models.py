"""Model registry, the single source of truth. TABIB never runs inference:
every entry is an Inspect provider string; the per-model GenerateConfig
travels with the Model object."""

from __future__ import annotations

from inspect_ai.model import GenerateConfig, Model, get_model

REGISTRY: dict[str, dict] = {
    # dev probes
    "glm-5.2":          {"model": "openrouter/z-ai/glm-5.2",           "temperature": 0.7},
    "kimi-k3":          {"model": "openrouter/moonshotai/kimi-k3",     "temperature": 0.6},
    "deepseek-v4-pro":  {"model": "openrouter/deepseek/deepseek-v4-pro", "temperature": 0.6},
    "nemotron-ultra":   {"model": "openrouter/nvidia/nemotron-3-ultra-550b-a55b",
                         "temperature": 0.6},
    # free tier: 20 requests/minute and a daily cap, good for plumbing smokes
    # and nothing binding
    "nemotron-ultra-free": {"model": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
                            "temperature": 0.6, "max_connections": 2, "max_retries": 10},
    # deployed-class panel
    "qwen3.6-35b-a3b":  {"model": "openrouter/qwen/qwen3.6-35b-a3b",   "temperature": 0.7, "hybrid": True},
    "qwen3.6-27b":      {"model": "openrouter/qwen/qwen3.6-27b",       "temperature": 0.7, "hybrid": True},
    "glm-4.7-flash":    {"model": "openrouter/z-ai/glm-4.7-flash",     "temperature": 0.7},
    "mistral-medium":   {"model": "openrouter/mistralai/mistral-medium-3-5", "temperature": 0.3},
    # frontier reference
    "claude-haiku-4.5": {"model": "openrouter/anthropic/claude-haiku-4.5", "temperature": 0.0,
                         "reasoning_effort": "minimal"},
    # no inference at all: the scripted backend Inspect ships. It answers
    # nothing useful, and that is the point: it walks a scenario end to end
    # with no endpoint, no key and no network.
    "mock":             {"model": "mockllm/model",           "temperature": 0.0},
    # local, for development only: small enough to smoke a scenario end to end
    "dev":              {"model": "ollama/gemma4:e2b",       "temperature": 0.7, "hybrid": True},
    # local panel (Ollama; tool-calling models only for agentic arms)
    "qwen3.5-4b":       {"model": "ollama/qwen3.5:4b",       "temperature": 0.7, "hybrid": True},
    "qwen3.5-9b":       {"model": "ollama/qwen3.5:9b",       "temperature": 0.7, "hybrid": True},
    "ministral-8b":     {"model": "ollama/ministral-3:8b",   "temperature": 0.0},
    "nemotron-4b":      {"model": "ollama/nemotron-3-nano:4b", "temperature": 0.0, "hybrid": True},
    # cluster vLLM endpoint (VLLM_BASE_URL + VLLM_API_KEY=EMPTY at run time)
    # thinking is on for these: the reasoning trace is half
    # of what a world records. glm thinks natively, gpt-oss at low effort,
    # qwen and gemma are declared below; mistral-small has no thinking mode
    # (Magistral is the reasoning line, a different model), which is a
    # property of the panel and is reported as such. S1/S2 campaigns before
    # that date ran qwen with thinking off.
    "qwen3.6-27b-local": {"model": "openai-api/vllm/qwen3.6-27b", "temperature": 0.7,
                          "hybrid": True, "thinking": True},
    "qwen3.5-122b-local": {"model": "openai-api/vllm/qwen3.5-122b", "temperature": 0.7, "hybrid": True},
    "gpt-oss-120b-local":  {"model": "openai-api/vllm/gpt-oss-120b",  "temperature": 0.7,
                            "reasoning_effort": "low"},
    # one GPU where the 120b asks for four and waits days in the queue
    "gpt-oss-20b-local":   {"model": "openai-api/vllm/gpt-oss-20b",   "temperature": 0.7,
                            "reasoning_effort": "low"},
    "glm-4.7-flash-local": {"model": "openai-api/vllm/glm-4.7-flash", "temperature": 0.7},
    # gemma 4 has a thinking mode too (doc: <|think|> at the head of the
    # system prompt, channel-structured output). Declared hybrid so the mode is
    # sent explicitly; whether the served chat template honors
    # enable_thinking is verified at its first serve, and injecting the token
    # ourselves would be an instrument decision, never a silent fallback.
    "gemma-4-26b-local":   {"model": "openai-api/vllm/gemma-4-26b",   "temperature": 0.7,
                            "hybrid": True, "thinking": True},
    "deepseek-v4-flash-local": {"model": "openai-api/vllm/deepseek-v4-flash", "temperature": 0.6},
    "minimax-m2.7-local":  {"model": "openai-api/vllm/minimax-m2.7",  "temperature": 0.7},
    "mistral-small-4-local": {"model": "openai-api/vllm/mistral-small-4", "temperature": 0.3},
    "mistral-small-24b-local": {"model": "openai-api/vllm/mistral-small-24b", "temperature": 0.3},
    # the reasoning line of the same family, parked: serving works (R0 green),
    # but without its own reasoning template in the
    # system prompt it emits no [THINK] block (R1 0.35, zero reasoning in 214
    # assistant messages). Nobody deploys it as an agent, so the +/- reasoning
    # contrast within one family is paper material, not panel material. The
    # official template is SYSTEM_PROMPT.txt in its HF repo; serving it means
    # a per-model system prefix, a deliberate instrument change
    "magistral-small-local": {"model": "openai-api/vllm/magistral-small", "temperature": 0.7},
}

# the long_shift serving line: same models, same modes, 65536 context. A tag
# is a serving configuration, and a context size is part of it
REGISTRY.update({
    "qwen3.6-27b-l20": {**REGISTRY["qwen3.6-27b-local"]},
    # the panel's qwen: three billion active parameters where
    # the 27B is dense, for the one model that writes a chain of thought per
    # file and has no prefix cache. A roster change, declared, not a tuning
    "qwen3.6-35b-l20": {"model": "openai-api/vllm/qwen3.6-35b", "temperature": 0.7,
                        "hybrid": True, "thinking": True},
    "glm-4.7-flash-l20": {**REGISTRY["glm-4.7-flash-local"]},
    "gemma-4-26b-l20": {**REGISTRY["gemma-4-26b-local"]},
    "gpt-oss-20b-l20": {**REGISTRY["gpt-oss-20b-local"]},
    "mistral-small-24b-l20": {**REGISTRY["mistral-small-24b-local"]},
})

PANEL: tuple[str, ...] = ("qwen3.6-35b-a3b", "qwen3.6-27b", "glm-4.7-flash", "mistral-medium")
DEV_MODEL = "dev"


def model(tag: str, *, thinking: bool | None = None,
          temperature: float | None = None) -> Model:
    """A registry entry as an Inspect model.

    Switching a hybrid model out of reasoning mode has three different spellings
    and no portable one. `chat_template_kwargs` is a vLLM extension, Ollama
    wants `think`, and OpenRouter takes `reasoning_enabled` as a model argument
    rather than in the generation config. A backend silently ignores a spelling
    meant for another, so the model reasons until it runs out of budget and
    returns an empty completion, which reads downstream as a parsing failure or
    an abstention rather than as a serving setting.
    """
    entry = REGISTRY[tag]
    provider = entry["model"].split("/")[0]
    args = dict(entry.get("args", {}))
    extra = None
    # None means "what the registry declares": the caller only overrides for a
    # one-off probe. A hybrid's mode is sent explicitly in both directions,
    # relying on a chat template's default is how thinking silently follows a
    # serving upgrade instead of this table.
    if thinking is None:
        thinking = bool(entry.get("thinking"))
    if entry.get("hybrid"):
        if provider == "ollama":
            extra = {"think": thinking}
        elif provider == "openrouter":
            args["reasoning_enabled"] = thinking
        else:
            extra = {"chat_template_kwargs": {"enable_thinking": thinking}}
    # Left to its default the backoff grows without bound: a model whose format
    # makes the server answer 500 now and then was seen waiting 1539 seconds on
    # its tenth try, and slept through a whole allocation. Five tries keep the
    # wait in seconds. A session that fails all five is lost and counted as an
    # error, which is the outcome we want: an error is a row in a table, waiting
    # is a campaign.
    # A long session replays its whole history every turn, so what makes it
    # affordable is the server's prefix cache: the turn only pays for its own
    # delta. Left unset, Inspect keeps 60 to 100 sessions in flight at once and
    # the KV cache, at 157k tokens, holds about 1.6k per session, while a
    # twenty-file session weighs ten times that. Every session is evicted
    # between two of its own turns, the hit rate sits at 0 to 5 %, and each turn
    # re-prefills from scratch: the cost becomes quadratic in session length,
    # which is why the long cells crawl and the short ones do not. Fewer
    # sessions at once is the faster setting here, not the slower one.
    return get_model(entry["model"], config=GenerateConfig(
        temperature=entry["temperature"] if temperature is None else temperature,
        reasoning_effort=entry.get("reasoning_effort"),
        max_retries=entry.get("max_retries", 5),
        max_connections=entry.get("max_connections", 16),
        extra_body=extra), **args)
