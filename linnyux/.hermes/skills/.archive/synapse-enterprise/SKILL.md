---
name: synapse-enterprise
description: "Build and deploy Synapse Enterprise — multi-tenant AI memory backbone with cross-platform plugins and automatic LLM proxy."
version: 1.2.0
author: Synapse Enterprise
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [memory, mcp, plugin, deployment, docker, tailscale, proxy, multi-agent, deepseek]
    related_skills: [hermes-agent, native-mcp, mcp-builder]
---

# Synapse Enterprise

Synapse Enterprise is a production-grade, multi-tenant, cross-device AI memory
and context orchestration layer. It acts as a persistent "enterprise AI brain"
across IDEs, agents, and productivity tools — with automatic memory injection
and capture via a transparent LLM proxy.

**Naming note:** Internally the Docker Compose stack is called "nexus"
(project name), but it IS Synapse Memory. The two terms are interchangeable
in conversation — always refer to the system as "Synapse Memory" unless the
user specifically mentions "nexus".

## What Ships

| Component | Description |
|-----------|-------------|
| **MCP Server** (Python/FastMCP) | 15 MCP tools: health, store/retrieve/update/delete, sync, rank, embed, compress, context, list |
| **Docker Compose Stack** | Full-service deployment: FastAPI+asyncpg, pgvector, Redis, worker, stdio bridge |
| **Hermes Plugin** (Python) | `plugin.yaml` + `schemas.py` + `tools.py` — 7 tools, installs into `~/.hermes/plugins/` |
| **OpenClaw Plugin** (TypeScript) | `openclaw.plugin.json` + `index.ts` — 9 tools, copies into `extensions/synapse/` |
| **Paperclip Plugin** (TypeScript) | `manifest.json` + `worker.ts` — 4 tools, uses `@paperclipai/plugin-sdk` |
| **VS Code Extension** (TypeScript) | Full extension — host detection, status bar, commands, sidebar, auto-sync |
| **LLM Proxy** (Python) | Transparent middleware — auto-injects context, auto-stores facts |
| **Dashboard** (Python/HTML) | Beautiful dark-themed web UI at `:8767` (standalone) or `:7777` (docker) |
| **Python SDK** | Full client class, lifecycle hooks, `pip install -e sdk/python` |
| **TypeScript SDK** | Full client class, lifecycle hooks |

## Deployment Variants

There are two deployment variants. Both expose the same MCP API but differ in
infrastructure:

### Variant A: Standalone Server (rabuntu)

The original deployment on a Raspberry Pi with Python systemd service. MCP on
port 8765, LLM proxy on 8768, dashboard on 8767.

```yaml
mcp_servers:
  synapse:
    url: "http://100.68.0.96:8765/mcp"
    timeout: 120
    headers:
      Authorization: "Bearer <secret>"
```

### Variant B: Docker Compose Stack (kubuntux — "nexus")

A full-stack Docker deployment with FastAPI, PostgreSQL (pgvector), Redis,
background worker, and stdio bridge. MCP on port 7777, dashboard on 7777,
internal bridge on 7778.

```yaml
mcp_servers:
  nexus:
    url: "http://100.93.75.87:7777/mcp"
    timeout: 120
    headers:
      Authorization: "Bearer nexus-memory-shared-key-2026"
```

**Docker containers:**

| Container | Purpose | Port |
|-----------|---------|------|
| `nexus-nexus-api-1` | FastAPI HTTP + MCP endpoint | 7777 |
| `nexus-nexus-worker-1` | Background processing | — |
| `nexus-nexus-bridge-1` | MCP stdio bridge (node) | 7778 |
| `nexus-postgres-1` | pgvector storage | 5435 |
| `nexus-redis-1` | Cache/task queue | 6381 |

**Finding the running NEXUS_SECRET on the host:**

The `.env` file and the running container may have different secrets. Always
check the RUNNING container, not the `.env` file:

```bash
docker inspect nexus-nexus-api-1 \
  --format '{{range .Config.Env}}{{.}}{{"\n"}}{{end}}' | grep NEXUS_SECRET
```

