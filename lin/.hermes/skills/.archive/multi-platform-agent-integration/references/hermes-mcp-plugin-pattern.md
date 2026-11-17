# Hermes Plugin with MCP Proxy Pattern

A Hermes plugin that proxies to an external MCP server.

## Files

```
~/.hermes/plugins/<name>/
├── plugin.yaml      # Manifest
├── schemas.py       # Tool schemas (LLM-facing)
└── tools.py         # Tool handlers → MCP server calls
```

## Tool Handler Pattern

Each handler:
1. Accepts `args: dict, **kwargs`
2. Builds MCP call args with auth
3. Manages MCP session (initialize, cache session ID with TTL)
4. Calls the MCP server via `urllib.request`
5. Returns a JSON string (always, even on error)

## Session Management

```python
import time, json
from urllib.request import Request, urlopen

_session_id = None
_session_expiry = 0

def _ensure_session(server_url: str) -> str:
    global _session_id, _session_expiry
    now = time.time()
    if _session_id and now < _session_expiry:
        return _session_id
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "hermes-plugin", "version": "1.0"}},
    }).encode()
    req = Request(server_url, data=body,
                  headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urlopen(req) as resp:
        _session_id = resp.headers.get("mcp-session-id", "")
        _session_expiry = now + 840  # 14 min (refresh before 15min expiry)
    return _session_id
```

## Tool Call Pattern

```python
def _call_server(server_url: str, tool: str, args: dict) -> dict:
    session_id = _ensure_session(server_url)
    call_args = dict(args)
    if API_KEY: call_args["api_key"] = API_KEY
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": call_args},
    }).encode()
    req = Request(server_url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "Mcp-Session-Id": session_id})
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if "error" in data:
        return {"error": data["error"].get("message", str(data["error"]))}
    result = data.get("result", {})
    content = result.get("content", [])
    if content:
        try: return json.loads(content[0]["text"])
        except: return {"error": "Parse failure"}
    return result.get("structuredContent", {})
```

## Tool Handler

```python
def my_tool(args: dict, **kwargs) -> str:
    try:
        result = _call_server(SERVER_URL, "my_tool", {
            "param": args.get("param"),
        })
        if result.get("ok"):
            return json.dumps({"status": "ok", "data": result.get("data")})
        return json.dumps({"error": result.get("error", "Failed")})
    except Exception as e:
        return json.dumps({"error": str(e)})
```
