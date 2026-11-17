# Hermes MCP Wrapper Plugin — Worked Example

This reference documents the Synapse Memory Hermes plugin as a concrete
example of wrapping an external MCP server as a Hermes plugin.

## Source

The complete plugin lives at `/home/lin/synapse-mcp/plugins/hermes-synapse/`.
It was installed into `~/.hermes/plugins/synapse-memory/` via `cp -r`.

## Three-File Layout

```
~/.hermes/plugins/synapse-memory/
├── plugin.yaml       # Manifest
├── schemas.py        # 7 tool schemas
└── tools.py          # Handlers proxying to MCP server
```

## plugin.yaml

```yaml
name: synapse-memory
version: 1.0.0
description: "Synapse Memory — persistent AI memory backbone across sessions and devices."
author: Synapse Enterprise
provides_tools:
  - synapse_health
  - synapse_store
  - synapse_retrieve
  - synapse_update
  - synapse_delete
  - synapse_context
  - synapse_rank
  - synapse_memory
provides_hooks: []
requires_env:
  - name: SYNAPSE_API_KEY
    description: "Synapse tenant API key (leave empty for single-tenant mode)"
    secret: true
    url: "http://100.91.55.113:8765/mcp"
```

## MCP Session Management (tools.py)

The core pattern for calling any MCP server from a Hermes plugin:

```python
import json, os, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Read config from env vars
SERVER_URL = os.environ.get("SYNAPSE_SERVER_URL", "http://100.91.55.113:8765/mcp")
API_KEY = os.environ.get("SYNAPSE_API_KEY", "")

# Global session cache (per-process)
_session_id = None
_session_expiry = 0

def _call_server(tool: str, args: dict) -> dict:
    """Make an MCP tool call with automatic session management."""
    global _session_id, _session_expiry

    # 1. Initialize or reuse MCP session
    now = time.time()
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
            _session_expiry = now + 840  # refresh after 14 min

    # 2. Inject auth if configured
    call_args = dict(args)
    if API_KEY:
        call_args["api_key"] = API_KEY

    # 3. Call the tool
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": call_args},
    }).encode("utf-8")
    req = Request(SERVER_URL, data=body,
        headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "Mcp-Session-Id": _session_id,
        })
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}"}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}

    if "error" in data:
        return {"error": data["error"].get("message", str(data["error"]))}

    # 4. Parse response content
    content = data.get("result", {}).get("content", [])
    if content:
        try:
            return json.loads(content[0]["text"])
        except (json.JSONDecodeError, KeyError):
            return {"error": "Failed to parse response"}
    return {}

## Handler Pattern

Each tool handler follows this pattern:

```python
def synapse_store(args: dict, **kwargs) -> str:
    try:
        content = args.get("content", "").strip()
        if not content:
            return json.dumps({"error": "No content provided"})
        result = _call_server("store", {
            "project_key": args.get("project_key", "default"),
            "kind": args.get("kind", "semantic"),
            "content": content,
            "tags": args.get("tags", []),
            "importance": args.get("importance", 0.5),
        })
        if result.get("ok"):
            return json.dumps({
                "memory_id": result["memory_id"],
                "version": result.get("version", 1),
                "message": f"Memory stored (v{result.get('version', 1)})",
            })
        return json.dumps({"error": result.get("error", "Store failed")})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

## Key Patterns

1. **Session caching**: Store session ID globally with a 14-minute TTL
2. **Shared `_call_server`**: One function handles all MCP calls — auth, session, errors
3. **Return JSON strings always**: Hermes tool handlers must return `str` (JSON)
4. **Error wrapping**: Catch all exceptions, return `{"error": "..."}` JSON
5. **Null-safe responses**: `result.get("ok")` for safe truthiness checks