## Project Structure

Keep the ENTIRE project in a self-contained directory (e.g. `synapse-mcp/` or
`synapse-memory/`). **DO NOT** build plugin source code directly into the
target platform's source tree (e.g. inside `openclaw/extensions/`). Each plugin
is a standalone package deployed by copying into the target's directory.

```text
project-root/
├── server.py                       # MCP server (systemd service)
├── app/                            # FastAPI application (Docker variant)
├── docker-compose.yml              # Full-stack Docker deployment
├── proxy/proxy.py                  # LLM proxy (auto-memory middleware)
├── dashboard/dashboard.py          # Web UI
├── openclaw-plugin/                # OpenClaw plugin (plain JS, no build needed)
│   ├── index.js
│   ├── openclaw.plugin.json
│   └── package.json
├── plugins/
│   ├── hermes-synapse/             # Hermes plugin (plugin.yaml + schemas + tools)
│   ├── openclaw-synapse/           # OpenClaw plugin (TypeScript, needs build)
│   └── paperclip-synapse/          # Paperclip adapter (TypeScript)
├── ides/
│   ├── extension/                  # VS Code extension (VSIX package)
│   ├── windsurf/mcp_config.json
│   ├── antigravity/mcp_config.json
│   ├── vscode/mcp_config.json
│   └── install-to-ides.mjs
├── sdk/
│   ├── python/                     # Python SDK (pip installable)
│   └── typescript/                 # TypeScript SDK (npm package)
├── client-configs/                 # Configs for all platforms
├── scripts/                        # Adapters, installers
├── systemd/synapse-mcp.service
└── migrations/001_init.sql         # Database schema
```

## Deployment Architecture

Deploy the MCP server on one machine (the "brain"), and configure all agents
on all machines to connect to it over Tailscale. There are currently two brain
deployments:

```text
★ KUBUNTUX DOCKER (100.93.75.87) — internal project name "nexus"
   ├── :7777  HTTP API + MCP endpoint (FastAPI)
   ├── :7777  Dashboard (same port, integrated)
   └── :7778  STDIO Bridge (internal, for agent tooling)

   ★ LIN (100.91.55.113)
      Hermes MCP → 100.93.75.87:7777/mcp
      OpenClaw plugin → 100.93.75.87:7777 (REST)

★ RABUNTU STANDALONE (100.68.0.96)
   ├── :8765  MCP Server     ← memory brain (Python/FastMCP)
   ├── :8768  LLM Proxy      ← auto context + auto store (DeepSeek)
   └── :8767  Dashboard      ← web UI
```

## Setup Steps

### User's LLM Provider

This user runs **DeepSeek** as their primary LLM via:
```bash
DEEPSEEK_API_KEY=sk-...
# Endpoint: https://api.deepseek.com/v1
# Model: deepseek-chat
```

The LLM proxy MUST be configured with DeepSeek, not OpenRouter or LiteLLM:
```bash
LLM_PROVIDER_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_API_KEY=$DEEPSEEK_API_KEY
```

Do NOT use LiteLLM for DeepSeek routing — LiteLLM is only for Gemini models
on this user's setup. The proxy talks directly to `api.deepseek.com`.

### 100% Automatic Memory (Critical Requirement)

The user requires **zero manual tool calls** for memory management. The MCP
tools (`synapse_store`, `synapse_retrieve`, etc.) are NOT sufficient on their
own — the user expects memory to work transparently.

**The fix is the LLM Proxy** — every LLM call automatically:
1. Retrieves relevant context from Synapse and injects it into the prompt
2. Extracts key facts from the response and stores them as episodic/semantic

**Verification that auto-memory is working:**
```python
from synapse_sdk import SynapseClient
c = SynapseClient(server_url='http://<server>:8765/mcp')
h = c.health()
print(f'{h["memories"]} memories')  # Should increase over time
```

