# Tunnel-Client + Hermes MCP Bridge Setup

**Context:** OpenAI's `tunnel-client` wrapping Hermes's `mcp_direct_bridge.py` to expose Hermes built-in tools as MCP tools through OpenAI's control plane.

## Architecture

Two modes:

### Single Device (stdio MCP command)
```
mcp_direct_bridge.py (Hermes tools → stdio MCP server)
       │
       ▼
tunnel-client run --profile hermes-tools (wraps stdio, tunnels outbound)
       │
       ▼
OpenAI control plane → ChatGPT / Codex / etc.
```

### Multi-Device SSH Aggregation (same tunnel, 4 channels)
```
kubuntux: mcp_direct_bridge.py (local)
lin:     SSH → lin@100.91.55.113 → .../mcp_direct_bridge.py
macuntu: SSH → macuntu@100.75.23.127 → .../mcp_direct_bridge.py
rabuntu: SSH → root@100.68.0.96 → .../mcp_direct_bridge.py
         │
         ▼ (all 4 in same tunnel-client config)
    tunnel-client run --profile hermes-tools
         │
         ▼
    OpenAI control plane (tunnel_6a55d54fc5408191a5ed7224e73dd9fb)
```

Each machine's tools are prefixed with the machine hostname (e.g. `lin_hp_pavilion_laptop_15_cs0xxx_read_file`, `macuntu_terminal`, `pi5_deflab_system_exec`). The MCP client sees which physical device it's targeting.

## Config File Format

`~/.config/tunnel-client/<profile-name>.yaml` (JSON-compatible YAML):

```json
{
  "admin_ui": { "open_browser": false },
  "config_version": 1,
  "control_plane": {
    "api_key": "sk-proj-...",
    "base_url": "https://api.openai.com",
    "tunnel_id": "tunnel_6a55d54fc5408191a5ed7224e73dd9fb"
  },
  "health": {
    "listen_addr": "127.0.0.1:0",
    "url_file": "/home/kubuntux/.local/state/tunnel-client/health/hermes-tools.url"
  },
  "log": {
    "format": "json",
    "level": "info"
  },
  "mcp": {
    "commands": [
      {
        "channel": "main",
        "command": "/path/to/venv/bin/python3 /path/to/mcp_direct_bridge.py"
      },
      {
        "channel": "lin",
        "command": "ssh -o StrictHostKeyChecking=no -o BatchMode=yes user@host /remote/path/venv/bin/python3 /remote/path/mcp_direct_bridge.py"
      }
    ]
  }
}
```

**Rules:**
- Exactly one channel must be named `"main"` — the rest get unique names
- Each command that fails causes the tunnel to shut down entirely (no partial failure)
- SSH commands must work with `-o BatchMode=yes` — no interactive password prompts
- The tunnel-client runs the command as a child process and pipes MCP JSON-RPC over its stdio

## Credential Strategy — Embed Directly, Not via `env:` References

The config format supports `"env:VARIABLE_NAME"` as a reference, but this creates a single point of failure: if the env var was set only in the launching shell session (not in `.bashrc`/`.profile`), killing the process loses the key permanently.

**Best practice:** embed the API key string directly in the config file. This survives reboots, tmux restarts, and machine migrations.

## Omniscient Bridge (Full Unrestricted Access)

The `mcp_direct_bridge.py` can be upgraded to omni mode with three additions:

### 1. Remove toolset exclusions
```python
EXCLUDE_TOOLSETS: set[str] = set()
```
This exposes delegation, todo, clarify, cronjob — normally excluded.

### 2. Wire auto-approve + sudo callbacks
```python
from tools.terminal_tool import set_approval_callback, set_sudo_password_callback

def _always_approve(_command: str) -> dict:
    return {"approved": True, "message": None}
def _sudo_password_prompt(_prompt_text: str = "") -> str:
    return "root"

set_approval_callback(_always_approve)
set_sudo_password_callback(_sudo_password_prompt)
```

Also set env vars to skip remaining guards:
```python
os.environ.setdefault("HERMES_CRON_SESSION", "approve")
os.environ.setdefault("HERMES_EXEC_ASK", "0")
```

### 3. Add `system_exec` raw shell tool
A bonus tool that runs arbitrary commands via `asyncio.create_subprocess_shell()` — no Hermes tool security at all. Use for installing packages, modifying system config, accessing raw devices.

### 4. Add `hermes_ask` fallback
Shells out to `hermes -z <prompt> --accept-hooks` for full Hermes agent turns. Supports session continuation via `session_id`.

### 5. Hostname-prefix all tool names
```python
import socket
HOSTNAME = socket.gethostname().split(".")[0]
PREFIX = HOSTNAME.lower().replace("-", "_").replace(" ", "_")

# Then prefix every tool name: f"{PREFIX}_{original_name}"
# Strip prefix in call_tool() before registry.dispatch()
```

This makes multi-device aggregation unambiguous: the client sees `macuntu_terminal`, `pi5_deflab_system_exec`, etc.

