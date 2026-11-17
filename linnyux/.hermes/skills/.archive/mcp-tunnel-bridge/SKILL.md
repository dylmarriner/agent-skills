---
name: mcp-tunnel-bridge
description: "Deploy, configure, and operate MCP bridge servers exposed through OpenAI's tunnel-client for remote consumption. Covers single-device and multi-device aggregation."
version: 1.0.0
author: Hermes Agent (session-derived)
metadata:
  hermes:
    tags: [MCP, tunnel-client, OpenAI, infrastructure, networking]
    related_skills: [mcp:native-mcp, mcp:mcporter, hermes-agent]
---

# MCP Tunnel Bridge

Deploy a Python-based MCP server that wraps Hermes Agent tools (via `registry.dispatch()`), then expose it externally through OpenAI's `tunnel-client` for consumption by ChatGPT, Codex, or any MCP-capable client.

Can aggregate **multiple machines** through a single tunnel — each device gets a unique hostname prefix so the client knows which device it's targeting.

## When to Use

- Expose Hermes Agent's built-in tools (terminal, file ops, web, browser, code exec, memory) as MCP tools for external consumption
- Connect a local MCP server to OpenAI's control plane via tunnel-client
- Aggregate tools from multiple machines (lin, macuntu, rabuntu, etc.) through one tunnel
- Provide remote shell access (`system_exec` tool) or full agent turns (`hermes_ask` escape hatch)

## Architecture

```
┌──────────────┐     stdio     ┌────────────────────┐    outbound    ┌──────────────────┐
│ Hermes Tools  │─────────────▶│ tunnel-client       │──────────────▶│ OpenAI Control    │
│ (via registry │  MCP JSON-RPC│ (Go binary)         │    tunnel      │ Plane             │
│  .dispatch()) │◀─────────────│                     │◀──────────────│ → ChatGPT/Codex   │
└──────────────┘              └────────────────────┘                └──────────────────┘
```

Multi-device: tunnel-client supports multiple `commands` with different `channel` names. Each command wraps an SSH call to a remote machine running the same bridge, with a `HERMES_MCP_PREFIX` env var for device identification.

## Prerequisites