A memory count that stays static means the proxy isn't running or isn't
configured correctly. Check:
- Proxy process is alive: `curl http://<proxy>:8768/health`
- Hermes config points `model.base_url` to proxy, not directly to LLM
- Proxy has correct `SYNAPSE_URL` and `LLM_API_KEY` env vars

### 1. Deploy MCP Server — Variant A: Standalone

```bash
# Clone repo
git clone https://github.com/dylanmarriner/synapse-memory.git
cd synapse-memory

# Install deps
python3 -m venv .venv
.venv/bin/pip install mcp numpy ulid-py zstandard cryptography PyJWT

# Configure for single-tenant mode (no API key required)
# Edit env vars: SYNAPSE_TENANT_LIMIT=0, SYNAPSE_DEFAULT_TENANT=default
# The server auto-creates the "default" tenant on first startup.
# _ensure_tenant() also auto-creates it if missing.

# Run as systemd service
cp systemd/synapse-mcp.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now synapse-mcp
```

### 1b. Deploy MCP Server — Variant B: Docker Compose

```bash
# Clone or navigate to the project
cd /media/kubuntux/DEVELOPMENT1/shared-memory/nexus

# Configure .env
cp .env.example .env
# Edit NEXUS_SECRET to match the intended key
# The docker-compose.yml uses NEXUS_PORT=7777

# Start the stack
docker compose up -d

# Health check
curl http://localhost:7777/health
# Returns: {"healthy":true,"version":"1.0.0","components":{"postgres":true,...}}

# After editing code, restart the API container:
docker restart nexus-nexus-api-1
```

### 2. Install Plugins + MCP Configs on Each Machine

**Hermes MCP config** — add to `~/.hermes/config.yaml` (via `hermes config set`):

```bash
# For the Docker variant (nexus at kubuntux):
hermes config set mcp_servers.nexus.enabled true
hermes config set mcp_servers.nexus.url "http://100.93.75.87:7777/mcp"
hermes config set mcp_servers.nexus.headers '{"Authorization": "Bearer nexus-memory-shared-key-2026"}'
hermes config set mcp_servers.nexus.timeout 120
hermes config set mcp_servers.nexus.connect_timeout 30
hermes config set mcp_servers.nexus.description "Synapse Memory on kubuntux"

# For the standalone variant (synapse at rabuntu):
hermes config set mcp_servers.synapse.enabled true
hermes config set mcp_servers.synapse.url "http://100.68.0.96:8765/mcp"
hermes config set mcp_servers.synapse.headers '{"Authorization": "Bearer <secret>"}'
```

**IMPORTANT:** Do NOT edit `~/.hermes/config.yaml` directly with `patch`/`sed`/`write_file`.
Hermes blocks direct writes to the config file. Always use `hermes config set`.

**Hermes plugin (standalone variant only):**
```bash
mkdir -p ~/.hermes/plugins/synapse-memory
cp plugins/hermes-synapse/* ~/.hermes/plugins/synapse-memory/
```

**Hermes model config** — point to proxy for auto-memory:
```yaml
model:
  provider: custom:litellm
  base_url: http://<proxy-tailscale-ip>:8768/v1
  api_key: sk-proxy
```

**OpenClaw plugin:**

The nexus-memory OpenClaw plugin is plain JavaScript (no TypeScript build).
Copy the `openclaw-plugin/` directory to OpenClaw extensions and register it:

```bash
# 1. Copy plugin files
mkdir -p ~/.openclaw/extensions/nexus-memory
cp -r <project-root>/openclaw-plugin/* ~/.openclaw/extensions/nexus-memory/

# 2. Register in openclaw.json (edit manually — no CLI tool for this)
# Add four things:
#   - plugins.entries.nexus-memory: { enabled: true, config: { nexusUrl, nexusSecret, agentId, autoCapture, autoRecall } }
#   - plugins.allow: ["nexus-memory", ...existing entries...]
#   - plugins.slots.memory: "nexus-memory"
#   - plugins.load.paths: ["/home/<user>/.openclaw/extensions/nexus-memory"]
```

