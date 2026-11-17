# Free hosted models for background agent workloads

Candidates are only useful if they accept the caller's request shape and return
the expected output marker. Everything below was probed with the same shape
(`temperature: 0.3`, `max_tokens`, `stream: false`) via `scripts/probe-model.py`.
Re-probe before relying on any of it — free-tier availability and gating change
without notice, and a model that is throttled today works tomorrow.

## Failure taxonomy

Read the reply, not just the status code. Each of these is a real rejection mode:

| Symptom | Meaning | Action |
|---|---|---|
| `429` / `Provider returned error` with an upstream note | The free tier is fine, the underlying provider is throttled | Try a different model, do not retry this one |
| `403` mentioning agentic harnesses / coding agents | The model is gated to specific clients | Pick an ungated model |
| `HTTP 200` with `content: ""` | Silent failure on structured prompts | Treat as a failure |
| Reply begins with a reasoning trace | Thinking model leaking its scratchpad into `content` | Pick a non-thinking model, or disable thinking server-side |
| `400` naming `temperature` | The model pins sampling parameters | Use a caller with an override, or pick another model |

A large `chars` count with a thinking trace in it is the worst case: it looks
like a successful call and still breaks the caller's parse.

## Observed results

Re-probe to confirm; these were true at the time of writing.

**Usable as a claude-mem observer** — accepted `temperature: 0.3`, returned the
observation XML, no reasoning trace:

- `nvidia/nemotron-3-super-120b-a12b:free` — fastest of the set (~2 s), clean XML. Preferred pick.
- `qwen/qwen3.8-27b:free` — ~3 s, clean XML.
- `cohere/north-mini-code:free` — ~3 s, clean XML.

**Rejected:**

- `google/gemma-4-31b-it:free` — upstream 429.
- `thinkingmachines/inkling:free` — 403, gated to agentic harnesses.
- `inclusionai/ling-3.0-flash-sante:free` — 200 with empty content.
- `nvidia/nemotron-3.5-lightning:free` — returned a reasoning trace ahead of the answer (~19 s).

## Sizing the model to the job

These are background jobs, so latency is less important than reliability and
output shape — but latency still bounds how far behind the observer falls:

- A memory observer fires per tool use. Multi-second calls are fine; minute-long
  calls are not, because the queue never drains.
- Keep the prompt small. A free tier is metered per request *and* per token, and
  a small served context cannot read a huge transcript anyway.
- `max_tokens` around 2048 is ample for a structured record and halves the
  worst-case latency versus a 4096 cap.

The same rules apply when pointing at a paid model — the probe and the prompt
budget are not a workaround for being free, they are how you find out whether a
model can do the job at all.
