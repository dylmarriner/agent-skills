---
name: multi-platform-agent-integration
description: "Build and package plugins/extensions for multiple AI agent platforms (Hermes, OpenClaw, Paperclip, VS Code, Windsurf, Antigravity) around an MCP server core."
version: 2.0.0
author: Hermes Agent
---

# Multi-Platform Agent Integration

Architect and build plugins/extensions for multiple AI agent platforms
around a central MCP server. Each platform has its own plugin format,
manifest schema, and installation path. This skill covers all of them.

## When to Use

- Building a service that needs to integrate with 2+ agent platforms
- Creating plugins for Hermes, OpenClaw, Paperclip, or VS Code forks
- Adding MCP server configuration to Windsurf or Antigravity IDE
- Packaging a multi-platform integration project
- Deploying the MCP server and client configs across multiple machines

## Complete Delivery Checklist

When the user asks for "the whole system" or "everything" or "production grade":

- [ ] MCP server (all tools working, systemd service)
- [ ] Hermes plugin (plugin.yaml + schemas.py + tools.py)
- [ ] OpenClaw plugin (openclaw.plugin.json + package.json + src/)
- [ ] Paperclip plugin (manifest.json + package.json + worker.ts)
- [ ] VS Code/IDE extension (package.json + extension.ts)
- [ ] Windsurf MCP config
- [ ] Antigravity MCP config
- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] Client configs documentation
- [ ] Install/deploy scripts
- [ ] Systemd service file
- [ ] Full README
- [ ] Git init + GitHub publish

Do not omit items or treat any as optional unless explicitly stated.
If the user later asks "what about X?" and X was on this list, that's a
missed deliverable — complete delivery means everything in one pass.

## Project Structure Rule (CRITICAL — user preference)

**Do NOT build plugins directly into the target project's source tree.**
Each plugin lives as a self-contained, distributable package inside your
own project, under `plugins/<platform>-<name>/`.

```
your-project/
├── server.py                     # MCP server (the core)
├── plugins/
│   ├── hermes-synapse/           # Hermes plugin (distributable package)
│   ├── openclaw-synapse/         # OpenClaw plugin (distributable package)
│   └── paperclip-synapse/        # Paperclip plugin (distributable package)
├── ides/
│   ├── extension/                # VS Code extension (distributable .vsix)
│   ├── windsurf/mcp_config.json  # Windsurf MCP config
│   └── antigravity/mcp_config.json # Antigravity MCP config
├── sdk/                          # Client SDKs
├── client-configs/               # All client configs
├── scripts/install.sh            # Install script
└── systemd/                      # Service files
```

Do NOT put plugin files directly into `openclaw/extensions/`,
`~/.hermes/plugins/`, or any platform-specific directory during
development. Those are installation targets, not development locations.
Use a `scripts/install-*.mjs` or `plugins/*/scripts/install-*.mjs`
file to copy the plugin to its target at install time.

## MCP Server Core

The MCP server is the single backend. All plugins proxy to it.

```python
# server.py uses FastMCP with streamable-http transport
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("My Service", json_response=True, host=HOST, port=PORT)
mcp.run(transport="streamable-http")
```

### MCP Session Management

MCP streamable-HTTP requires session initialization:
1. Client sends `initialize` request
2. Server responds with `mcp-session-id` header
3. All subsequent requests include `Mcp-Session-Id` header
4. Sessions expire after ~15 minutes; re-initialize as needed

### FastMCP API Key Redaction

FastMCP v1.27.1 automatically redacts fields named `api_key`, `secret`,
`password`, `token`, or any value matching patterns like `sk_...` in
structured content output. This means API keys returned from tool calls
get truncated with `...` even in `content[0].text`.

**Workaround**: Use an alternative field name like `"key"` instead of
`"api_key"` in the return dict, AND change the API key prefix from
`sk_syn_` to something that doesn't trigger the pattern matcher (e.g.,
`syn_`). Both changes are needed:
- Field name change prevents structuredContent redaction
- Prefix change prevents JSON serialization redaction in content text

## Platform Plugin Formats