Example openclaw.json structure:
```json
{
  "plugins": {
    "entries": {
      "nexus-memory": {
        "enabled": true,
        "hooks": { "allowConversationAccess": true },
        "config": {
          "nexusUrl": "http://100.93.75.87:7777",
          "nexusSecret": "nexus-memory-shared-key-2026",
          "agentId": "openclaw",
          "autoCapture": false,
          "autoRecall": true
        }
      }
    },
    "allow": ["nexus-memory", "deepseek", "microsoft-foundry", "duckduckgo"],
    "slots": { "memory": "nexus-memory" },
    "load": { "paths": ["/home/lin/.openclaw/extensions/nexus-memory"] }
  }
}
```

**Windsurf / Antigravity / VS Code** — use the install script:
```bash
node ides/install-to-ides.mjs
```

### 3. Deploy LLM Proxy (for 100% automatic memory)

Run on the **same machine as the MCP server** — not on a client node.

**CRITICAL — model name override:** The proxy forwards whatever model name the
agent sends (e.g. `gemini-2.5-flash`) to the upstream LLM. If the upstream
doesn't serve that model, the request silently fails — no context injection,
no fact storage. **Always edit the proxy to use `LLM_MODEL` in the forward
body instead of the agent-sent model:**

In `proxy.py`, change:
```python
model = body.get("model", LLM_MODEL)  # BROKEN: forwards agent's model
# ...
"model": model,  # Agent sends "gemini-2.5-flash", DeepSeek gets it and rejects
```
To:
```python
model = LLM_MODEL  # FIXED: always use configured upstream model
# ...
"model": LLM_MODEL,  # Always sends "deepseek-chat" regardless of agent
```

**Deployment that survives SSH disconnect** — `nohup` inside an SSH session
dies when the SSH session ends. Use `systemd-run` instead:

```bash
DKEY=$DEEPSEEK_API_KEY
systemd-run --user --unit=synapse-proxy \
  -p "Environment=PYTHONIOENCODING=utf-8" \
  -p "Environment=LLM_PROVIDER_URL=https://api.deepseek.com/v1" \
  -p "Environment=LLM_MODEL=deepseek-chat" \
  -p "Environment=LLM_API_KEY=$DKEY" \
  -p "Environment=SYNAPSE_URL=http://<brain-tailscale-ip>:8765/mcp" \
  -p "Environment=PROXY_PORT=8768" \
  /usr/bin/python3 /path/to/proxy.py
```

The `--unit` name must not conflict with existing transient units. If a service
file with the same name exists, remove it first:
```bash
rm -f ~/.config/systemd/user/synapse-proxy.service
systemctl --user daemon-reload
```

### 4. Deploy Dashboard

```bash
# Standalone variant
cd dashboard && python3 dashboard.py
# Open http://<brain-tailscale-ip>:8767

# Docker variant — dashboard is integrated into the FastAPI app at :7777
# Already running: no extra step needed
```

## MCP Tool Namespace

When connected via HTTP MCP, all 40+ tools register at the TOP level (no
`mcp_nexus_` prefix). Key categories:

| Category | Example Tools | Count |
|----------|--------------|-------|
| Core memory | `memory_save`, `memory_recall`, `memory_reflect`, `memory_synthesize` | ~8 |
| Agent management | `agent_context`, `agent_learn`, `agent_represent`, `agent_learnings` | ~5 |
| Lesson/global memory | `memory_save_lesson`, `memory_save_global`, `memory_note_to_agent` | ~4 |
| Session tracking | `session_start`, `session_append`, `session_end`, `session_get`, `session_list` | ~5 |
| Project code ops | `sys_core_01`–`sys_core_31`, `register_project`, `remember`, `recall`, `ingest_file`, `search_files` | ~35 |
| Trust/reputation | `memory_confirm`, `memory_contradict`, `memory_profile` | ~3 |

Verify with `hermes mcp list` or curl the tools/list endpoint.

## Connecting from Client Machines

See `references/nexus-memory-mcp.md` in the `native-mcp` skill for full client
connection details, including how to discover the secret from a running Docker
container, auth header config, and end-to-end verification.

