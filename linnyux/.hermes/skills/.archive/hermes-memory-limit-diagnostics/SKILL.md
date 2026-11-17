---
name: hermes-memory-limit-diagnostics
description: Diagnose and update Hermes built-in memory limits by tracing the real source of the cap, patching config defaults and runtime fallbacks, then verifying the active code and docs.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# Hermes Memory Limit Diagnostics

Use this skill when the user wants to inspect, raise, or debug Hermes built-in memory capacity, especially when a wrapper MCP repo is not the real source of the limit.

## Steps

1. Find the actual Hermes agent repo and inspect the built-in memory implementation.
   - Check `hermes_cli/config.py` for the default `memory_char_limit` and `user_char_limit`.
   - Check `run_agent.py` for the runtime fallback values passed into `MemoryStore`.

2. Confirm whether the limit is configurable or hardcoded.
   - If the code reads from config or env-backed settings, treat the limit as overridable.
   - If only wrapper repos or MCP configs are visible, keep searching until you find the real Hermes source.

3. Patch every source of truth that affects new sessions.
   - Update the config default.
   - Update the runtime fallback.
   - Update docs/examples that advertise the old values.

4. Verify the change.
   - Read back the patched files.
   - Search for remaining old values in the Hermes codebase.
   - Run a lightweight terminal check to confirm the new value appears in the files you changed.

## Pitfalls

- Do not assume an MCP wrapper repo contains the memory cap logic; it may only point at the real Hermes backend.
- Do not change docs without also changing the runtime fallback.
- Do not claim the limit changed globally until the code paths you changed are verified.

## Why it works

Hermes memory capacity is controlled by a small number of config and startup code paths, so patching the actual source of truth plus the fallback prevents the old limit from reappearing in new sessions.

## Last validated

2026-04-18
