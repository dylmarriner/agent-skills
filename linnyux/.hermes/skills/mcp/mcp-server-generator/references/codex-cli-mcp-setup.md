# Codex CLI MCP Setup & Streamable HTTP Workaround

## Config Format vs Other Clients

Codex CLI does **not** use the standard `mcp_config.json` (JSON with `{"mcpServers": {...}}`).
Instead it uses its own TOML-based config at `~/.codex/config.toml` under `[mcp_servers.<name>]`,
managed via the `codex mcp add` CLI.

| Client | Config file | Key | CLI command |
|--------|-------------|-----|-------------|
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.<name>]` | `codex mcp add <name> [--url URL \| -- <command>...]` |
| Cline | `~/.cline/data/settings/cline_mcp_settings.json` | `mcpServers.<name>` | `cline mcp install <name>` |
| Claude Code | `~/.codex/mcp_config.json` or project `mcp.json` | `mcpServers.<name>` | Manual file edit |

## Streamable HTTP Bug (Codex 0.142.x)

Codex CLI v0.142.4 has a known bug: when a streamable HTTP MCP server is configured
(added via `codex mcp add <name> --url <url>`), tool calls fail with:

```
pretooluse hook returned unsupported permission decision: allow
```

This happens because Codex's internal permission system receives an `allow` decision
from the streamable HTTP transport handler and doesn't know how to process it.

## Workaround: Stdio Proxy

The fix: instead of connecting to the HTTP MCP server directly, run a tiny local stdio
proxy that reads MCP JSON-RPC from stdin and forwards it as HTTP POST to the server.

### The Proxy Script

A minimal proxy (`~/.codex/mcp-servers/nexus_mcp_proxy.py`, also in this skill's `references/` dir):

```python
#!/usr/bin/env python3
import json, sys, urllib.request, urllib.error, os

URL = os.environ.get('MCP_URL', 'http://nexus:7777/mcp')
TOKEN = os.environ.get('MCP_TOKEN', '')
# ... handles initialize handshake + forwards everything else
```

The proxy does two things:
1. **Initialize handshake** — responds to MCP `initialize` with capabilities metadata
2. **Passthrough** — all other methods (`tools/list`, `tools/call`, etc.) forwarded as HTTP POST

### Register in Codex

```bash
codex mcp remove <name>                 # remove the broken streamable HTTP entry
codex mcp add <name> -- python3 ~/.codex/mcp-servers/proxy.py
```

Set `MCP_TOKEN` via `env` in config.toml:

```toml
[mcp_servers.nexus]
command = "python3"
args = ["/home/user/.codex/mcp-servers/proxy.py"]
env = { MCP_TOKEN = "your-bearer-token-here" }
enabled = true
startup_timeout_sec = 10
tool_timeout_sec = 60
```

### Register in Cline / Claude Code

These clients support `mcp_config.json` format directly, but can also use the stdio
proxy if needed:

```json
{
  "mcpServers": {
    "nexus": {
      "command": "python3",
      "args": ["/path/to/proxy.py"],
      "enabled": true
    }
  }
}
```

## Verification

Test the proxy standalone:

```bash
printf '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{...}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","method":"tools/list","id":2}\n' \
  | MCP_TOKEN=your-token python3 proxy.py
```

Expected output: initialize response + tools/list with the server's tool list.
