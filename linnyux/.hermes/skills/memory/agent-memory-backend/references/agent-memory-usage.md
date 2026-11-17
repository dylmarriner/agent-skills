---
name: agent-memory-usage
description: Daily workflow for using agentmemory MCP tools as primary memory — saving facts, cross-session recall, semantic search, and migration from basic memory. Use instead of the limited basic `memory` tool for anything substantive.
category: memory
emoji: 🧠
trigger: |
  User says "remember this", "store that", "why don't you know X", "transfer my memories",
  or you need to recall something from a past session. Also when the session starts and
  you need to re-establish context — use agentmemory recall first, not basic memory.
  Whenever you'd reach for the basic `memory` tool, consider whether agentmemory is the
  better choice (it usually is).
---

# Agent Memory Operations (agentmemory MCP)

## Golden Rule

**Use `mcp_agentmemory_memory_save` and `mcp_agentmemory_memory_recall` for ALL substantive memory.** The basic `memory` tool has a 2.2K char limit and is injected every turn — reserve it for compact essentials only (a single pointer to agentmemory, timezone, etc.).

## Tool Reference

### Save facts
```
mcp_agentmemory_memory_save(
  content="What to remember — be specific and self-contained",
  type="fact|preference|pattern|architecture|bug|workflow",
  concepts="comma-separated keywords for search"
)
```

Types:
- `fact` — environment config, project structure, installed tools
- `preference` — user preferences, communication style, pet peeves
- `pattern` — recurring technique, workflow, or approach
- `architecture` — architectural decisions and rationale
- `bug` — known bugs and their fixes
- `workflow` — multi-step procedures

### Recall cross-session context
```
mcp_agentmemory_memory_recall(
  query="what I need to find — describe the concept",
  limit=5  # bump to 10-20 for broad discovery
)
```
Use this when the session starts to re-establish context. Also use when the user references something from a past session — never ask "what were you working on" before checking agentmemory first.

### Smart search (hybrid semantic + keyword)
```
mcp_agentmemory_memory_smart_search(
  query="describe the concept",
  limit=10
)
```
Use when `recall` returns nothing useful — casts a wider net.

### Other tools
- `mcp_agentmemory_memory_sessions` — list recent sessions
- `mcp_agentmemory_memory_audit` — see recent save operations
- `mcp_agentmemory_memory_export` — export all memory as JSON

## Migration: Basic Memory → agentmemory

When the basic `memory` tool is full (or the user asks to transfer):

### Via MCP Tools (preferred)

```
1. Read all entries from basic memory (call `memory(action='add', target='memory')` 
   with dummy content to list them, or `memory(action='add', target='user')` for profile)
2. Save each entry to agentmemory via mcp_agentmemory_memory_save with appropriate type
3. Remove each old entry from basic memory via memory(action='remove', old_text=...)
4. Leave a single compact pointer: "Primary memory is agentmemory (port 3111, 
   MCP mcp_agentmemory_memory_* tools). Basic memory is fallback only."
```

### Via REST API (fallback when MCP tools unavailable)

When the MCP bridge isn't responding (daemon restart, config not yet applied), use
agentmemory's REST API directly at `http://localhost:3111`:

```
POST /agentmemory/remember
Content-Type: application/json

{"content": "The memory text", "metadata": {"type": "fact|user|project|..."}}
```

**Key detail:** The field is `content`, NOT `memory`. Using `memory` returns HTTP 400.

Node.js example:

```javascript
const data = JSON.stringify({content: "memory text", metadata: {type: "fact"}});
const req = http.request("http://localhost:3111/agentmemory/remember", {
  method: "POST",
  headers: {"Content-Type": "application/json"}
}, res => { /* handle 201 */ });
req.write(data);
req.end();
```

Search via REST:

```
POST /agentmemory/search
Content-Type: application/json

{"query": "search terms"}
```

Returns `{results: [...]}` with matched memories.

Use REST for bulk operations (10+ entries at once) or when MCP tools aren't
loading. The MCP bridge transparently uses the same backend, so entries written
via REST are immediately visible to MCP tools and vice versa.

### When `agentmemory import` Won't Work

The CLI `agentmemory import <file.jsonl>` command spawns its **own daemon instance**
that competes for port 3111. It cannot run while the main daemon is already active,
and it times out if `iii` binary isn't on PATH. Use REST API instead for bulk seeding.

## What Goes Where

| Store | Use For | Limit |
|-------|---------|-------|
| agentmemory MCP | Everything substantive: user prefs, env config, project facts, decisions | Unlimited |
| basic `memory` tool | Only compact turn-injected essentials: timezone, agentmemory pointer, 1-2 critical facts | 2.2K chars |
| user profile (basic) | Avoid — put user preferences in agentmemory as type=preference | 1.4K chars |

## Pitfalls

- agentmemory's `recall` may return empty for a few seconds after `save` — data is persisted (check `standalone.json`), indexing is async. Retry once before concluding data is lost.
- Multiple agentmemory MCP servers (Hermes + OpenClaw both start one) can cause confusion if they talk to different backends. They share the same `~/.agentmemory/` store by default — this is fine.
- **Multi-machine memory**: When sharing a single agentmemory backend across multiple Hermes nodes (see agent-memory-backend `references/multi-machine-cognitive-memory.md`), agentmemory MCP tools (`recall`, `save`, `smart_search`) transparently use the shared store. However, the basic `memory` tool is per-machine — each machine's entries are separate. Use agentmemory MCP for cross-machine persistent facts.
- **Headroom integration**: When headroom is used for context compression, its CCR markers (`[N items compressed hash=abc123]`) are opaque to the agent unless the headroom-retrieve Hermes plugin is installed. See `references/headroom-agentmemory-bridge.md` for the full bridge pattern including auto-sync cron and REST API seeding.
- Hindsight is an alternative cloud-backed memory engine but requires credits. agentmemory runs locally with no API costs.
- Memory export: `mcp_agentmemory_memory_export` returns all data as JSON — useful before migrations.
