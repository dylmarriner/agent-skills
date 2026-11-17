---
name: hindsight
description: Install, configure, and integrate Hindsight semantic memory system — CLI, API, and MCP server wiring for OpenCode/OpenClaw.
tags:
  - memory
  - mcp
  - hindsight
  - semantic-memory
  - vector-memory
---

# Hindsight — Semantic Memory System

Hindsight is a semantic memory system with a CLI, REST API, and MCP server. Use this skill when setting up Hindsight, configuring its CLI, wiring it as an MCP server into OpenCode, or debugging memory/recall issues.

## Installation

```bash
curl -fsSL https://hindsight.vectorize.io/get-cli | bash
```

Installs to `~/.local/bin/hindsight`. Confirm with `hindsight --help`.

## CLI Configuration

```bash
hindsight configure \
  --api-url https://api.hindsight.vectorize.io \
  --api-key hsk_<your_key_here>
```

Config saved to `~/.hindsight/config`. Environment variables `HINDSIGHT_API_URL` and `HINDSIGHT_API_KEY` override the config file.

### Named profiles (optional)

```bash
hindsight profile create my-profile \
  --api-url https://api.hindsight.vectorize.io \
  --api-key hsk_...
hindsight -p my-profile bank list
```

Profiles stored in `~/.hindsight/cli-profiles/<name>.toml`.

## Local Self-Hosting (Docker)

Run a full Hindsight server locally — no cloud dependency, data stays on your machine, includes a web UI at port 9999.

### Image Variants

| Tag | Size | Best For |
|-----|------|----------|
| `latest` | ~4.5 GB | Full-featured, all extras |
| `latest-slim` | ~2.3 GB | Constrained disks, minimal install — MCP + API + UI |

Prefer `latest-slim` unless you need bundled extras. The full image is nearly double the size with no functional difference for MCP/API use.

### Quick Start

```bash
docker run --rm -d --name hindsight \
  -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_LLM_PROVIDER=deepseek \
  -e HINDSIGHT_API_LLM_MODEL=deepseek-v4-flash \
  -e HINDSIGHT_API_LLM_API_KEY=<your_key> \
  -e HINDSIGHT_API_LLM_BASE_URL=https://api.deepseek.com/v1 \
  -v $HOME/.hindsight-docker:/home/hindsight/.pg0 \
  ghcr.io/vectorize-io/hindsight:latest
```

- API: `http://localhost:8888`
- UI: `http://localhost:9999`
- MCP: `http://localhost:8888/mcp/`
- Data persists in `~/.hindsight-docker/`

### Supported LLM Providers

Hindsight needs an LLM for fact extraction, entity resolution, and reflection. 27+ providers supported including:

| Provider | Env var | Example model |
|----------|---------|---------------|
| `deepseek` | `HINDSIGHT_API_LLM_API_KEY` | `deepseek-v4-flash` |
| `openrouter` | same env var | `qwen/qwen3.5-9b` (default) |
| `openai` | `HINDSIGHT_API_LLM_API_KEY` | `gpt-4o-mini` (default) |
| `anthropic` | same | `claude-haiku-4-5-20251001` |
| `gemini` | `HINDSIGHT_API_LLM_API_KEY` | `gemini-2.5-flash` |
| `ollama` | — | `gemma3:12b` (default) |
| `llamacpp` | — | auto-downloads GGUF (~3.5GB) |

Set `HINDSIGHT_API_LLM_PROVIDER` and optionally `HINDSIGHT_API_LLM_MODEL`. For OpenAI-compatible endpoints (DeepSeek, OpenRouter, LiteLLM), also set `HINDSIGHT_API_LLM_BASE_URL`.

### Docker Volume Permission Fix

Hindsight runs as UID 1000 (`hindsight` user) inside the container. If the mounted volume has different ownership, you'll see:
```
RuntimeError: Failed to start embedded PostgreSQL. Last error: IO error: Permission denied
```

Fix:
```bash
mkdir -p $HOME/.hindsight-docker
sudo chown 1000:1000 $HOME/.hindsight-docker
```

### Create Your First Bank

```bash
# Using env var override (or set HINDSIGHT_API_URL in your shell)
HINDSIGHT_API_URL=http://localhost:8888 hindsight bank create default -n "Default Bank"

# Verify
HINDSIGHT_API_URL=http://localhost:8888 hindsight bank list
# → Found 1 bank(s): default
```

## Profile Management (Local vs Cloud)

If you use both a local instance and the hosted cloud API, manage them with named profiles:

```bash
# Create a local profile
hindsight profile create local --api-url http://localhost:8888

# Create a cloud profile  
hindsight profile create cloud --api-url https://api.hindsight.vectorize.io --api-key hsk_...

# Use a profile
hindsight -p cloud bank list
hindsight -p local memory recall "query"

# Or set as default via env var
export HINDSIGHT_PROFILE=local
```

Profiles are stored at `~/.hindsight/cli-profiles/<name>.toml`.

### Shell Env Var Priority

`HINDSIGHT_API_URL` and `HINDSIGHT_API_KEY` environment variables **override** both the config file and the profile. If you have these set in `.bashrc`/`.profile`, the CLI will always connect to that URL regardless of profile:

