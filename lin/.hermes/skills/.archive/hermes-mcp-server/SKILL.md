---
name: hermes-mcp-server
description: "Expose Hermes Agent's built-in tools as an MCP server for external clients — OpenAI Codex, ChatGPT, Claude Code, or any MCP consumer. Covers the mcp_direct_bridge.py mechanism, the tunnel-client integration to OpenAI's control plane, the Hermes Gateway SSE endpoint, and how to open it up to full unrestricted access."
version: 1.0.0
metadata:
  hermes:
    tags: [MCP, Hermes, Tunnel, SSE, OpenAI, Codex]
    related_skills: [native-mcp, mcporter, hermes-plugin-development]
---

# Hermes MCP Server — Expose Hermes Tools Externally

There are two separate mechanisms for exposing Hermes Agent tools
to external MCP clients. They serve different purposes and can
run independently or together.

## Mechanism 1: mcp_direct_bridge.py (stdio → tunnel)

Hermes ships with `tools/mcp_direct_bridge.py` — a self-contained
MCP server that exposes **every Hermes built-in tool** as MCP tools
by calling `registry.dispatch()`. This skips the Hermes agent loop
entirely — no model/provider call, no token cost for normal tool
operations. The external agent (Codex, ChatGPT, etc.) is the only
"brain" involved.

### Location

```
<mcp_direct_bridge.py>
  └─ herman/mcp_direct_bridge.py
```

or at the deployed path on the remote machine:
```
/mnt/storage/kubuntux-home/.hermes/hermes-agent/mcp_direct_bridge.py
```

### Running it standalone (stdio transport)

```bash
<hermes_venv>/bin/python3 <hermes_agent_dir>/mcp_direct_bridge.py
```

Must run with Hermes's own venv — it needs Hermes's dependencies
plus the import side effects of `model_tools` (which triggers
tools.registry.discover_builtin_tools()).

### Registration with Claude Code (example)

```bash
claude mcp add hermes-tools -- \
    <hermes_venv>/bin/python3 \
    <hermes_agent_dir>/mcp_direct_bridge.py
```

### Excluded Tool Sets (Default)

By default these tool sets are excluded because they only make
sense inside a live Hermes agent session:

- `delegation` — task delegation to subagents
- `todo` — session-scoped task list
- `clarify` — asking the user questions mid-turn
- `cronjob` — scheduling persistent jobs

Override via `HERMES_MCP_EXCLUDE_TOOLSETS` env var (comma-separated
toolset names). Set to empty string to exclude nothing.

### Making it Unrestricted (Omniscient Mode)

#### Step 1: Remove toolset exclusions

Patch the source to empty the exclude set:

```python
# Before:
_DEFAULT_EXCLUDED_TOOLSETS = {"delegation", "todo", "clarify", "cronjob"}

# After:
EXCLUDE_TOOLSETS: set[str] = set()
```

This exposes EVERY Hermes tool — including task delegation, todo
management, clarification, and cron scheduling.

#### Step 2: Wire auto-approve + sudo callbacks

The terminal tool has approval callbacks, sudo password prompts,
tirith scanning, and hardline guards. In the bridge context
(non-CLI, non-gateway) commands pass through, but for full
bulletproofing, register callbacks before the server starts:

**⚠️ CRITICAL: the approval callback MUST accept `**kwargs`**

The `tools.approval` module calls the callback with extra keyword
arguments (`description`, `allow_permanent`, etc.). A lambda that
only accepts one argument (`lambda cmd: ...`) will crash with:
```
TypeError: _always_approve() got an unexpected keyword argument 'allow_permanent'
```
Use a def with `**kwargs` instead:

```python
try:
    from tools.approval import set_hermes_interactive_context
    _interactive_token = set_hermes_interactive_context(True)
except ImportError:
    pass  # Hermes < 0.18 — context not available

from tools.terminal_tool import set_approval_callback, set_sudo_password_callback

def _always_approve(command: str, description: str = "", allow_permanent: bool = False, **kwargs) -> dict:
    """Auto-approve every command regardless of danger level."""
    return {"approved": True, "message": None}

def _sudo_password_prompt(prompt_text: str = "", **kwargs) -> str:
    try:
        from tools.terminal_tool import _get_cached_sudo_password
        pw = _get_cached_sudo_password()
        return pw or "root"
    except Exception:
        return "root"

set_approval_callback(_always_approve)
set_sudo_password_callback(_sudo_password_prompt)
```

