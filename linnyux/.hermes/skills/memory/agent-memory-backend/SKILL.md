---
name: agent-memory-backend
description: Install, configure, and wire third-party memory engines (agentmemory, mem0, etc.) into Hermes Agent and OpenClaw via MCP + memory provider config.
category: memory
emoji: 🧠
requires:
  bins: [node, npm]
trigger: |
  User asks to install agentmemory, set up persistent memory for agents,
  wire a memory backend into Hermes/OpenClaw, or fix memory persistence.
  Also relevant when user says "agent keeps forgetting things".
---

# Agent Memory Backend Setup

Install and configure an external memory engine (agentmemory, mem0, etc.)
for Hermes Agent and/or OpenClaw. Each engine runs as a daemon with a
REST API + MCP bridge, providing persistent cross-session memory with
hybrid search (BM25 + vector + optional graph).

## General Pattern

```
1. Install engine globally (npm/Python/etc.)
2. Start the daemon (port-based, e.g. 3111)
3. Wire MCP server into agents
4. Set memory provider config where applicable
5. Install companion skills (tool access)
6. Restart agents to pick up changes
7. Verify via health endpoint or demo
```

## agentmemory (v0.9.24+)

### Install

```bash
npm install -g @agentmemory/agentmemory
```

Initialize config:

```bash
agentmemory init          # Creates ~/.agentmemory/.env
```

Without an LLM provider key in `.env`, agentmemory runs in noop mode:
BM25 + synthetic compression + hybrid search still work, but LLM-backed
compression/summarisation/reflection/consolidation are disabled.

### Wire into Hermes Agent (manual YAML)

Hermes uses YAML config. Automated merge is not supported, so do it
manually in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  agentmemory:
    command: npx
    args:
    - -y
    - '@agentmemory/mcp'
    enabled: true

memory:
  provider: agentmemory
  agentmemory_url: http://127.0.0.1:3111
```

The `memory.provider` field tells Hermes to use agentmemory as the
memory backend instead of the built-in store.

**Pitfalls:**
- `~/.hermes/config.yaml` is security-sensitive: avoid the Hermes
  `patch` tool here and use shell/tools like `sed` instead.
- **NEVER use `yaml.dump()` to rewrite the config.** PyYAML's `dump`
  strips ALL comments from the file, destroying carefully organized
  sections. Always use `sed`, targeted line insertion, or manual edits
  via an editor. If you must use Python, read-as-string + line-level
  insert is safer than parse-dump.
- If a prior install already inserted an `agentmemory` block under
  `mcp_servers:`, ensure there is only **one** such block and it
  includes `enabled: true`. Duplicate keys will silently override
  each other and can disable the server.
- If the machine already runs `honcho` as the memory provider,
  replace it with `agentmemory` rather than adding a second provider
  entry. Read the file back and grep for `provider:` after editing
  to confirm only one active provider remains.

### Remote Hermes (client-only, shared backend)

When a second machine should use an *existing* agentmemory daemon on another
host (no local agentmemory install needed), wire its Hermes to connect
remotely. See `references/remote-client-deployment.md` for the complete
SSH-driven deployment workflow (config edits, skill install, cognitive
memory setup, verification).

```yaml
# On the remote/client Hermes instance (no agentmemory daemon locally)
mcp_servers:
  agentmemory:
    command: npx
    args:
    - -y
    - '@agentmemory/mcp'
    enabled: true
    env:
      AGENTMEMORY_URL: http://<tailscale-ip-or-hostname>:3111   # point to the host running agentmemory

memory:
  provider: agentmemory
  agentmemory_url: http://<tailscale-ip-or-hostname>:3111        # same remote address
```

Key details:
- The `env` block in `mcp_servers` passes `AGENTMEMORY_URL` to the MCP shim
  so the npx process talks to the remote daemon, not localhost.
- `memory.agentmemory_url` tells Hermes where to send memory tool calls.
- Install companion skills on the client too: `npx skills add rohitg00/agentmemory -y`
- **No local agentmemory daemon needed** on the client machine.

### Wire into OpenClaw (auto)

OpenClaw uses JSON config and supports auto-wiring:

```bash
agentmemory connect openclaw
```

This adds `mcpServers.agentmemory` to `~/.openclaw/openclaw.json`.

Then restart the gateway: `systemctl --user restart openclaw-gateway`

### Install Companion Skills

agentmemory ships 8 skills (recall, remember, recap, forget, handoff,
session-history, commit-context, commit-history):

```bash
npx skills add rohitg00/agentmemory -y
```

These get symlinked into both Hermes and OpenClaw skill directories.

### Start the Server

```bash
agentmemory                 # Daemon on :3111
```

Viewer at `http://localhost:3113`. Health check:

