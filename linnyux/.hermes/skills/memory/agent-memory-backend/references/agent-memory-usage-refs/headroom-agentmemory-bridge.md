# Headroom → agentmemory Bridge Pattern

When integrating headroom (context compression) with agentmemory (persistent vector store),
the key insight is that headroom compresses tool outputs and agentmemory stores them for
cross-session retrieval. Together they form a write-through cache: headroom compresses,
agentmemory persists, and both machines on the tailnet can query.

## Architecture

```
Tool output → headroom proxy (8787) → compressed (CCR marker)
                                          ↓
                              headroom memory store (local SQLite)
                                          ↓
                              agentmemory REST API (:3111)
                              (auto-sync via cron every 5m)
```

## Hermes Plugin

Headroom ships a Hermes plugin at `plugins/hermes/headroom_retrieve/` that registers a
`headroom_retrieve` tool. It turns compression markers (like `[N items compressed hash=abc123]`)
back into full content — without it, the agent sees opaque hashes.

Install by copying the plugin directory into Hermes:
```bash
cp -r plugins/hermes/headroom_retrieve ~/.hermes/plugins/
```

The plugin's `register(ctx)` function uses `ctx.register_tool()` — the same API as
Hermes' native plugins (rtk-rewrite, synapse-memory). No plugin.yaml changes needed.

If the plugin imports `from tools.registry import tool_error, tool_result`, ensure
`httpx` is installed (`pip install httpx`).

## Agentmemory Bridge Plugin

The bridge plugin (`headroom_agentmemory_bridge.py`) registers a second Hermes tool:
`headroom_agentmemory_bridge` with actions `push`, `search`, `status`.

- **Push**: Takes compressed observations from headroom and writes to agentmemory
  via `POST /agentmemory/remember`
- **Search**: Queries agentmemory for prior compressed content via `POST /agentmemory/search`
- **Status**: Health check against the agentmemory daemon

## Auto-Sync Cron

A Python script (`headroom_agentmemory_sync.py`) polls headroom's SQLite database at
`~/.headroom/memory.db` for new entries and pushes them to agentmemory. Run as a
cron job every 5 minutes:

```bash
python3 headroom_agentmemory_sync.py --once
```

The cursor is maintained in `~/.headroom/.agentmemory_cursor` so each run only syncs
new records.

## Key Endpoints

| Endpoint | Method | Body | Purpose |
|----------|--------|------|---------|
| `/agentmemory/remember` | POST | `{"content": "...", "metadata": {...}}` | Write compressed observation |
| `/agentmemory/search` | POST | `{"query": "..."}` | Search stored observations |
| `/agentmemory/health` | GET | - | Daemon health check |
| `/agentmemory/memories` | GET | - | List all memories |

## Design Notes

- The bridge is unidirectional (headroom → agentmemory) — agentmemory doesn't
  feed back into headroom's compression decisions. That would be a V2 improvement.
- The `content` field (not `memory`) is the correct key — this is a common gotcha.
- agentmemory's MCP bridge and REST API share the same backend, so entries written
  via REST are immediately visible via MCP tools and vice versa.
- The sync script uses `urllib` (stdlib) to avoid adding httpx as a dependency.
