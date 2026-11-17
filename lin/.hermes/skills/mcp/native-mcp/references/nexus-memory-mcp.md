# Nexus (Synapse Memory) MCP Server

The Docker Compose stack internally called "nexus" IS Synapse Memory — a
persistent cross-device memory server for AI agents. It exposes 40+ MCP tools
for saving/recalling/reflecting on memories, managing agent context, learning
from corrections, and project-level code/search operations.

**Naming:** Refer to the system as "Synapse Memory" unless the user explicitly
mentions "nexus" — they are the same thing, but "Synapse Memory" is the
user-facing name.

## Finding Nexus on a Remote Machine

Nexus typically runs as a Docker Compose stack. Key containers:

| Container | Purpose | Port |
|-----------|---------|------|
| `nexus-nexus-api-1` | HTTP API + MCP endpoint | 7777 |
| `nexus-nexus-worker-1` | Background processing | — |
| `nexus-nexus-bridge-1` | MCP stdio bridge | 7778 |
| `nexus-postgres-1` | Primary store (pgvector) | 5435 |
| `nexus-redis-1` | Cache/task state | 6381 |

### Discovery steps on host

```bash
# Find the compose project working directory
docker inspect nexus-nexus-api-1 \
  --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'
# → /media/kubuntux/DEVELOPMENT1/shared-memory/nexus

# Extract NEXUS_SECRET for Bearer auth
docker inspect nexus-nexus-api-1 \
  --format '{{range .Config.Env}}{{.}}{{"\n"}}{{end}}' | grep NEXUS_SECRET
# → NEXUS_SECRET=<the-token>

# Check the integration guide
ls <project-root>/UNIVERSAL_AGENT_INTEGRATION.md
```

## Hermes Config

**IMPORTANT:** Edit Hermes config via `hermes config set`, NOT by directly editing
`~/.hermes/config.yaml`. Direct writes are blocked.

```bash
hermes config set mcp_servers.nexus.enabled true
hermes config set mcp_servers.nexus.url "http://100.93.75.87:7777/mcp"
hermes config set mcp_servers.nexus.headers '{"Authorization": "Bearer <NEXUS_SECRET>"}'
hermes config set mcp_servers.nexus.timeout 120
hermes config set mcp_servers.nexus.connect_timeout 30
hermes config set mcp_servers.nexus.description "Synapse Memory on kubuntux"
```

Resulting YAML:
```yaml
mcp_servers:
  nexus:
    url: http://<tailscale-ip>:7777/mcp
    headers:
      Authorization: Bearer <NEXUS_SECRET>
    timeout: 120
    connect_timeout: 30
    enabled: true
    description: Synapse Memory on kubuntux
```

Test with:

```bash
hermes mcp test nexus
```

Expect `✓ Connected` and 40+ tools discovered.

## Tool Namespace

All 42 tools are registered at the top level (no `mcp_nexus_` prefix — Nexus uses its own naming). Core tools:

| Tool | Purpose |
|------|---------|
| `memory_save` | Save durable fact, auto-classifies type |
| `memory_recall` | 4-way parallel semantic/keyword search |
| `memory_reflect` | LLM-driven synthesis over retrieved memories |
| `memory_synthesize` | Comprehensive understanding from memory |
| `memory_save_lesson` | High-priority save after correction/mistake |
| `memory_save_global` | Share knowledge with ALL agents |
| `memory_note_to_agent` | Leave context for a specific agent |
| `agent_context` | Load agent-specific context and handoff notes |
| `agent_learn` | Teach agent something new, saves immediately |
| `agent_represent` | Update agent's self-representation after learning |
| `nexus_status` | Health check for all components |
| `sys_core_01`–`sys_core_31` | Project-level search, code analysis, diffs, skill creation, diagnostics |

## Auth Header Config

The Bearer token must match `NEXUS_SECRET` from the server's environment. Set it in `headers` on the MCP server config — not in a `command` env, and never add it to `.env` (the HTTP client reads headers from config, not env vars).

### Container env vs `.env` file

The running container's env may differ from the `.env` file. Always read from the running container as source of truth:

```bash
docker exec nexus-nexus-api-1 env | grep NEXUS_SECRET
```

- `docker restart` re-reads the `.env` file — so changes to `.env` take effect on restart.
- If the service was created with a stale `.env`, use `docker compose up -d --force-recreate <service>` to force a fresh read.

## Verification

```bash
# 1. Connection + tool discovery
hermes mcp test nexus

# 2. Health check
curl -s http://<tailscale-ip>:7777/health | python3 -m json.tool

# 3. REST endpoint direct call (without MCP)
curl -X POST http://<tailscale-ip>:7777/v1/memory/recall \
  -H "Authorization: Bearer <NEXUS_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"hermes:hostname", "query":"test", "limit":1}'
```

## Pitfalls

- The NEXUS_SECRET is **not** a shell env var on the agent machine — it goes in `config.yaml` `headers.Authorization`. Do not `export` it.
- `hermes mcp test` only validates connection + tool list. A real tool call (`memory_save` → `memory_recall`) is the true end-to-end check.
- MCP server config changes require a **full Hermes restart** (`/reset` is not enough). After restart, run `hermes mcp list` to confirm the server shows up.
- If you get `401 Unauthorized`, the Bearer token in config doesn't match `NEXUS_SECRET` on the server. Re-inspect the container env to confirm.
- Nexus uses top-level tool names (no `mcp_nexus_` prefix). These can collide with native tools — Nexus handles disambiguation server-side.