```bash
agentmemory status
```

### Verify

```bash
agentmemory demo            # Seeds 3 sessions, runs search queries
```

### Enable LLM-Backed Features

Edit `~/.agentmemory/.env`, uncomment one provider key:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=sk-or-...
```

Flags to enable:

| Flag | Effect |
|------|--------|
| `AGENTMEMORY_AUTO_COMPRESS=true` | LLM compression on every observation |
| `AGENTMEMORY_INJECT_CONTEXT=true` | Inject recalled memories into agent prompts |
| `GRAPH_EXTRACTION_ENABLED=true` | Knowledge graph extraction |
| `CONSOLIDATION_ENABLED=true` | 4-tier memory pipeline |

### Venice.ai as OpenAI-Compatible Provider

When no DeepSeek/OpenAI key is available but a Venice.ai key exists (from Hermes custom providers), use Venice as the agentmemory LLM backend:

```ini
OPENAI_API_KEY=<venice-api-key>
OPENAI_BASE_URL=https://api.venice.ai/api/v1
EMBEDDING_PROVIDER=local        # Venice may not support embeddings
```

**Why Venice:** Venice offers DeepSeek models (v4-flash, v4-pro) via OpenAI-compatible chat completions API. The same key used for Hermes custom providers works here.

**Pitfall — no embedding support:** Venice doesn't serve embedding models. Set `EMBEDDING_PROVIDER=local` to use Xenova/all-MiniLM-L6-v2 locally (384-dim vectors, works OOB with no API key).

See `references/venice-ai-provider.md` for exact .env contents and verification output.

### DeepSeek as OpenAI-Compatible Provider

DeepSeek's API is OpenAI-compatible. Configure via:

```bash
OPENAI_API_KEY=sk-<your-deepseek-key>
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

Set these in `~/.agentmemory/.env` and start with:

```bash
env OPENAI_API_KEY=sk-... OPENAI_BASE_URL=https://api.deepseek.com/v1 agentmemory
```

**Known pitfall — dotenv override:** If `OPENAI_API_KEY` is already set in the shell environment (e.g., from LiteLLM at `sk-anything`), the `.env` file value is silently ignored — dotenv does not override existing env vars. The `env` prefix approach above is the reliable workaround.

For persistent startup, create a wrapper script at `~/.local/bin/agentmemory-start`:

```bash
#!/bin/bash
cd ~/.agentmemory
set -a; source .env; set +a
exec /home/kubuntux/.npm-global/bin/agentmemory "$@"
```

**Always use the full path** (`~/.npm-global/bin/agentmemory` or resolve it with `which agentmemory`) rather than the bare `agentmemory` command. The user's terminal PATH may drop system directories, and the nvm/npm-global paths may not be on the non-interactive shell PATH. Using the full path avoids `command not found` when launched from background shell sessions.

When DeepSeek is configured as the provider, enable all 4 LLM-backed features in `.env`:

```ini
AGENTMEMORY_AUTO_COMPRESS=true
AGENTMEMORY_INJECT_CONTEXT=true
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION_ENABLED=true
```

### Cross-Machine Setup (via SSH)

For remote machines on the same Tailscale network that have Node installed:

```bash
# 1. Install globally via SSH
ssh <user>@<tailscale-ip> "npm install -g @agentmemory/agentmemory"

# 2. Init config remotely
ssh <user>@<tailscale-ip> "<path-to-agentmemory> init"

# 3. Copy the env config with DeepSeek key
ssh <user>@<tailscale-ip> "cat > ~/.agentmemory/.env << 'EOF'
OPENAI_API_KEY=<deepseek-key>
OPENAI_BASE_URL=https://api.deepseek.com/v1
AGENTMEMORY_AUTO_COMPRESS=true
AGENTMEMORY_INJECT_CONTEXT=true
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION_ENABLED=true
EOF"

# 4. Start agentmemory remotely (background)
ssh <user>@<tailscale-ip> "env OPENAI_API_KEY=... OPENAI_BASE_URL=https://api.deepseek.com/v1 agentmemory" &

# 5. Wire agents (after verifying PATH)
ssh <user>@<tailscale-ip> "<path-to-agentmemory> connect openclaw"   # Auto for JSON agents
ssh <user>@<tailscale-ip> "python3 -c \"...\" "                        # Manual YAML for Hermes
```

**PATH gotcha on SSH:** SSH non-interactive sessions often don't source `.bashrc`/`.profile`, so `~/.npm-global/bin` may not be in PATH. Use the full path `~/.npm-global/bin/agentmemory` or check with `which agentmemory` first.

### Wire into Devin CLI

Devin CLI supports adding MCP servers directly:

