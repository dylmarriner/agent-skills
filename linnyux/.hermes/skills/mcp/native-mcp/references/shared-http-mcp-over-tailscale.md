# Shared HTTP MCP server over Tailscale

Use this pattern when the user wants one free/local MCP capability (for example shared memory) available to Hermes plus other agents/devices such as Windsurf, Antigravity, OpenClaw, Paperclip, or remote machines.

## Durable pattern

1. Run the MCP server as a user systemd service on the machine that owns the data.
2. Bind the HTTP listener to all interfaces or the Tailscale interface, not only `127.0.0.1`, if other devices must connect.
3. Use the machine's Tailscale IPv4 address in all cross-device client configs.
4. Configure Hermes under `mcp_servers` with a URL ending in the server's MCP path, usually `/mcp`.
5. Fully restart Hermes after editing config; `/reset` is not enough for MCP discovery.
6. Verify from both sides: local loopback, Tailscale URL from a second device, MCP handshake/tool list, then one real tool call.

## Hermes config shape

```yaml
mcp_servers:
  synapse:
    url: "http://100.x.y.z:8765/mcp"
    timeout: 120
    connect_timeout: 30
```

Tool names appear as `mcp_<server>_<tool>`, for example `mcp_synapse_recall`.

## Generic client config shape

Most editor/agent clients accept one of these:

```json
{
  "mcpServers": {
    "synapse": {
      "url": "http://100.x.y.z:8765/mcp"
    }
  }
}
```

If the client requires an explicit transport:

```json
{
  "mcpServers": {
    "synapse": {
      "transport": "http",
      "url": "http://100.x.y.z:8765/mcp"
    }
  }
}
```

## Systemd user service checks

```bash
systemctl --user status synapse-mcp.service
systemctl --user restart synapse-mcp.service
journalctl --user -u synapse-mcp.service -f
```

If the service must survive logout on a non-desktop/server account, enable linger:

```bash
sudo loginctl enable-linger "$USER"
```

## Verification checklist

- `systemctl --user status ...` is active/running.
- The process listens on the expected port and address.
- `curl http://127.0.0.1:<port>/...` reaches the local service.
- A second Tailscale device can reach `http://<tailscale-ip>:<port>/...`.
- `hermes mcp list` shows the server after restart.
- MCP tools are visible with the expected `mcp_<server>_` prefix.
- A real write/read or health/check tool call succeeds end-to-end.

## Pitfalls

- Do not advertise `127.0.0.1` to other devices; it points at the client device, not the server.
- Do not stop at a raw HTTP health check. Confirm MCP initialize/list_tools and at least one real tool call.
- If tools do not appear after editing `~/.hermes/config.yaml`, fully exit and relaunch Hermes.
- Avoid rewriting the entire Hermes YAML with generic serializers; use targeted edits or append the `mcp_servers` block carefully to preserve ordering and comments.