```bash
# To switch, either:
export HINDSIGHT_API_URL=http://localhost:8888    # override in shell
# or unset and use -p flag:
unset HINDSIGHT_API_URL
hindsight -p cloud bank list
```

## Verification

```bash
hindsight health
hindsight bank list
hindsight version
```

The `version` output includes feature flags: look for `MCP Server: enabled`.

## MCP Server Integration

Hindsight exposes an MCP endpoint at `<api-url>/mcp/` (note trailing slash). The local endpoint is `http://localhost:8888/mcp/`. The MCP server auto-discovers tools like `retain`, `recall`, `reflect`, `list_memories`, etc.

### Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  hindsight:
    url: "http://localhost:8888/mcp/"
```

For cloud, add the auth header:
```yaml
mcp_servers:
  hindsight:
    url: "https://api.hindsight.vectorize.io/mcp/default/"
    headers:
      Authorization: "Bearer hsk_..."
```

Verify: `hermes mcp test hindsight` should show "Connected" and list ~28 tools.

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "hindsight": {
      "serverUrl": "http://localhost:8888/mcp/",
      "headers": {}
    }
  }
}
```

For cloud: add `"Authorization": "Bearer hsk_..."` under headers.

### OpenCode

Hindsight exposes an MCP endpoint at `<api-url>/mcp`. Wire it into OpenCode's `~/.config/opencode/opencode.json` under the `mcp` key:

```json
{
  "mcp": {
    "hindsight": {
      "type": "remote",
      "url": "https://api.hindsight.vectorize.io/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer hsk_5b8816e021e870f680fc3a3417b311b4_73e15d0268a6d8f3"
      }
    }
  }
}
```

### OpenCode MCP config format (v1.14+)

OpenCode 1.14+ validates config against `https://opencode.ai/config.json`. Key facts:

| Key | Status | Notes |
|-----|--------|-------|
| `mcp` | Valid | Singular, used for MCP server definitions |
| `mcpServers` | **INVALID** | Old key from archived schema — remove if present |

MCP server entries under `mcp` use one of two types:

**Remote** (HTTP/SSE servers):
```json
{
  "type": "remote",
  "url": "<mcp-endpoint-url>",
  "enabled": true,
  "headers": { "Authorization": "Bearer <token>" }
}
```

**Local** (stdio/command-based):
```json
{
  "type": "local",
  "command": ["<binary>", "<arg1>"],
  "env": { "VAR": "value" }
}
```

After editing, validate by running `opencode models` — if it fails with "Configuration is invalid / Unrecognized key: X", check for stale keys under `mcp`/`mcpServers`.

## Common Operations

```bash
# Bank management
hindsight bank list
hindsight bank create my-bank --description "My memory bank"
hindsight bank profile <bank>

# Memory operations
hindsight memory list --bank <bank>
hindsight memory recall "query text" --bank <bank>
hindsight memory reflect <memory-id>

# Entity management
hindsight entity list --bank <bank>

# Documents
hindsight document list --bank <bank>

# Explore (interactive TUI)
hindsight explore

# Web UI
hindsight ui

# Audit
hindsight audit list --bank <bank>
```

## Verification Checklist

- `hindsight health` returns healthy with database connected
- `hindsight bank list` shows expected banks
- `opencode models` succeeds (no config validation errors)
- OpenCode can discover and use the hindsight MCP server tools

## Pitfalls

- The `mcpServers` key in OpenCode config is **rejected** by OpenCode 1.14+. Always use `mcp` (singular).
- For remote MCP servers, the format is `{ type: "remote", url: "...", enabled: true }` — not `{ command: "http", args: [...] }`.
- The local Hindsight MCP endpoint is `/mcp/` (no bank ID in path), while the cloud endpoint uses `/mcp/default/` (includes the bank ID). These are not interchangeable.
- Docker container runs as UID 1000 (user `hindsight`) — mounted volumes need `chown 1000:1000` or PostgreSQL fails with permission errors.
- Shell env vars (`HINDSIGHT_API_URL`, `HINDSIGHT_API_KEY`) override both `~/.hindsight/config` AND named profiles. If the CLI ignores profile settings, check `.bashrc`/`.profile` for stale env vars.
- A local Hindsight server (localhost:8888) and the cloud API (api.hindsight.vectorize.io) are separate data stores with independent banks. Configure the right one for your context.
- After `hindsight configure`, confirm `hindsight version` shows `MCP Server: enabled` before trying to use the MCP endpoint.
- The first `retain` call on a fresh instance is slow (DeepSeek/LLM needs to warm up and verify connection). Subsequent calls are faster.
- **Docker `--add-host host.docker.internal:host-gateway` may be blocked** by agent security policies (tirith, command_allowlist). Fallback: use `--network host` (makes localhost inside the container map to the host's localhost, but conflicts with `-p` port mapping) or use the host's LAN IP directly (e.g. `http://192.168.1.X:PORT`). To get the host's LAN IP: `ip route show default | head -1 | awk '{print $3}'` (the gateway, or use `src` field for the host's own IP).
- **LLM base URL must use a resolvable address from inside the container**: `localhost` inside the container is the container, not the host. Use `host.docker.internal`, the host's LAN IP, or `--network host` to bridge this gap.