### Hermes Plugin (Python)

| File | Purpose |
|------|---------|
| `plugin.yaml` | Manifest: name, version, provides_tools, provides_hooks, requires_env |
| `schemas.py` | Tool schemas (what the LLM sees to decide when to call) |
| `tools.py` | Tool handlers (Python functions returning JSON strings) |

Install target: `~/.hermes/plugins/<name>/`

**plugin.yaml**:
```yaml
name: my-plugin
version: 1.0.0
description: "Description"
provides_tools:
  - my_tool
requires_env:
  - name: MY_API_KEY
    secret: true
```

**schemas.py** — each tool is a JSON schema dict:
```python
MY_TOOL = {
    "name": "my_tool",
    "description": "What this tool does",
    "parameters": {
        "type": "object",
        "properties": {...},
        "required": [...],
    },
}
```

**tools.py** — each handler receives args + **kwargs, returns JSON string:
```python
def my_tool(args: dict, **kwargs) -> str:
    result = do_something(args.get("param"))
    return json.dumps({"status": "ok", "data": result})
```

For MCP-backed Hermes plugins, handlers call the MCP server via
`urllib.request` with session management built in. See
`references/hermes-mcp-plugin-pattern.md`.

### OpenClaw Plugin (TypeScript)

| File | Purpose |
|------|---------|
| `openclaw.plugin.json` | Manifest: id, contracts, configSchema, uiHints |
| `package.json` | npm package with `openclaw` block |
| `src/index.ts` | Plugin entry using `definePluginEntry` + `register` |
| `skills/<name>/SKILL.md` | Agent guidance |

Tools register via `api.registerTool()` which takes a factory function
and a `{ name }` metadata object. The factory receives a tool context
and returns an `AnyAgentTool` with `{ name, label, description, parameters, execute }`.

Agent guidance hooks via `api.on("before_prompt_build", ...)`.

The tool's `execute` function receives `(_toolCallId, rawParams)` and
must return `{ content: [{ type: "text", text: "..." }], isError: bool }`.

OpenClaw auto-discovers plugins from its `extensions/` directory based
on `package.json` + `openclaw.plugin.json`. The install script should copy
the plugin into the OpenClaw extensions directory.

### Paperclip Plugin (TypeScript)

| File | Purpose |
|------|---------|
| `manifest.json` | Tool definitions (name, params, descriptions) |
| `package.json` | npm package |
| `src/worker.ts` | Plugin using `definePlugin` from `@paperclipai/plugin-sdk` |

Paperclip uses the adapter plugin model. Plugins are loaded via
`~/.paperclip/adapter-plugins.json` and registered through
Board → Adapter manager. The SDK provides `definePlugin({ setup,
onHealth, onShutdown })` where `setup` receives a `PluginContext`
with `ctx.tools.register()`, `ctx.events.on()`, `ctx.jobs.register()`.

### VS Code / Windsurf / Antigravity Extension (TypeScript)

Standard VS Code extension with host detection. Build as a `.vsix`
package installable in all three IDEs.

**package.json** must include:
- `activationEvents: ["onStartupFinished"]`
- `main: "./dist/extension.js"`
- `contributes.commands`, `contributes.configuration`, `contributes.viewsContainers`

**Extension activation** should:
1. Detect which IDE it's running in via `vscode.env.appName`
2. Write the MCP config to the correct path for that IDE
3. Register commands and status bar items
4. Check server health on activation

**IDE detection**:
```typescript
function detectHost() {
  const app = vscode.env.appName.toLowerCase();
  if (app.includes("windsurf") || app.includes("codeium"))
    return "windsurf";
  if (app.includes("antigravity") || app.includes("gemini"))
    return "antigravity";
  return "vscode";
}
```

## IDE MCP Config Paths