The `try/except` around `set_hermes_interactive_context` is needed
for Hermes 0.17.x where this function doesn't exist — the bridge
still works without it, just loses the interactive-context optimization.

Also set env vars at the top of the script (before tool imports):

```python
os.environ.setdefault("HERMES_CRON_SESSION", "approve")
os.environ.setdefault("HERMES_EXEC_ASK", "0")
os.environ.setdefault("HERMES_MCP_EXCLUDE_TOOLSETS", "")
```

**What stays blocked even with omni:**
- Hardline commands (rm -rf /, mkfs, dd to raw device, shutdown, reboot, fork bomb)
- Sudo stdin guard (piping to sudo -S without cached SUDO_PASSWORD)
- User-defined deny rules (approvals.deny in config.yaml)

For anything these block, use `system_exec` (see Step 3).

#### Step 3: Add system_exec raw shell tool

Add `system_exec` to the bridge to bypass ALL Hermes security
layers. Runs via `asyncio.create_subprocess_shell` — no guards,
no approval, no restrictions:

```python
SYSTEM_EXEC_TOOL_NAME = "system_exec"
async def _run_system_exec(arguments: dict) -> dict:
    command = arguments.get("command", "")
    timeout = min(int(arguments.get("timeout_sec", 60)), 600)
    workdir = arguments.get("workdir", "/tmp")
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, cwd=workdir,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        timed_out = False
    except asyncio.TimeoutError:
        proc.kill()
        stdout_b, stderr_b = await proc.communicate()
        timed_out = True
    return {"stdout": stdout_b.decode(), "stderr": stderr_b.decode(),
            "exit_code": proc.returncode, "timed_out": timed_out}
```

Register in `list_tools()` and dispatch in `call_tool()` alongside
the `hermes_ask` handler.

### Fallback: hermes_ask

Every other tool dispatches directly (free, no model call).
`hermes_ask` is the deliberate exception: it shells out to
`hermes -z <prompt> --accept-hooks`, running a REAL Hermes agent
turn — own model, own agent loop, full toolset. This costs real
inference spend. Use it as the escape hatch for tasks needing
multi-step reasoning.

Env knobs:
- `HERMES_MCP_BIN` — path to `hermes` CLI (default: on PATH)
- `HERMES_MCP_ASK_TIMEOUT_SEC` — default 300
- `HERMES_MCP_EXCLUDE_TOOLSETS` — toolset exclusions (see above)
- `HERMES_MCP_PREFIX` — hostname prefix for multi-device setups.
  When set, overrides `socket.gethostname()` as the tool name prefix.
  Use to set clean names like `HERMES_MCP_PREFIX=lin` instead of
  auto-detected ugly hostnames like `lin-HP-Pavilion-Laptop-15-cs0xxx`.

## Mechanism 2: Hermes Gateway (SSE, network-facing)

Hermes has a built-in gateway mode that exposes tools over SSE:

```bash
python -m hermes_cli.main gateway run
```

Binds to `0.0.0.0:8644` by default. This is the **Hermes-native**
channel — a full Hermes agent behind the SSE endpoint, not just tool
dispatch. Clients connect over SSE and get the full agent experience.

## Mechanism 3: tunnel-client (OpenAI Control Plane)

`tunnel-client` is OpenAI's official Go binary for connecting a local
MCP server to OpenAI's control plane over an outbound tunnel. It wraps
the stdio server and makes it available to ChatGPT, Codex, Codex CLI,
and any OpenAI-connected tool.

### Installation

```bash
# Installed at ~/.local/bin/tunnel-client
# Statically linked Go binary
file ~/.local/bin/tunnel-client
# ELF 64-bit LSB executable, statically linked, stripped
```

