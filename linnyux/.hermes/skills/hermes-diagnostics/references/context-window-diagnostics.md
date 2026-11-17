---
name: hermes-context-window-diagnostics
description: Diagnose why Hermes appears capped at a smaller context window than the selected model/provider advertises.
version: 1.0.0
author: Hermes Agent
metadata:
  category: software-development
  tags: [hermes, debugging, context-window, model-metadata, compression]
---

# Hermes Context Window Diagnostics

Use this skill when a selected model seems to have a smaller effective context window than the backend should support.

## Workflow

1. Inspect `agent/model_metadata.py` first.
   - Check how the runtime context length is resolved.
   - Prefer provider/server-reported runtime values such as `max_context_length`, `context_length`, or `num_ctx`.
   - Watch for conservative fallback defaults that may cap the agent at 128k even when the backend can do more.

2. Inspect `agent/context_compressor.py`.
   - Confirm compression thresholds are derived from the resolved runtime context length.
   - Check whether summary token budgets or tail protection rules are unintentionally too conservative for larger models.

3. Verify the active model/provider path.
   - Confirm the configured provider is the one actually queried for metadata.
   - Check whether the runtime is using a local server, hosted API, or cached length.

4. Compare reported runtime limit vs. training max.
   - Use the runtime limit for scheduling/compression.
   - Do not substitute a training maximum if the server reports a smaller live context budget.

## Common failure modes

- Conservative fallback metadata masks a larger supported window.
- The compressor threshold is correct, but the resolved context length is stale or cached.
- The provider exposes a larger limit than the agent actually queries.
- Output-token caps are confused with input-context caps.

## Verification

- Re-run the model metadata lookup.
- Recompute compressor thresholds after the context length changes.
- Confirm the agent is no longer using the conservative fallback for the active model/provider.

## Notes

This is a diagnostic workflow, not a model-tuning recipe. Use it to trace where the effective ceiling is coming from before changing compression or max-token behavior.
