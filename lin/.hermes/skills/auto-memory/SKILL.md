---
name: auto-memory
description: Use the AutoMemory harness to design, implement, and evaluate a tailored memory system for a target agent repository, with SCOS/OptMem preservation for Hermes.
---

# AutoMemory: Harness Entry Point

AutoMemory is **an agent-memory engineering process**, not a drop-in memory database. The installed upstream repository is at `/home/lin/.hermes/automemory`; its `ask_ref` CLI is on PATH.

## Usage
When asked to build/improve an agent's memory:
1. Identify the target repository and record its live memory providers before making changes.
2. Read the upstream instructions at `/home/lin/.hermes/automemory/commands/auto-memory.md`.
3. Call the `auto-memory-design` skill and review its memory design; use the matching upstream `commands/auto-memory-design.md`.
4. Only after the design is accepted, call `auto-memory-implement`, then `auto-memory-refine`. Use separate agent sessions for each phase to prevent context drift, as recommended upstream.
5. Verify regressions, integration, memory recall and persistence through restart.

## Lin/Hermes safety
For Hermes, target `/home/lin/.hermes/hermes-agent`. Its existing config currently uses `memory.provider: optmem` and exposes a separate SCOS MCP bridge. **Do not replace, disable, wipe, or migrate either provider without explicit approval and measured tests.** Preserve any uncommitted modifications. Work in a new branch/worktree and test before merging. Require owner approval before a lasting change to live runtime behavior, memory data or global configuration. Do not silently start paid LLM/evaluation loops.