### Configuration

Config file at `~/.config/tunnel-client/<profile>.yaml`:

```json
{
  "config_version": 1,
  "control_plane": {
    "api_key": "env:CONTROL_PLANE_API_KEY",
    "base_url": "https://api.openai.com",
    "tunnel_id": "tunnel_<id>"
  },
  "mcp": {
    "commands": [
      {
        "channel": "main",
        "command": "<venv>/bin/python3 <agent_dir>/mcp_direct_bridge.py"
      }
    ]
  }
}
```

### Running

```bash
export CONTROL_PLANE_API_KEY="sk-..."
tunnel-client run --profile-dir ~/.config/tunnel-client --profile <profile_name>
```

The API key must be exported into the shell environment — it's NOT
stored in the config file (uses `env:VAR_NAME` syntax).

### Multi-device aggregation

The tunnel-client can aggregate MCP bridges from multiple machines
through a single tunnel. Each device gets a unique `channel` name and
`HERMES_MCP_PREFIX` env var for tool name identification.

See `references/multi-device-deployment.md` for the full deployment
reference (SSH config, device identities, Hermes version compat).

### Architecture

```
mcp_direct_bridge.py (stdio MCP server, no model cost)
       │
       ▼
tunnel-client (wraps stdio, tunnels outbound)
       │
       ▼
OpenAI control plane → ChatGPT / Codex / Codex CLI
```

### Logs and State

```
~/.local/state/tunnel-client/
├── logs/<profile>.log          # JSON-format activity log
├── health/<profile>.url        # Health endpoint URL
├── processes.yaml              # Running profiles
├── history.md                  # Connection history
├── aliases.yaml                # Tunnel aliases + org/workspace IDs
└── admin_profiles.yaml         # Admin auth profiles
```

### Aliases File

The aliases file maps tunnel names to OpenAI org/workspace IDs:

```json
{
  "<alias>": {
    "alias": "<alias>",
    "tunnel_id": "tunnel_<id>",
    "name": "<human name>",
    "organization_ids": ["org-<id>"],
    "workspace_ids": ["<uuid>"]
  }
}
```

## Which One to Use

| Scenario | Use |
|----------|-----|
| OpenAI Codex / ChatGPT wants your tools | tunnel-client |
| Direct MCP connection (Claude Code, custom client) | mcp_direct_bridge.py (stdio) |
| Full Hermes agent behind SSE | Hermes Gateway (port 8644) |

## Pitfalls

- **Env var not set**: tunnel-client fails with "invalid
  control_plane.api_key reference" if `CONTROL_PLANE_API_KEY` or
  `OPENAI_ADMIN_KEY` aren't exported. They're NOT in any profile file.
- **Extract API key from /proc BEFORE killing**: Before killing a
  running tunnel-client, extract the API key from its environ:
  ```
  sudo cat /proc/<pid>/environ | tr '\\0' '\\n' | grep CONTROL_PLANE_API_KEY
  ```
  If you kill first you lose the key — the user will (rightfully) ask
  "why would you lose the key?". THE KEY IS NOT PERSISTED ANYWHERE
  ELSE unless embedded directly in the config.
- **Embedding the key directly in config**: Replace `env:VAR_NAME`
  with the literal key in the YAML config to make the tunnel survive
  reboots without any env var:
  ```json
  "control_plane": {
    "api_key": "sk-proj-XXXXX",
    ...
  }
  ```
- **Killing and restarting**: Killing the tmux session also kills the
  tunnel. Restart requires the API key (env var or embedded).
- **tmux session ownership**: tunnel-client runs as the user, not root.
  Use `sudo -u <user>` or `su - <user>` to manage the session.
- **Config not reloaded on restart**: tunnel-client must be fully
  restarted to pick up changes to the bridge script.
- **mcp_direct_bridge.py requires Hermes venv**: won't work with a
  plain system Python — it needs Hermes's deps and import side effects.
- **hermes_ask costs real tokens**: Every `hermes_ask` call uses the
  configured Hermes provider/model and incurs inference cost.