| IDE | Config Path | JSON Key |
|-----|-------------|----------|
| VS Code | `~/.vscode/mcp.json` | `servers` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` | `mcpServers` |

The MCP config format (streamable-HTTP):
```json
{
  "mcpServers": {
    "synapse": {
      "url": "http://<TAILSCALE_IP>:8765/mcp",
      "timeout": 120,
      "connect_timeout": 30
    }
  }
}
```

The MCP config format (SSE with auth headers — used by Synapse Memory and similar):
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

## Production-Grade Delivery

When the user asks for a complete system ("build the entire system",
"production grade code"), deliver everything in one pass:

- MCP server (all tools working)
- All platform plugins as self-contained packages
- Install scripts for each platform
- Client SDKs (Python + TypeScript)
- Systemd service file
- IDE configs (Windsurf, Antigravity, VS Code)
- Full README with usage examples
- Git init + GitHub publish

Do NOT build phases incrementally unless explicitly asked. "Fix everything"
means all of it right now. Use the **Complete Delivery Checklist** at the
top of this skill to verify nothing is missed.

## Single-Tenant vs Multi-Tenant Mode

The MCP server supports two modes, configured via `SYNAPSE_TENANT_LIMIT`:

| Mode | `TENANT_LIMIT` | API Key Required | Use Case |
|------|---------------|-----------------|----------|
| Single-tenant | `0` | No | Personal/dashboard use, cross-machine shared memory |
| Multi-tenant | `> 0` (default: 100) | Yes | SaaS, multiple organizations |

**Critical deployment pitfall**: In single-tenant mode, the server must have
a default tenant that actually exists in the database. The `_seed_default_tenant()`
function runs on startup and uses `INSERT OR IGNORE`, so on subsequent restarts
it doesn't re-create a missing default tenant. **Always delete the SQLite DB
when switching mode**, or patch `_ensure_tenant()` to auto-create the default
tenant on any function call that checks for it:

```python
def _ensure_tenant(con, tenant_id):
    row = con.execute("SELECT status FROM tenants WHERE tenant_id=?", (tenant_id,)).fetchone()
    if row is None and TENANT_LIMIT <= 0:
        con.execute("INSERT OR IGNORE INTO tenants(...) VALUES (...) WITH api_key FOR DEFAULT TENANT", ...)
        return True
    return row and row["status"] == "active"
```

**Dashboard implication**: The dashboard's `/api/search` and other endpoints
proxy MCP calls without an API key. In multi-tenant mode, these calls fail
with "Authentication required" or "Tenant not found or suspended". Always
run the dashboard alongside a single-tenant MCP server.

## Cross-Machine Deployment

After building the system, deploy it across multiple machines via
Tailscale. See `references/cross-machine-deployment.md` for full details.

### Architecture

One machine runs the Synapse MCP server (the "central brain"). All other
machines run plugins and clients that connect to it over Tailscale.

```
SERVER (Tailscale IP: 100.x.y.z)     ← MCP server on port 8765
  → CLIENT (any Tailscale node)      ← Hermes/Windsurf/Antigravity → SERVER_IP
  → CLIENT (any Tailscale node)      ← Point ALL clients to SERVER_IP
```

### Server Setup

1. Clone repo, `python3 -m venv .venv`, `pip install mcp numpy ulid-py zstandard cryptography PyJWT`
2. Create systemd service in `~/.config/systemd/user/synapse-mcp.service`
3. Start with `systemctl --user enable --now synapse-mcp`
4. Verify with MCP initialize curl command

### Client Setup (per machine)

1. Install Hermes plugin: copy files to `~/.hermes/plugins/synapse-memory/`
2. Add MCP server to `~/.hermes/config.yaml` pointing to SERVER_IP
3. Add synapse to Windsurf/Antigravity MCP configs if those IDEs exist
4. Verify: `curl http://<SERVER_IP>:8765/mcp` with MCP initialize

### Verification

Store a memory from one machine, retrieve it from another:
```python
c = SynapseClient(server_url='http://<SERVER_TS_IP>:8765/mcp')
c.store(kind="semantic", content="test")
c.retrieve("test")  # Should return the memory stored from any machine
```

## MCP Dashboard / Web UI

After building the MCP server and plugins, create a web UI dashboard for
visual management. Pattern: lightweight Python HTTP proxy that wraps MCP
calls into REST endpoints and serves a single-page HTML frontend.

