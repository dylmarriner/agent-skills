# Stdio-to-HTTP MCP Bridge Pattern

When you need to expose an HTTP-based MCP endpoint through the tunnel-client (which requires stdio MCP), build a lightweight Python bridge.

## How It Works

```
tunnel-client (stdio)  ←→  bridge.py (stdin/stdout)  ←→  HTTP POST →  remote MCP endpoint
```

The bridge:
1. Reads JSON-RPC messages from stdin (the MCP stdio protocol)
2. For `tools/list`: responds from a cached discovery result (fetched once at startup)
3. For `tools/call`: proxies the request as HTTP POST to the remote endpoint
4. For `initialize`: responds with capabilities declaring `{"tools": {}}`
5. For `notifications/initialized`: no response needed (JSON-RPC notification)
6. Logs everything to stderr so stdio stays protocol-clean

## Minimal Template

```python
#!/usr/bin/env python3
import json, sys, urllib.request, re

# ── Config ──
REMOTE_URL = "http://host:port/mcp"
SECRET = "bearer-token-here"

def log(msg):
    sys.stderr.write(f"[bridge] {msg}\n"); sys.stderr.flush()

def proxy(method, params):
    """Send JSON-RPC to the remote HTTP endpoint."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
    headers = {"Content-Type": "application/json"}
    if SECRET:
        headers["Authorization"] = f"Bearer {SECRET}"
    try:
        req = urllib.request.Request(REMOTE_URL, data=body, headers=headers)
        return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    except Exception as e:
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": str(e)}}

# Discover tools at startup
tools_cache = proxy("tools/list", {}).get("result", {}).get("tools", [])
log(f"discovered {len(tools_cache)} tools")

# MCP stdio loop
for line in sys.stdin:
    msg = json.loads(line.strip())
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params", {})

    if method == "initialize":
        resp = {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "my-bridge", "version": "1.0.0"},
            "capabilities": {"tools": {}}}}
    elif method == "tools/list":
        resp = {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools_cache}}
    elif method == "tools/call":
        result = proxy("tools/call", {"name": params["name"], "arguments": params.get("arguments", {})})
        resp = {"jsonrpc": "2.0", "id": mid, **result}
    elif method == "notifications/initialized":
        continue  # no response
    else:
        resp = {"jsonrpc": "2.0", "id": mid, "result": {}}

    sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()
```

## Key Points

- **Tool discovery is one-shot**: Fetch at startup, cache for the lifetime of the bridge. The remote endpoint rarely changes tools mid-session.
- **Initialize response is critical**: Without declaring capabilities, the tunnel-client won't consider the bridge ready.
- **Stdio must be clean**: Never print to stdout except JSON-RPC responses. Route all logging to stderr.
- **Auth via file/env**: For secrets, read from a `.env` file at startup rather than hardcoding — keeps the tunnel config clean.
- **No notification responses**: `notifications/initialized` and similar JSON-RPC notifications get no reply.

## Tunnel Config Entry

```yaml
mcp:
  commands:
    - channel: nexus
      command: "python3 /path/to/bridge.py"
```
