# Hermes Plugin Pattern

Hermes plugins are Python packages that add tools directly into the agent's
toolchain. Place them at `~/.hermes/plugins/<name>/` — Hermes auto-discovers
them on startup.

This pattern covers wrapping an MCP server as Hermes native tools. Since Hermes
supports MCP natively via `mcp_servers` in config.yaml, a native plugin is
optional but provides: better tool descriptions, richer error handling, and
direct API key configuration via `requires_env`.

## Package Structure

```
~/.hermes/plugins/synapse-memory/
├── plugin.yaml        ← Manifest (required)
├── schemas.py         ← Tool schemas (required, file name is fixed)
└── tools.py           ← Tool handlers (required, file name is fixed)
```

## plugin.yaml

```yaml
name: synapse-memory
version: 1.0.0
description: "Persistent AI memory backbone — store/retrieve project knowledge"
author: Synapse Enterprise
provides_tools:
  - synapse_health
  - synapse_store
  - synapse_retrieve
  - synapse_update
  - synapse_delete
  - synapse_context
  - synapse_rank
provides_hooks: []
requires_env:
  - name: SYNAPSE_API_KEY
    description: "Tenant API key (leave empty for single-tenant mode)"
    secret: true
  - name: SYNAPSE_SERVER_URL
    description: "MCP server URL"
    default: "http://100.91.55.113:8765/mcp"
```

**Rules:**
- `provides_tools` names must match function names in `tools.py` AND dict key names in `schemas.py`
- `requires_env` gates plugin loading — plugin disabled if missing env vars
- If `secret: true`, Hermes prompts the user during install to set the value

## schemas.py — Tool Descriptions

Each tool is a dict following OpenAI tool format:

```python
SYNAPSE_STORE = {
    "name": "synapse_store",
    "description": (
        "Store a durable memory (convention, gotcha, architecture decision, "
        "fix, command, or note). Memories persist across sessions and devices."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The memory content text",
            },
            "kind": {
                "type": "string",
                "enum": ["working", "episodic", "semantic"],
                "description": "Memory kind",
                "default": "semantic",
            },
            "importance": {
                "type": "number",
                "description": "Importance 0.0-1.0",
                "minimum": 0.0, "maximum": 1.0, "default": 0.5,
            },
        },
        "required": ["content"],
    },
}
```

**The `description` field is the most critical** — the LLM reads it to decide
when to call the tool. Be specific about use cases.

## tools.py — Tool Handlers

Each function receives `(args: dict, **kwargs)` and MUST return a JSON string:

```python
import json
import os
import time
from urllib.request import Request, urlopen

SERVER_URL = os.environ.get("SYNAPSE_SERVER_URL", "http://100.91.55.113:8765/mcp")
API_KEY = os.environ.get("SYNAPSE_API_KEY", "")

_session_id = None
_session_expiry = 0

def _call_mcp(tool: str, args: dict) -> dict:
    """Make an MCP tool call with session caching."""
    global _session_id, _session_expiry
    now = time.time()

    # Initialize session if needed
    if not _session_id or now > _session_expiry:
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "hermes-plugin", "version": "1.0"},
            },
        }).encode("utf-8")
        req = Request(SERVER_URL, data=body,
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
        with urlopen(req) as resp:
            _session_id = resp.headers.get("mcp-session-id", "")
            _session_expiry = now + 840  # 14 min

    call_args = dict(args)
    if API_KEY:
        call_args["api_key"] = API_KEY

    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": call_args},
    }).encode("utf-8")

    req = Request(SERVER_URL, data=body,
                  headers={"Content-Type": "application/json",
                           "Accept": "application/json",
                           "Mcp-Session-Id": _session_id})
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "error" in data:
        return {"error": data["error"].get("message", str(data["error"]))}
    result = data.get("result", {})
    content = result.get("content", [])
    if content:
        try:
            return json.loads(content[0]["text"])
        except (json.JSONDecodeError, KeyError):
            return {"error": "Failed to parse response"}
    return result.get("structuredContent", {})


def synapse_store(args: dict, **kwargs) -> str:
    """Store a memory."""
    content = args.get("content", "").strip()
    if not content:
        return json.dumps({"error": "No content provided"})
    result = _call_mcp("store", {
        "project_key": args.get("project_key", "default"),
        "kind": args.get("kind", "semantic"),
        "content": content,
        "importance": args.get("importance", 0.5),
    })
    if result.get("ok"):
        return json.dumps({"memory_id": result["memory_id"],
                           "version": result.get("version", 1),
                           "message": "Memory stored"})
    return json.dumps({"error": result.get("error", "Store failed")})
```

**Handler rules:**
1. Receive args dict — the parameters the LLM passed
2. Do the work (call MCP server, process data)
3. Return a JSON string — ALWAYS, even on error
4. Accept `**kwargs` for forward compatibility
5. Cache MCP sessions globally (module-level variables persist across tool calls within a session)

## Key Differences from OpenClaw Plugin

| Aspect | Hermes | OpenClaw |
|--------|--------|----------|
| Language | Python | TypeScript |
| Manifest | `plugin.yaml` | `openclaw.plugin.json` |
| Entry point | `tools.py` function | `src/index.ts` `registerTool()` |
| Schema format | Python dict (OpenAI tool format) | TypeBox objects |
| Tool descriptions | In `schemas.py` | In the `parameters` field of tool def |
| Session caching | Module-level globals | Map with TTL check |
| Install dir | `~/.hermes/plugins/<name>/` | `openclaw/extensions/<name>/` |
| Env config | `requires_env` in plugin.yaml | `configSchema` + env vars |

## Pitfalls

- **MCP sessions are per-process**: Module-level globals persist within a Hermes session. They reset when Hermes restarts, which is fine — sessions auto-reinitialize on first call.
- **Error handling**: Always wrap MCP calls in try/except and return JSON string with error field. If an exception escapes the handler, Hermes logs a traceback but the tool call appears broken to the LLM.
- **Returns must be JSON strings**: Hermes tool handlers must return `str` (JSON). Returning a dict or list causes a silent error.
- **File names are fixed**: Hermes expects exactly `schemas.py` and `tools.py`. No other naming convention works.
