# SSE MCP Server with Auth Headers

Some MCP servers (e.g., Synapse Memory) use SSE transport with
 bearer-token auth headers rather than the default streamable-HTTP
 transport. This is common for Docker-deployed memory backends.

## Windsurf / Antigravity Config Format

The `serverUrl` + `headers` format is used for SSE-based MCP servers:

```json
{
  "mcpServers": {
    "synapse-memory": {
      "headers": {
        "Authorization": "Bearer <token>"
      },
      "serverUrl": "http://<TAILSCALE_IP>:7777/mcp/sse"
    }
  }
}
```

Key differences from regular (streamable-http) MCP config:
- Uses `serverUrl` (not `url`) — indicates SSE transport
- Uses `headers` for auth — no env var or API key field
- Endpoint path is `/mcp/sse` — the SSE-specific route

## Hermes Config (stdio adapter)

For Hermes, SSE MCP servers are typically bridged via a stdio adapter
script that handles the SSE connection and auth internally:

```yaml
mcp_servers:
  nexus-memory:
    command: python3
    args:
      - /path/to/synapse-memory/scripts/adapters/nexus_mcp_stdio.py
    env:
      NEXUS_URL: http://100.93.75.87:7777
      NEXUS_SECRET: <shared-key>
      NEXUS_AGENT_ID: hermes
```

## Cross-Machine Config Sync Pattern

When the same MCP server is used across multiple machines (e.g., laptop
+ remote server), copy the SSE config entry between machines. The
Tailscale IP and auth token should be identical if both machines are on
the same tailnet.

Steps:
1. SSH to the remote machine and `cat` the Windsurf/Antigravity MCP config
2. Extract the `synapse-memory` (or similar) entry with its `serverUrl` and `headers`
3. Add that entry to the local machine's MCP config using the same URL and token
4. Restart the IDE to pick up the new server
