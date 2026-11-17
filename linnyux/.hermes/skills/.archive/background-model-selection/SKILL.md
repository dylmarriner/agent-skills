---
name: background-model-selection
description: Use when choosing the model behind agent background work.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [models, providers, free-tier, openrouter, validation]
    related_skills: [ai-provider-cross-config, model-endpoint-wiring, agent-hook-troubleshooting]
---

# Background model selection for agent tooling

## When to Use

- An agent's background work — memory observer, summarizer, classifier, title generator, embedder — needs a model chosen or swapped.
- The user says "make it free", "cheaper", "stop using my paid key".
- A configured model 400s, 429s, or returns output the caller cannot parse.

This is about *which* model and *why it fits*, not the config syntax for each tool (that lives in the provider-config skills).

## Rules

### 1. "Free" is a provider question, not a hardware question

This user wants the model **free** and does **not** want to host it. Reach for a free hosted tier first. Never build a local inference stack from an ambiguous aside: a message that merely *mentions* a local runtime is not an instruction to install one. Confirm the direction in one line before downloading gigabytes — tearing a local stack back out costs as much as building it, and the user has to say it twice. Sizing VRAM unprompted means you took the wrong branch.

### 2. Validate against the caller's exact request shape, never a generic prompt

A model that answers a chat prompt perfectly can still be unusable in the slot you are filling. Reproduce the caller's real request — its temperature, output-token cap, streaming flag, and any vendor extras — and require the reply to satisfy the caller's parser (a specific tag, a JSON object, a bare line). `scripts/probe_chat_endpoint.py` sends that shape to any OpenAI-compatible endpoint and reports latency, token counts, whether the expected marker is present, and the raw reply.

### 3. Know how free tiers fail

A model list does not show any of these; expect several candidates to fail before one passes:

- upstream `429` on the free tier before the request is even processed,
- `403` because the model is restricted to specific agentic harnesses,
- `200` with an empty completion,
- a reasoning trace returned where the answer should be (also much slower),
- the request rejected outright because the endpoint pins a parameter the model refuses.

Reject on any of those and keep the one that passes. A probe costs seconds; the wrong pick costs every request.

### 4. Size the prompt budget to the model that will actually serve it

Background jobs often ship a default input budget far larger than a free or local model can read. Lower the tool's prompt-budget and context-window settings to match what is served, or the model is handed a transcript it silently truncates. Set concurrency to 1 unless the endpoint can genuinely batch.

### 5. Metered plans are the wrong shape for large-prompt background work

A background observer that sends tens of thousands of tokens per request trips per-minute token ceilings on a pay-per-token plan and retry-loops behind the limit. That is a structural mismatch, not a billing preference — prefer a free tier or (only when asked) a local endpoint for this workload.

### 6. Verify the artifact, not the green light

A provider health field reporting the right provider, and a request returning `200`, both prove nothing about output quality. Confirm a real artifact was produced by the new model — read the row/record/file it was supposed to create and check the model field on it.

### 7. Keep credentials where the tool expects them

Put the key in the tool's own credential file (mode 600), not in its settings JSON, and mirror the change across every machine that shares the configuration. A key left behind for a provider you stopped using is not harmful but is worth removing; say so rather than leaving it silently.

## Pitfalls

- **Do not treat "use X provider's key" as permanent.** The user may reverse a direction several turns later. Re-read the current instruction rather than defending an earlier configuration.
- **Do not claim a model is unusable from a failed probe alone** — a `429` is transient. Re-probe before writing a model off, and prefer reporting measured latency and parse success over adjectives.
- **Editing a tool's model config re-arms any trust gate over it.** After changing settings that a hook or plugin reads, re-check the harness's trust state (see `agent-hook-troubleshooting`).