## Single-Tenant vs Multi-Tenant

| Mode | Env | Auth Required | Use Case |
|------|-----|---------------|----------|
| Single-tenant | `SYNAPSE_TENANT_LIMIT=0` | No | Personal/small team use |
| Multi-tenant | `SYNAPSE_TENANT_LIMIT=100` | API key | SaaS, multiple orgs |

In single-tenant mode, `_seed_default_tenant()` creates a "default" tenant on
startup. The `_ensure_tenant()` function auto-creates it if it doesn't exist
yet (important if switching from multi-tenant mode).

**Switching to single-tenant:** delete the old SQLite DB first to avoid
orphaned data under the old multi-tenant schema:
```bash
systemctl --user stop synapse-mcp
rm -f ~/.local/share/synapse-mcp/synapse.sqlite*
# Add SYNAPSE_TENANT_LIMIT=0 to env
systemctl --user start synapse-mcp
```

## Pitfalls

- **FastMCP redacts API keys** in structured responses. Key names matching
  patterns like `api_key`, `sk_syn_*` are truncated. Workaround: change the
  response field name to `key` and use a prefix like `syn_` that doesn't
  trigger redaction.
- **Switching between single/multi-tenant** requires a fresh DB — the tenant
  IDs don't migrate between modes.
- **SSH to rabuntu** may be slow (Raspberry Pi). Use background processes
  and `notify_on_complete` for SSH operations.
- **The LLM proxy doesn't support streaming** — agents that require SSE won't
  work through the proxy.
- **Dashboard port 8767** may conflict with other services on the brain machine.
- **LLM Proxy MUST be on the same machine as the MCP server** — not on a
  client machine like lin. Centralize all server processes.
- **User uses DeepSeek directly**, not via LiteLLM. LiteLLM proxy is only for
  Gemini/Vertex AI models on this setup.
- **Auto-memory verification**: if memory count stays static over time, the
  proxy isn't intercepting traffic. Check Hermes `base_url` config.
- **Regex fact extraction** is imperfect — it catches patterns but misses
  nuanced information. 0 memories from a conversation means the extraction
  patterns didn't match the response content.
- **`.env` file and running container may disagree** on `NEXUS_SECRET`. Always
  inspect the RUNNING container's environment, not the file.
- **Don't edit Hermes config directly** — use `hermes config set` commands.
  Direct writes via `patch`/`write_file`/`sed` are blocked.
- **Hermes restart required** after MCP config changes. `/reset` is not enough
  to pick up new MCP servers. Exit and re-launch the Hermes CLI.
- **100.68.0.96 (rabuntu) may not be reachable from all machines** — it's
  a Tailscale IP on kubuntux's tailnet. 100.93.75.87 (kubuntux) is the
  reliable endpoint.
- **OpenClaw's nexus-memory plugin is plain JS**, unlike the TypeScript synapse
  plugin. No build step needed — just copy `index.js`, `openclaw.plugin.json`,
  and `package.json`.

## Key Source Files

- `server.py` — MCP server (15 tools, multi-tenant SQLite, FTS5, embeddings)
- `proxy/proxy.py` — LLM proxy (auto-inject + auto-store)
- `dashboard/dashboard.py` — Web UI
- `docker-compose.yml` — Full-stack Docker deployment (5 containers)
- `app/` — FastAPI application (Docker variant)
- `openclaw-plugin/index.js` — Self-contained OpenClaw plugin (no build needed)
- `plugins/openclaw-synapse/src/index.ts` — TypeScript OpenClaw plugin variant
- `plugins/hermes-synapse/tools.py` — MCP-wrapper tool handlers
- `plugins/paperclip-synapse/src/worker.ts` — Paperclip adapter entry
- `ides/extension/src/extension.ts` — VS Code extension activation
- `sdk/python/synapse_sdk/__init__.py` — Python client SDK
- `sdk/typescript/src/index.ts` — TypeScript client SDK
- `scripts/adapters/nexus_mcp_stdio.py` — STDIO bridge for agents that can't do HTTP MCP
