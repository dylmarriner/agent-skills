# MCP Config Migration Guide

How to translate MCP server configurations from other tools into Hermes' `~/.hermes/config.yaml` format.

## Common Formats

### Windsurf (`~/.codeium/windsurf/mcp_config.json`)

Windsurf uses JSON with `mcpServers` key, where servers can specify `registry` and `env`:

```json
{
  "mcpServers": {
    "io.windsurf/filesystem": {
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "command": "npx",
      "env": { "FILESYSTEM_PATHS": "/" },
      "registry": "io.windsurf/filesystem"
    }
  }
}
```

**Migration:**
- Rename keys with dots/slashes (e.g. `io.windsurf/filesystem` → `windsurf-filesystem`)
- Keep `command` and `args` as-is
- The `registry` field is Windsurf-specific — drop it
- Move `env` contents directly into the Hermes server entry under `env:`
- If the server was `disabled: false`, just include it (Hermes doesn't have a per-server disable toggle)

```yaml
mcp_servers:
  windsurf-filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/"]
```

### Cursor (`~/.cursor/mcp.json`)

Cursor uses the same JSON format as Windsurf:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_..." }
    }
  }
}
```

**Migration:**
- Nearly identical mapping — rename if needed (usually they're already clean names)
- `command`, `args`, `env` map 1:1 into Hermes config

### VS Code (`~/.vscode/mcp.json` or workspace `.vscode/mcp.json`)

Same JSON format, same mapping.

### Claude Desktop (`claude_desktop_config.json`)

Same format again. Some configs use `disabled` flags — just omit disabled servers.

## Key Differences

| Aspect | Windsurf/Cursor/VS Code | Hermes Agent |
|--------|------------------------|--------------|
| Config file | `mcp_config.json` / `mcp.json` | `~/.hermes/config.yaml` |
| Config key | `mcpServers` (JSON) | `mcp_servers:` (YAML) |
| Server names with dots/slashes | Allowed (`io.windsurf/filesystem`) | Not recommended — rename |
| Per-server disable | `"disabled": true` | Not supported — omit entry |
| `registry` field | Windsurf/Cursor-specific | Not used — drop it |
| Env var passing | Full parent env | Filtered (safe baseline only) — declare needed vars explicitly under `env:` |
| Hot-reload | Yes (some tools) | No — full agent restart required |
| Tool naming | Original tool names | Prefixed: `mcp_{server}_{tool}` |

## Common Servers

| Server | Command | Notes |
|--------|---------|-------|
| Filesystem | `npx -y @modelcontextprotocol/server-filesystem /path` | Pass allowed directories as positional args |
| GitHub | `npx -y @modelcontextprotocol/server-github` | Requires `GITHUB_TOKEN` env var |
| Memory | `npx -y @modelcontextprotocol/server-memory` | No auth needed |
| PDF | `npx -y @modelcontextprotocol/server-pdf` | No auth needed |
| Time | `uvx mcp-server-time` | No auth needed |
| Puppeteer | `npx -y @modelcontextprotocol/server-puppeteer` | Requires Chromium |
| Brave Search | `npx -y @modelcontextprotocol/server-brave-search` | Requires `BRAVE_API_KEY` env var |