### Architecture

```
Browser ──HTTP──► Dashboard Server ──MCP──► MCP Server
                 (port 8767)               (port 8765)
```

### REST Endpoints

| Endpoint | Method | MCP Call | Purpose |
|----------|--------|----------|---------|
| `/api/status` | GET | `health` | Server info, memory count, Tailscale IP |
| `/api/search?q=X` | GET | `retrieve` | Ranked search results |
| `/api/store` | POST | `store` | Store a memory |
| `/api/delete` | POST | `delete` | Delete by ID |
| `/api/rank` | GET | `rank` | Importance-ranked list |

### Key Decisions

- **Use Python `http.server`** — no framework needed for a single-page app
- **Dynamic Tailscale IP** — detect with `subprocess.run(["tailscale", "status", "--json"])` at startup. Never hardcode an IP in the startup banner.
- **Single-file HTML** — no build step. Dark glassmorphism theme (`--bg-primary: #0a0a0f; --accent: #6c5ce7`), inline `<script>` for the API calls.
- **Session management server-side** — browsers can't do MCP handshakes. The dashboard manages one session and re-initializes on expiry.
- **Deploy on the same machine as the MCP server** — access via `http://<TAILSCALE_IP>:8767`
- **Restart the dashboard after server restart** — the dashboard's MCP session expires when the server restarts. Use `pkill -f dashboard.py && nohup python3 dashboard.py &` on the server machine.

## VS Code Extension Details

When building the VS Code extension (also works in Windsurf and Antigravity):

### package.json essentials

```json
{
  "activationEvents": ["onStartupFinished"],
  "main": "./dist/extension.js",
  "contributes": {
    "commands": [
      { "command": "synapse.store", "title": "Synapse: Store Memory" },
      { "command": "synapse.health", "title": "Synapse: Check Status" }
    ],
    "configuration": {
      "properties": {
        "synapse.serverUrl": { "type": "string", "default": "http://..." }
      }
    },
    "viewsContainers": { "activitybar": [...] },
    "views": { "synapse-sidebar": [...] }
  }
}
```

### extension.ts activation pattern

1. **Detect host** — `vscode.env.appName` → windsurf/codeium/antigravity/gemini
2. **Write MCP config** — based on detected host, write the correct config path
3. **Register commands** — health, store, retrieve, context, configure
4. **Status bar** — `vscode.window.createStatusBarItem` showing connected/disconnected
5. **Auto-sync** — optional `workspace.onDidSaveTextDocument` to store working memories
6. **Sidebar** — `TreeDataProvider` for memory overview

### IDE-specific MCP config paths

- Windsurf: `~/.codeium/windsurf/mcp_config.json` with key `mcpServers`
- Antigravity: `~/.gemini/antigravity/mcp_config.json` with key `mcpServers`
- VS Code: `~/.vscode/mcp.json` with key `servers`

Use a single install script (`install-to-ides.mjs`) that writes all three.

## GitHub Publishing

After completing development:

```bash
cd your-project
git init
git branch -M main
git add -A
git commit -m "Initial release: v0.1.0"
git remote add origin git@github.com:<user>/<repo>.git
# Use HTTPS if SSH keys aren't set up (gh CLI handles auth):
git remote set-url origin https://github.com/<user>/<repo>.git
git push -u origin main
```

Set up a `.gitignore` that excludes: `__pycache__/`, `.venv/`, `node_modules/`,
`.env`, `*.sqlite*`, `*.vsix`, `dist/`, `*.egg-info/`.

## References

See `references/` for:
- `hermes-mcp-plugin-pattern.md` — Hermes plugin with MCP proxy pattern
- `openclaw-plugin-entry.md` — OpenClaw plugin entry structure
- `fastmcp-redaction-workaround.md` — FastMCP API key redaction fix
- `cross-machine-deployment.md` — Multi-machine Tailscale deployment
- `sse-mcp-with-auth.md` — SSE MCP servers with auth headers (Windsurf/Antigravity/Hermes config patterns)
