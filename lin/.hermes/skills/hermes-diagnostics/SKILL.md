---
name: hermes-diagnostics
description: 'Diagnose Hermes Agent issues: context window caps, memory limits, session env propagation failures.'
---

# Hermes Diagnostics

Troubleshoot issues with Hermes Agent runtime behavior.

## When to Use

Triggers:
- Model appears capped at smaller context window than advertised
- Built-in memory limits cause unexpected truncation
- Resume sessions get 401/Unauthorized

## Sub-workflows

### 1. Context Window Diagnostics
See: `references/context-window-diagnostics.md`
Diagnose why Hermes appears capped at a smaller context window.

### 2. Memory Limit Diagnostics
See: `references/memory-limit-diagnostics.md`
Diagnose and update Hermes built-in memory limits.

### 3. Session Env Propagation Debugging
See: `references/session-env-propagation-debugging.md`
Diagnose 401/Unauthorized failures caused by resumed sessions lacking env vars.

### 4. Memory Provider Architecture
See: `references/memory-provider-setup.md`
Understand the distinction between built-in agentmemory (MCP server, always active) and external memory plugins (`hermes memory setup`). Includes the correct commands, plugin list, and common pitfalls.

### 5. Comprehensive Session Search
See: `references/comprehensive-session-search.md`
When the built-in session_search tool returns too few results (e.g. only 5 recent sessions), use SQLite queries against the full state.db to find older conversations across all platforms (CLI + Telegram).
