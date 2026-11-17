# Hetzner MCP Server Setup

If a pre-built `@modelcontextprotocol/server-hetzner` package is not available in the public npm registry, follow these steps to use a custom or local binary.

1. Locate the binary path (e.g., via `which mcp-hetzner`).
2. Update `~/.config/hermes/config.yaml` to include the server:

```yaml
mcp_servers:
  hetzner:
    command: "mcp-hetzner"
    args: ["--restriction", "read_only"]
```

3. Restart the Hermes agent process to apply the changes.