- Hermes Agent installed (with `mcp` Python package: `pip install mcp`)
- `tunnel-client` binary installed (OpenAI's official MCP tunnel daemon)
- SSH key access to any remote machines you want to aggregate
- An OpenAI API key with tunnel permissions

## Bridge Script: `mcp_direct_bridge.py`

The core is a self-contained Python script that:
1. Imports `model_tools` (triggers tool registry discovery)
2. Imports `tools.registry` for dispatch
3. Registers auto-approve + sudo callbacks so terminal tool never prompts
4. Reads `HERMES_MCP_PREFIX` env var to set the tool name prefix per device
5. Registers all Hermes tools as MCP tools with the prefix
6. Adds two bonus tools:
   - `{prefix}_system_exec` — raw subprocess shell execution, no guards
   - `{prefix}_hermes_ask` — shells out to `hermes -z <prompt>` for a full agent turn

### Key Code: env var overrides for omni mode

```python
os.environ.setdefault("HERMES_CRON_SESSION", "approve")
os.environ.setdefault("HERMES_EXEC_ASK", "0")
os.environ.setdefault("HERMES_MCP_EXCLUDE_TOOLSETS", "")
```

### Key Code: auto-approve callbacks (backward compat)

```python
try:
    from tools.approval import set_hermes_interactive_context
    _interactive_token = set_hermes_interactive_context(True)
except ImportError:
    pass  # Hermes < 0.18 — context not available

from tools.terminal_tool import set_approval_callback, set_sudo_password_callback

def _always_approve(_command):
    return {"approved": True, "message": None}

def _sudo_password_prompt(_prompt_text=""):
    try:
        from tools.terminal_tool import _get_cached_sudo_password
        return _get_cached_sudo_password() or "root"
    except Exception:
        return "root"

set_approval_callback(_always_approve)
set_sudo_password_callback(_sudo_password_prompt)
```

### Key Code: hostname prefix

```python
import socket
_HERMES_MCP_PREFIX_ENV = os.environ.get("HERMES_MCP_PREFIX")
if _HERMES_MCP_PREFIX_ENV:
    CLEAN_HOSTNAME = _HERMES_MCP_PREFIX_ENV
    HOSTNAME = CLEAN_HOSTNAME
else:
    HOSTNAME = socket.gethostname().split(".")[0]
PREFIX = HOSTNAME.lower().replace("-", "_").replace(" ", "_")
```

See `references/bridge-template.py` for the full script.

## Tunnel-Client Configuration

The config file (YAML, JSON accepted) lives at `~/.config/tunnel-client/<profile>.yaml`.

### Single device

```json
{
  "control_plane": {
    "api_key": "sk-...",
    "base_url": "https://api.openai.com",
    "tunnel_id": "tunnel_<id>"
  },
  "health": {
    "listen_addr": "127.0.0.1:0",
    "url_file": ".../health/<profile>.url"
  },
  "mcp": {
    "commands": [
      {
        "channel": "main",
        "command": "env HERMES_MCP_PREFIX=myhost .../venv/bin/python3 .../mcp_direct_bridge.py"
      }
    ]
  }
}
```

### Multi-device aggregation (SSH)

Add one `command` per device with unique `channel` names. The `main` channel is required.

```json
{
  "mcp": {
    "commands": [
      {
        "channel": "main",
        "command": "env HERMES_MCP_PREFIX=kubuntux /path/to/venv/bin/python3 /path/to/mcp_direct_bridge.py"
      },
      {
        "channel": "lin",
        "command": "ssh -o StrictHostKeyChecking=no -o BatchMode=yes lin@IP \"env HERMES_MCP_PREFIX=lin /path/to/venv/bin/python3 /path/to/bridge.py\""
      },
      {
        "channel": "macuntu",
        "command": "ssh -o StrictHostKeyChecking=no -o BatchMode=yes macuntu@IP \"env HERMES_MCP_PREFIX=macuntu /path/to/venv/bin/python3 /path/to/bridge.py\""
      }
    ]
  }
}
```

**Important**: the SSH remote command must be **quoted** so it's passed as a single argument to SSH. The tunnel-client runs the command through a shell, so quoted inner args work.

## Running the Tunnel

```bash
tunnel-client run --profile-dir ~/.config/tunnel-client --profile <profile>
```

Run in tmux for persistence:
```bash
tmux new-session -d -s tunnel-mcp__<name> \
  "tunnel-client run --profile-dir ~/.config/tunnel-client --profile <profile> >> ~/.local/state/tunnel-client/logs/<name>.log 2>&1"
```

Check health:
```bash
HEALTH_URL=$(cat ~/.local/state/tunnel-client/health/<profile>.url)
curl -s $HEALTH_URL/healthz   # should return "live"
curl -s $HEALTH_URL/readyz    # should return "ready"
```

## Hermes Version Compatibility

| Feature | Hermes 0.17.x | Hermes 0.18.x |
|---|---|---|
| `set_hermes_interactive_context` | Not available | Available |
| `tools.approval` module | Available | Available |
| `tools.terminal_tool` | Available | Available |
| MCP Python package | Must install separately | Must install separately |

The bridge uses `try/except` for features not present in older versions. For Hermes 0.17, you lose the interactive context optimization but all other omni features (auto-approve, sudo, system_exec) still work.

## Pitfalls

### 1. Always extract env vars from /proc before killing a tunnel process
If you need to restart the tunnel, first read the environment of the running process:
```bash
cat /proc/<PID>/environ | tr '\0' '\n' | grep -i KEY
```
Otherwise you lose env-var-based secrets like `CONTROL_PLANE_API_KEY`. The tunnel-client config can embed the API key directly (instead of `env:VAR_NAME`) to avoid this.

### 2. A single failed MCP command kills the entire tunnel
If any channel's MCP command exits with an error, the tunnel-client shuts down ALL channels. Debug the failing channel first:
```bash
# Test the SSH command directly as the tunnel user
sudo -u <user> ssh -o BatchMode=yes <host> '<command>' 2>&1 | head -20
```

### 3. SSH exit code 255 ≠ remote command failure
When multiple channels are aggregated, exit 255 on lin/macuntu channels usually means they were killed by the tunnel shutting down because another channel (e.g. rabuntu) failed first. Check the log timeline to identify the actual root cause.

### 4. Channel naming constraints
- One channel **must** be named `main` — the tunnel-client rejects configs without it
- Other channel names must be unique
- If all channels omit the `channel` field, they all default to `main` → "duplicate channel 'main'" error

### 5. SSH host key verification
Use `-o StrictHostKeyChecking=no -o BatchMode=yes` so the tunnel subprocess doesn't hang on host key prompts. Verify key-based auth works first:
```bash
sudo -u <tunnel-user> ssh -o BatchMode=yes <user>@<host> 'echo ok'
```

### 6. HERMES_MCP_PREFIX placement
For local commands: `env HERMES_MCP_PREFIX=<name> python3 ...` (prepend before the command).
For SSH commands: place INSIDE the quoted SSH command: `ssh host "env HERMES_MCP_PREFIX=<name> python3 ..."` (sets it on the remote host, not locally).

### 7. Config file format
The tunnel-client accepts JSON even though the file has a `.yaml` extension. YAML is a superset of JSON, so this works.

### 8. Deploying the bridge to remote machines
Use SSH pipe to copy the bridge script:
```bash
cat bridge.py | ssh host 'cat > /path/to/bridge.py'
```
Then verify syntax:
```bash
ssh host 'python3 -c "import ast; ast.parse(open(\"/path/to/bridge.py\").read()); print(\"OK\")"'
```

## Verification

After the tunnel starts, confirm all channels are working:
```bash
# Check log for all 4 MCP commands starting
grep 'stdio MCP command started' /path/to/log | wc -l   # should be 4

# Check for errors
grep -E 'ERROR|WARN.*exit' /path/to/log | grep -v 'terminated\|context canceled'

# Health endpoints
curl -s $(cat /path/to/health.url)/healthz   # live
curl -s $(cat /path/to/health.url)/readyz    # ready

# Process count
ps aux | grep -E 'tunnel-client|mcp_direct' | grep -v grep | wc -l
# Expected: 1 tunnel-client + N bridge processes + N SSH processes
```