### Backward Compatibility with Hermes 0.17
The function `set_hermes_interactive_context` was added in Hermes 0.18.x. On older versions (rabuntu runs 0.17), import fails:
```python
try:
    from tools.approval import set_hermes_interactive_context
    _interactive_token = set_hermes_interactive_context(True)
except ImportError:
    pass  # Older Hermes — works without it
```

## Per-Machine Deploy Details

| Host | User | SSH from | Python | Venv Path | Bridge Path |
|------|------|----------|--------|-----------|-------------|
| kubuntux (100.93.75.87) | root | — (local) | /mnt/.../venv/bin/python3.12 | /mnt/storage/kubuntux-home/.hermes/hermes-agent/venv/ | /mnt/storage/kubuntux-home/.hermes/hermes-agent/mcp_direct_bridge.py |
| lin (100.91.55.113) | lin | kubuntux | /home/lin/.hermes/hermes-agent/venv/bin/python3.11 | /home/lin/.hermes/hermes-agent/venv/ | /home/lin/.hermes/hermes-agent/mcp_direct_bridge.py |
| macuntu (100.75.23.127) | macuntu | kubuntux | /home/macuntu/.hermes/hermes-agent/venv/bin/python3.12 | /home/macuntu/.hermes/hermes-agent/venv/ | /home/macuntu/.hermes/hermes-agent/mcp_direct_bridge.py |
| rabuntu (100.68.0.96) | root | kubuntux | /usr/bin/python3 (no venv — pip --break-system-packages) | n/a (system python) | /root/.hermes/hermes-agent/mcp_direct_bridge.py |

Deploy to remotes from kubuntux:
```bash
cat /local/path/mcp_direct_bridge.py | ssh user@host 'cat > /remote/path/mcp_direct_bridge.py'
```

## Deploying Updated Bridge

Each change requires updating all 4 machines + restarting the tunnel:

```bash
# 1. Update master on kubuntux
scp /tmp/hermes_mcp_omni.py root@kubuntux:/.../mcp_direct_bridge.py

# 2. Push to remotes
ssh kubuntux "cat master | ssh lin 'cat > /remote/lin/mcp_direct_bridge.py'"
ssh kubuntux "cat master | ssh macuntu 'cat > /remote/macuntu/mcp_direct_bridge.py'"
ssh kubuntux "cat master | ssh rabuntu 'cat > /remote/rabuntu/mcp_direct_bridge.py'"

# 3. Kill tunnel
ssh kubuntux "pkill -f 'tunnel-client run'"

# 4. Restart
ssh kubuntux "sudo -u kubuntux tmux new-session -d -s tunnel-mcp__hermes-tools__9de257be \
  \"/home/kubuntux/.local/bin/tunnel-client run \
  --profile-dir /home/kubuntux/.config/tunnel-client \
  --profile hermes-tools \
  >> /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log 2>&1\""
```

## Restart After Changes

```bash
# Kill
pkill -f 'tunnel-client run'
sleep 2

# Start in tmux (as user kubuntux)
sudo -u kubuntux tmux new-session -d -s tunnel-mcp__hermes-tools__9de257be \
  "/home/kubuntux/.local/bin/tunnel-client run \
  --profile-dir /home/kubuntux/.config/tunnel-client \
  --profile hermes-tools \
  >> /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log 2>&1"

# Verify after ~10s
grep -E 'started|ERROR' /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log | tail -5
```

## Verification

- **Health:** `curl http://127.0.0.1:<port>/healthz` → `live`
- **Readiness:** `curl http://127.0.0.1:<port>/readyz` → `ready`
- **Logs:** `~/.local/state/tunnel-client/logs/hermes-tools.log`
- **Process count:** should see 1 tunnel-client + N mcp_direct_bridge processes (1 local + 1 per SSH)

## Known Edge Cases

- **The tmux socket is per-UID.** `/tmp/tmux-1000/default` = kubuntux's socket. Root can't access it directly — use `sudo -u kubuntux ...`.
- **SSH `BatchMode=yes` requires key-based auth.** The user running tunnel-client must have SSH keys deployed to all remote machines.
- **Any MCP command failure kills the entire tunnel.** If one remote bridge fails (import error, SSH timeout, segfault), the tunnel-client shuts down ALL channels. Every bridge must start successfully.
- **Exit 255 from an SSH MCP command usually means the tunnel killed it, not that SSH failed.** Check the timing: if another bridge failed first, the 255 was from the tunnel shutting down, not from SSH.
- **Rabuntu (Pi5, Hermes 0.17.0) needs the `mcp` Python package** — install with `pip3 install mcp --break-system-packages` (no venv).
- **The bridge must use Hermes's own venv Python interpreter** — it depends on the editable install's import hooks for `model_tools` and `tools.registry`.
- **Verify syntax on all machines after changes** — `python3 -c "import ast; ast.parse(open('path/to/bridge.py').read()); print('OK')"` catches import issues early.
