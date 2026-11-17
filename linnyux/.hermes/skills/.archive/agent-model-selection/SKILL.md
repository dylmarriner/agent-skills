---
name: agent-model-selection
description: Use when choosing or swapping an agent's model.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [llm, provider, openrouter, model-selection, cost, observer]
    related_skills: [agent-memory-backend, ai-provider-cross-config]
---

# Agent model selection

Choosing the model an autonomous agent runs on for its own background work — memory compression, observation extraction, summarisation, classification, routing — as opposed to the model the user talks to. These jobs are high-volume, mechanical, and driven by a prompt the agent builds, so cost, hosting and output format matter far more than leaderboard rank.

## When to Use

- Picking or swapping the model behind a memory engine, observer, or summariser.
- A request to make that model "free", "cheaper", "local", or "not hit my quota".
- A provider that started returning 429s, 400s, or empty output and needs replacing.

## "Free" means free hosted, not self-hosted

**Standing user preference: when told to make a model free, answer with a free hosted tier — never local inference.** Do not propose Ollama, llama.cpp, vLLM, LM Studio or any self-hosted endpoint for this, and do not read "self-hosted" into "free". This user has corrected that misreading more than once and emphatically; reaching for a local model after being asked for a free one reads as not listening.

Keep the two hosting questions separate, because they have opposite answers:

| Question | Answer |
|---|---|
| Where does the *application* run? | The user's own machines — daemons, workers, databases stay local. |
| Where does the *model* run? | Hosted. Free tier is fine, self-hosting is not. |

Self-hosting a model is a separate request that has to be made explicitly. If it is ever made, see the sizing section below before downloading anything.

Free hosted options: OpenRouter `:free` models (`https://openrouter.ai/api/v1`), a provider's own free tier (Google AI Studio, Groq, Cerebras). An aggregator free tier needs no card and no local GPU.

## Probe before you wire

**Never wire a model without sending it the real request shape first.** Free tiers in particular are not uniformly usable, and the failures are silent or cryptic at runtime. Send exactly what the caller sends — `model`, `messages`, `temperature`, `max_tokens`, `stream: false` — then require the reply to contain the caller's expected output marker and no reasoning trace.

Run [scripts/probe-model.py](scripts/probe-model.py):

```sh
OPENROUTER_API_KEY=... python3 scripts/probe-model.py \
  --endpoint https://openrouter.ai/api/v1 \
  --key-env OPENROUTER_API_KEY \
  --marker '<observation>' \
  --model vendor/model-a:free --model vendor/model-b:free
```

It prints per-model pass/fail, latency, token counts and the first line of the reply, and exits non-zero when nothing passed. Wire only a model it passed. Verified and rejected candidates, with the failure taxonomy, are in [references/free-hosted-models.md](references/free-hosted-models.md).

Common rejection reasons to look for in the reply, not just the status code:

- **Reasoning trace instead of the answer.** A thinking model emits its scratchpad into `content`, so the caller's XML/JSON parse fails. Disable thinking at the server or pick a non-thinking model.
- **Upstream 429.** The free tier is fine but the underlying provider is throttled. Try another model rather than retrying this one.
- **Gating.** Some free models are restricted to coding agents or specific harnesses and 403 on a raw API call.
- **Empty content with a 200.** Treat as a failure; some models return `content: ""` for structured-output prompts.
- **Parameter rejection.** A 400 naming a parameter means that model pins it — see the temperature note below.

## Temperature and token parameters are pinned more often than you expect

Agent harnesses pick their own sampling parameters, and current reasoning models often accept only the default:

- A model that answers `Unsupported value: 'temperature' does not support 0.3 with this model. Only the default (1) value is supported` cannot be used by a caller that hardcodes `temperature: 0.3`. Either the caller exposes an override (claude-mem's OpenRouter provider does, via a JSON extra-body setting that merges over the request) or pick a different model.
- `max_tokens` vs `max_completion_tokens` is a similar split. Many clients retry automatically on a 400 that names the parameter, so check the log before assuming the model is unusable.

Probe at the temperature the caller actually uses — passing 1.0 while the caller sends 0.3 hides the failure.

## Metered plans fail under agent prompt sizes

Background jobs are not small prompts. A memory observer sends tens of thousands of tokens per request — claude-mem's sends roughly 58 k — which trips per-minute token limits on a metered plan and surfaces as repeated failures while the session keeps retrying:

```
Observer failed {kind=rate_limit} ... Rate limit reached ... Limit 200000 TPM, Used 198023, Requested 58385
```

Free hosted tiers avoid the billing ceiling. Independently, cap the prompt the caller builds — a large prompt also has to fit whatever context the served model actually has:

```
CLAUDE_MEM_OBSERVER_CONTEXT_WINDOW=16384
CLAUDE_MEM_OBSERVER_MAX_CONVERSATION_CHARS=24000
CLAUDE_MEM_OBSERVER_MAX_OUTPUT_TOKENS=2048
CLAUDE_MEM_MAX_CONCURRENT_AGENTS=1
```

One worker slot is right for a background job: a free tier serialises anyway, and parallel requests only burn the quota faster.

## Credential and settings hygiene

- Put keys in the engine's own credential file (claude-mem uses `~/.claude-mem/.env`, mode 600, with a fixed whitelist of key names), not in its `settings.json`. Never inline a key into a settings JSON or a systemd unit.
- When swapping providers, clear the previous provider's fields rather than leaving them populated. Stale values produce confusing health output — you want the health endpoint to name exactly one provider.
- Check the health endpoint after the swap. A field that mirrors subscription rate limits (claude-mem's `rateLimits`) should come back empty once the caller is off a subscription: an empty object is the proof the subscription is no longer in the path.
- Point any tier/small-model aliases at the real model name. An alias that resolves to a model the endpoint does not serve produces a 404 on a subset of requests rather than a clean failure.

## If self-hosting a model is explicitly requested

Measure before downloading, because the recorded reality is usually worse than the spec sheet:

1. **Ask the runtime for real free memory, not the marketing number.** `llama-server --list-devices`, and `/sys/class/drm/card*/device/mem_info_vram_used` while the desktop is up. A 4 GB card driving a remote desktop reported 4096 MiB total and only ~3 GiB free.
2. **Sizing is binary: does the model fit entirely or not.** Automatic layer-fitting keeps a model *loaded* but not *fast* — offloading part of a 5 GB model left the rest on CPU, the runtime picked half the available threads, and generation ran at 2.4 tok/s (91 s for a 126-token answer). The same job on a model that fit entirely ran at 12 tok/s. Prefer the smaller model that fits over the larger one that spills.
3. **Benchmark the candidate with the caller's real request shape before wiring it**, same as the hosted path, and confirm the output marker is present.

The general lesson holds outside LLMs: a background job on a small always-on box needs a model sized to the box, and the box's real free memory is what counts.
