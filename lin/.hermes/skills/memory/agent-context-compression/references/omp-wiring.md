# oh-my-pi (omp) Headroom + Agentmemory Wiring

## Discovery Mechanisms

omp discovers MCP servers through multiple providers:

| Provider | Source | Priority | Scope |
|----------|--------|----------|-------|
| Claude Plugin | `~/.claude/plugins/*/plugin.json` | High | User |
| omp Extension | `~/.omp/extensions/*/.mcp.json` | High | User |
| MCP JSON | `{cwd}/.mcp.json` or `{cwd}/mcp.json` | Low (5) | Project |
| Builtin | Bundled discovery | Medium | Built-in |

## Extension Structure

```
~/.omp/extensions/ciphercompress/
├── .mcp.json                    # MCP server configs
└── skills/ → (symlink)          # Skills directory
```

The `.mcp.json` format:
```json
{
  "mcpServers": {
    "agentmemory": {
      "command": "npx",
      "args": ["-y", "@agentmemory/mcp"],
      "env": {"AGENTMEMORY_URL": "http://100.93.75.87:3111"},
      "enabled": true
    },
    "headroom-compress": {
      "command": "/usr/bin/python3",
      "args": ["-m", "headroom.cli.mcp", "serve"],
      "enabled": true
    }
  }
}
```

## Config Registration

Add to `~/.omp/agent/config.yml`:
```yaml
extensions:
  - ciphercompress
```

## Package Manager

omp uses **bun** exclusively. Repo uses `bun.lock` and `catalog:` protocol in
package.json which is bun-specific. npm cannot resolve `catalog:` entries:
```
npm error Unsupported URL Type "catalog:": catalog:
```

Install omp dependencies:
```bash
cd oh-my-pi
bun install
```

Run omp:
```bash
bun run dev                    # from repo root
# or after linking:
omp "your task here"
```

## Verification

After setup, omp should discover both MCP servers:
```
# If omp has a tool listing command, it should show agentmemory and headroom-compress
# Agentmemory endpoints:
POST http://100.93.75.87:3111/agentmemory/remember  → 201
POST http://100.93.75.87:3111/agentmemory/search    → 200

# Headroom compression:
headroom compress "test"  → compressed output
```
