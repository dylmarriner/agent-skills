# Nexus Hermes Plugin — Setup Reference

Full details from the integration session (28 Jun 2026).

## Architecture

```
Hermes Agent
  └── ~/.hermes/plugins/nexus-memory/      ← Hermes plugin (6 tools)
        ├── plugin.yaml                     ← tool definitions
        └── tools.py                        ← forwards calls via MCP
  └── ~/.hermes/nexus.env                   ← URL + secret
              ↓ MCP POST
Nexus Server (100.93.75.87:7777/mcp)
  ├── 69 MCP tools
  └── REST API at /v1/memory/*
```

The plugin is a thin proxy — each tool handler in `tools.py` constructs an MCP `tools/call` JSON-RPC request and POSTs it to Nexus. No direct DB access.

## Files

| File | Purpose |
|------|---------|
| `synapse-memory/integrations/plugins/hermes-nexus/plugin.yaml` | Plugin manifest (name, tools, env requirements) |
| `synapse-memory/integrations/plugins/hermes-nexus/tools.py` | 6 tool handlers forwarding to Nexus MCP |
| `~/.hermes/plugins/nexus-memory/` | Install destination (copy from above) |
| `~/.hermes/nexus.env` | Runtime env vars (NEXUS_URL, NEXUS_SECRET, NEXUS_AGENT_ID) |

## Env File Format

```
NEXUS_URL=http://100.93.75.87:7777/mcp
NEXUS_SECRET=<actual-secret>
NEXUS_AGENT_ID=hermes
```

Critical: `NEXUS_URL` must end with `/mcp` (the MCP POST endpoint), not the base URL. The default in `tools.py` is `http://100.93.75.87:7777/mcp` but the env file overrides it.

## Secret Handling

The nexus-install script suffered from redaction bugs — the secret written to nexus.env was truncated to ~6 chars (literal asterisks + partial suffix). Fix:

```python
from pathlib import Path
src = Path("/path/to/synapse-memory/.env")
dst = Path.home() / ".hermes" / "nexus.env"
for line in src.read_text().splitlines():
    if line.startswith("NEXUS_SECRET=") and "=" in line:
        secret = line.split("=", 1)[1]
dst.write_text(f"NEXUS_URL=http://<host>:7777/mcp\nNEXUS_SECRET={secret}\nNEXUS_AGENT_ID=hermes\n")
```

Never paste or echo the secret — the terminal redactor will truncate it.

## Verification

```bash
python3 -c "
import json, os
from urllib.request import Request, urlopen
secret = [l.split('=',1)[1] for l in open(os.path.expanduser('~/.hermes/nexus.env')) if l.startswith('NEXUS_SECRET=')][0]
body = json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}}).encode()
req = Request('http://<host>:7777/mcp', data=body, headers={'Content-Type':'application/json','Authorization':f'Bearer {secret}'})
tools = json.loads(urlopen(req, timeout=10).read())['result']['tools']
print(f'{len(tools)} tools available')
"
```

## Tools Available

From plugin.yaml:
- nexus_health — check server status
- nexus_store — save a memory
- nexus_recall — search memories (4-mode fused)
- nexus_context — get agent context pack
- nexus_learn — teach an agent
- nexus_reflect — LLM reflection over memories

These map to Nexus MCP tools (memory_save, memory_recall, agent_context, etc.).