```bash
devin mcp add agentmemory -- npx -y @agentmemory/mcp
```

Note the `--` separator syntax: the command and args go after `--`, not as `--args` flags.

Devin also auto-picks up skills from `~/.agents/skills/` as a global skill path (verified via `devin skills paths`), so the 8 agentmemory skills installed via `npx skills add rohitg00/agentmemory -y` are immediately available without additional configuration.

Verify:
```bash
devin mcp list | grep agentmemory
devin skills list | grep -E "recall|remember|recap|forget|handoff"
```

### Wire into Other Agents (general pattern)

For any agent CLI that supports MCP servers (Cursor, Gemini CLI, Windsurf, etc.):

1. Add an MCP server with command `npx -y @agentmemory/mcp`
2. If the agent has a `memory.provider` or similar config, set it to `agentmemory`
3. Install 8 companion skills via `npx skills add rohitg00/agentmemory -y`
4. Skills land in `~/.agents/skills/` — most agents auto-discover this directory

### Network Exposure (Tailscale / socat)

agentmemory's iii-engine binds to `localhost:3111` by default with no configurable bind address. To make it accessible to other machines on the tailnet, use a `socat` TCP forwarder:

```bash
# Get your tailscale IP
TAILSCALE_IP=$(tailscale ip -4)

# Start socat forwarder (after agentmemory is running)
socat TCP-LISTEN:3111,bind=$TAILSCALE_IP,reuseaddr,fork TCP:127.0.0.1:3111 &
```

Verify remotely:
```bash
curl -s http://<tailscale-ip>:3111/agentmemory/health
# → 200 OK
```

This is useful when a machine on the tailnet (e.g., `lin@100.91.55.113` with Tailscale SSH policy blocking) can't run agentmemory locally but its agents can connect to the REST/MCP endpoint remotely. Remote agents configure `AGENTMEMORY_URL=http://<tailscale-ip>:3111` to use the shared memory backend.

**Persistence (cron keepalive):** The socat forwarder can die on network hiccups or machine sleep/wake cycles. Create a cron job that checks and restarts it every 5 minutes:

```bash
hermes cron create \
  --name agentmemory-socat-keepalive \
  --schedule "every 5m" \
  --toolsets terminal \
  --prompt 'Ensure socat TCP forwarder for agentmemory is running on tailscale-ip:3111 -> localhost:3111. Start it with: socat TCP-LISTEN:3111,bind=<tailscale-ip>,reuseaddr,fork TCP:127.0.0.1:3111'
```

This runs silently and only acts when the forwarder is down.

### Pitfalls

- **Hermes YAML** cannot be auto-wired by `agentmemory connect`. Must
  edit `~/.hermes/config.yaml` manually for both `mcp_servers` and
  `memory.provider`.
- **OpenClaw binary stub**: `~/.local/bin/openclaw` may be a stale
  9-byte stub ("Not Found") from a prior installation, shadowing the
  real binary at `~/.npm-global/bin/openclaw`. Verify with `which` and
  remove the stub if present.
- **Gateway restart required**: After adding MCP config to OpenClaw,
  the gateway must be restarted: `systemctl --user restart openclaw-gateway`.
- **No LLM key = reduced features**: agentmemory works without a key
  (BM25 + local embeddings), but compression, graph extraction, and
  reflection are disabled until a provider is configured.
- **OpenClaw web-search plugin**: known TypeScript build issue causes
  harmless warnings. Disable with `openclaw plugins disable openclaw-web-search`.

## Verification

```bash
agentmemory status          # Health, sessions, observations, memories, graph
agentmemory doctor          # Full diagnostic (run --all for CI mode)
```

See `references/agentmemory-v0.9.24.md` for exact commands, output, and
wiring transcript from a real installation session. See
`references/agentmemory-v0.9.26-hermes-wiring.md` for Hermes-specific
YAML pitfalls and duplicate-key safeguards. See
`references/venice-ai-provider.md` for using Venice.ai as the OpenAI-compatible
LLM provider (when no DeepSeek key is available). See
`references/multi-machine-cognitive-memory.md` for the dual-layer architecture
when sharing a single agentmemory backend across multiple Hermes nodes. See
`references/remote-client-deployment.md` for the SSH-based deployment workflow
to wire a second machine as a client-only node with no local agentmemory daemon.
See `references/seeding-memories-via-rest-api.md` for bulk-importing memories\ndirectly via the REST API (preferred over `agentmemory import` which spawns\na competing daemon instance).\n\nSee the `agent-context-compression` skill (memory category) for headroom\nintegration — context compression, RTK fusion, and agentmemory-aware\npriority compression that reduces token costs by 60-97%.
