---
name: mcp-tunnel-client
description: "Manage OpenAI Secure MCP tunnel-client daemon — install, configure profiles, run foreground/background, verify health, and troubleshoot the bridge that connects local MCP servers to ChatGPT, Codex, and the Responses API."
version: 1.0.1
author: Hermes
---

# MCP Tunnel Client (OpenAI Secure MCP Tunnel)

`tunnel-client` is OpenAI's customer-run agent for Secure MCP Tunnel. It connects
a private or localhost MCP server to ChatGPT, Codex, the Responses API, and AgentKit
through an OpenAI-hosted MCP tunnel endpoint, keeping the MCP server off the public internet.

Use it when:
- You have an MCP server on a private network that needs to reach an OpenAI-hosted product
- Security won't approve inbound firewall rules
- You want a daemon with `/healthz`, `/readyz`, `/metrics`, and `/ui`

---

## Trigger

Use when the user says:
- "fix the chatgpt connector tunnel"
- "start the openai tunnel"
- "tunnel-client is not running" / "tunnel is down"
- "set up MCP tunnel to ChatGPT"
- "tunnel-client run" or "tunnel-client doctor"
- "expose the other mcp servers" / "expose mcp servers through tunnel"

## Prerequisites

- tunnel-client binary installed (Go, `~/.local/bin/tunnel-client` or similar)
- OpenAI account with tunnel permissions (Tunnels Read + Use)
- CONTROL_PLANE_TUNNEL_ID — from `https://platform.openai.com/settings/organization/tunnels` or `tunnel-client admin tunnels create`
- CONTROL_PLANE_API_KEY — from Runtime API keys `https://platform.openai.com/settings/organization/api-keys`
- OPENAI_ADMIN_KEY — only for tunnel management commands, not for the daemon

## Installation

### From source
```bash
git clone https://github.com/openai/tunnel-client
cd tunnel-client
make admin-ui         # builds the admin UI assets (optional)
go build -o bin/tunnel-client ./cmd/client
mv bin/tunnel-client ~/.local/bin/
```

### Verify
```bash
tunnel-client help quickstart
```

## Profile Configuration

Profiles live in `~/.config/tunnel-client/<profile-name>.yaml`.

### Standard profile structure
```yaml
config_version: 1
control_plane:
  api_key: "sk-pro..."      # Runtime API key (CONTROL_PLANE_API_KEY)
  base_url: "https://api.openai.com"
  tunnel_id: "tunnel_..."   # From Tunnels management
health:
  listen_addr: "127.0.0.1:0"    # :0 = random port
  url_file: "/home/user/.local/state/tunnel-client/health/<profile>.url"
log:
  format: json
  level: info
mcp:
  commands:
    - channel: main
      command: "python3 /path/to/mcp_server.py"
    - channel: remote
      command: "ssh user@host 'python3 /path/to/mcp_server.py'"
admin_ui:
  open_browser: false
```

### MCP commands over SSH
For multi-machine setups, use SSH commands to bridge remote MCP servers:
```yaml
mcp:
  commands:
    - channel: main
      command: "env PREFIX=kubuntux python3 /path/to/mcp_direct_bridge.py"
    - channel: remote1
      command: "ssh -o StrictHostKeyChecking=no -o BatchMode=yes user@host 'env PREFIX=remote1 python3 /path/remote_bridge.py'"
```

Each `channel` appears as a separate MCP endpoint in ChatGPT/Codex.

## Checking Runtime Status

Before running, check what exists:

```bash
# List registered runtimes and their tunnel IDs
tunnel-client runtimes list

# Check a specific runtime's actual process state
tunnel-client runtimes status <profile-name>
# Shows: running | stopped | not registered
```

A runtime can be **registered** (known to the CLI) but **stopped** (no daemon process active). Always check actual status, not just registration.

## Running the Daemon

### Doctor check first (always)
```bash
tunnel-client doctor --profile <profile-name>
# Must show: RESULT ok
# Typical checks: config_source, profile_load, tunnel_id, control_plane_api_key, mcp_target, health_listener, ui
```

### Foreground daemon
```bash
tunnel-client run --profile <profile-name>
```
Output shows:
- Health/UI URL (random port, printed at startup)
- Plugin load warnings (often cosmetic — ignore)
- `tunnel-client started` with tunnel URL on success

### Background via terminal tool (for agent use)
```bash
terminal(command="tunnel-client run --profile <name>", background=True)
```
Then verify with:
```bash
# Get health URL from url_file
cat /home/user/.local/state/tunnel-client/health/<profile>.url
# Check health
curl -s http://127.0.0.1:<port>/healthz   # should say "live"
curl -s http://127.0.0.1:<port>/readyz     # should say "ready"
```

### Persistent runtime via runtimes connect (Codex-managed)
```bash
tunnel-client runtimes connect <alias> --profile <profile-name>
tunnel-client runtimes status <alias>   # should show process_running, healthy, ready
```
Use `--json` flag for programmatic checks.

### Persistent via systemd user service (Linux, survives reboot)

The most reliable persistence on Linux — survives reboots, auto-restarts on crash, no Codex dependency.

**Single profile** — create one service at `~/.config/systemd/user/tunnel-client.service`:

```ini
[Unit]
Description=OpenAI Secure MCP Tunnel - <profile-name>
Documentation=https://github.com/openai/tunnel-client
After=network-online.target network.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=%h/.local/bin/tunnel-client run --profile <profile-name>
Restart=always
RestartSec=5
Nice=-5

[Install]
WantedBy=default.target
```

> **`Restart=always` vs `Restart=on-failure`**: Always use `Restart=always`. When all MCP bridges drop (SSH failures, network blips), the tunnel exits cleanly with code 0. `on-failure` treats that as normal shutdown and won't restart. `always` catches it.

No `Environment=` line needed — tunnel-client reads the API key from the profile YAML directly.

**Multiple profiles concurrently** — create one service **per profile** using unique names:

| Profile | Service file |
|---------|-------------|
| `hermes-tools` | `~/.config/systemd/user/tunnel-client.service` |
| `openclaw-tools` | `~/.config/systemd/user/tunnel-client-openclaw.service` |
| any other | `~/.config/systemd/user/tunnel-client-<profile>.service` |

Only the **primary** profile uses the bare `tunnel-client.service` name; all others append a dash + profile name. This keeps tab-completion clean (`tunnel-client-` + Tab shows all).

**2. Enable and start all:**
```bash
systemctl --user daemon-reload
systemctl --user enable tunnel-client.service tunnel-client-openclaw.service
systemctl --user start tunnel-client.service tunnel-client-openclaw.service
```

**3. Verify each:**
```bash
systemctl --user status tunnel-client.service
systemctl --user status tunnel-client-openclaw.service
# Should show: active (running), enabled
# The process tree includes the tunnel-client binary + all MCP subprocesses
# (python bridge scripts, SSH tunnels to remote machines, Node/TSX bridges, etc.)
```

**4. Check logs individually:**
```bash
journalctl --user -u tunnel-client.service -n 50 --no-pager
journalctl --user -u tunnel-client-openclaw.service -n 50 --no-pager
```

## Health Verification

```bash
# From the health URL file
HEALTH_URL=$(cat /home/user/.local/state/tunnel-client/health/<profile>.url)
curl -s $HEALTH_URL/healthz     # "live"
curl -s $HEALTH_URL/readyz      # "ready"
curl -s $HEALTH_URL/metrics     # Prometheus: poll cycles, queue length, workers

# Web UI
# Open $HEALTH_URL/ui in a browser

# Runtime status (if using runtimes)
tunnel-client runtimes status <alias>
```

## Multi-MCP Server Channels (Mixed Types)

Beyond SSH clones of the same bridge, a tunnel profile can mix **different MCP server types** as separate channels. Each channel runs its own stdio MCP server — all under the same tunnel.

```yaml
mcp:
  commands:
    - channel: main           # Primary — your app's toolset
      command: "node --import tsx src/mcp/bridge.ts"
    - channel: tailscale      # Secondary — Tailscale network tools
      command: "/path/to/tailscale-mcp-server"
    - channel: linode         # Secondary — Linode cloud API
      command: "npx -y @takashito/linode-mcp-server -t <TOKEN> -c instances,networking,regions,volumes,databases"
    - channel: nexus          # Secondary — stdio-to-HTTP bridge
      command: "python3 /path/to/nexus-mcp-bridge.py"
```

Each channel appears as a separate MCP endpoint in ChatGPT/Codex, distinct from the tool namespace of `main`.

### Stdio-to-HTTP MCP Bridge Pattern

When an MCP server only speaks HTTP (e.g. a REST-based MCP endpoint), you can wrap it with a lightweight stdio bridge script. The script:

1. Reads JSON-RPC messages from stdin (MCP stdio protocol)
2. Forwards `tools/call` as HTTP POST to the remote MCP endpoint
3. Responds to `tools/list` from a cached discovery result (fetched at startup)
4. Logs to stderr so stdio stays protocol-clean

Key implementation points:
- **Tool discovery at startup**: Call `tools/list` once on the HTTP endpoint and cache the result. Respond to `tools/list` from cache, not live queries.
- **Initialize response**: Respond with capabilities including `{"tools": {}}` — the stdio MCP client needs this to know the server is ready.
- **Notifications**: `notifications/initialized` gets no response (JSON-RPC notification pattern).

### Creating a systemd service per profile

Each profile gets its own service name. The primary profile uses the bare name; all others append a dash + profile name:

| Profile | Service file |
|---------|-------------|
| `hermes-tools` (primary) | `~/.config/systemd/user/tunnel-client.service` |
| `openclaw-tools` | `~/.config/systemd/user/tunnel-client-openclaw.service` |

After creating a new service file:
```bash
systemctl --user daemon-reload
systemctl --user enable --now tunnel-client-openclaw.service
```

## Troubleshooting

### Common issues

| Issue | Fix |
|-------|-----|
| `doctor` fails: invalid profile name | Use profile NAME not file path: `--profile hermes-tools` not `--profile /path/to/yaml` |
| `doctor` fails: control_plane_api_key | Export `OPENAI_API_KEY` env var with the Runtime API key, or re-check the profile's `api_key` field |
| `run` exits immediately | Check `tunnel_id` is valid on the platform page. Check API key has Tunnels Read + Use permissions |
| Health URL changes every restart | Random port is expected — read the url_file after each start |
| SSH-based MCP commands fail | Verify SSH keys, hostnames, `StrictHostKeyChecking=no`, and `BatchMode=yes` |
| Plugin load warnings | Cosmetic — these are non-MCP plugins that don't have register() functions |
| Codex detected without Tunnel MCP plugin | Run `tunnel-client codex plugin install` if using Codex integration |
| `Failed to load plugin 'nexus-memory': No __init__.py` | Expected when the plugin dir exists without __init__.py — harmless for tunnel-client |
| `tunnel-client run` exits: `main channel is required` | No MCP command has `channel: main`. At least one commands entry must be named `main`. Rename your primary channel or add one. |

### MCP server not reachable from ChatGPT
1. Verify the daemon is running: `ps aux | grep tunnel-client`
2. Check health: `curl -s $(cat ~/.local/state/tunnel-client/health/<profile>.url)/healthz`
3. Check the connector in ChatGPT settings: `https://chatgpt.com/#settings/Connectors`
4. The connector must be created/verified while the daemon is healthy
5. Check the tunnel metadata matches: `tunnel_id` in profile vs platform page

## Profile listing and management

```bash
# List all profiles
tunnel-client profiles list

# Run doctor on a profile
tunnel-client doctor --profile <name>

# List registered runtimes
tunnel-client runtimes list

# Disconnect a runtime
tunnel-client runtimes disconnect <alias>

# List all commands
tunnel-client help
```

## Reference files

- `references/hermes-multi-machine-setup.md` — multi-machine tunnel config (Hermes + OpenClaw on kubuntux, lin, macuntu, rabuntu)
- `references/openclaw-bridge-tools.md` — full tool inventory of what the OpenClaw bridge exposes through the tunnel (~35+ prefixed tools)
- `references/stdio-http-mcp-bridge.md` — walkthrough of building an stdio-to-HTTP MCP bridge with a working Python example (Nexus Memory bridge)

## Network Tuning for Tunnel Speed

The tunnel-client uses HTTPS (TCP) to `api.openai.com:443`. If the tunnel feels slow:

- **It's not a WireGuard/Tailscale issue** — it's generic TCP throughput
- **Tune the kernel TCP stack**: BBR + fq congestion control, RPS/RFS (spread RX IRQs), buffer sizing, TCP fastopen
- See `linux-network-performance-tuning` → `references/tunnel-client-optimization-context.md` for the full guide with verified numbers

Baseline on kubuntux: OpenAI API ~11ms latency, DNS ~8ms, internet ~88/79 Mbps.

## Pitfalls

- **`Restart=on-failure` misses clean exits**: When all MCP bridges (especially SSH-based ones) fail, the tunnel client shuts down gracefully with exit code 0. Systemd treats exit 0 as success, so `Restart=on-failure` does NOT restart it. Use `Restart=always` instead so it auto-recovers from total-bridge-failure scenarios. The 5s `RestartSec` prevents restart loops if the underlying issue persists.
- **Random health ports**: `health.listen_addr: "127.0.0.1:0"` means a random port. Read the url_file after starting to find it. Don't hardcode port numbers.
- **`channel: main` is mandatory**: At least one MCP command must have `channel: main`. If all channels use custom names, the daemon exits with error. Always keep one as `main`.
- **API key redaction by read_file**: The `read_file` tool redacts `sk-*` values from config files. To get the raw key, use `grep -o` via terminal or `python3 -c "import json; print(json.load(open('file.yaml'))['key'])"` instead.
- **API key vs Admin key**: Use Runtime API keys (`CONTROL_PLANE_API_KEY`) for the daemon. Admin keys (`OPENAI_ADMIN_KEY`) are only for `tunnel-client admin tunnels` commands.
- **Profile vs file path**: `--profile` expects the profile name (basename without `.yaml`), not a filesystem path.
- **Connector setup order**: The ChatGPT connector must be created/verified while the daemon is running — the daemon needs to be healthy for connector discovery to work.
- **Multiple channels**: Each `channel` in the profile's MCP commands becomes a separate endpoint in ChatGPT. Name them descriptively.
- **Background daemon lifecycle**: A `tunnel-client run` started via `terminal(background=True)` dies when the parent session ends. For durability, use `runtimes connect` or a systemd --user unit.
- **Multi-service pitfalls**: Each systemd service runs independently. Stopping one doesn't affect the other — check the right service name. The `tunnel-client.service` name is reserved for the primary profile; secondary profiles get `tunnel-client-<profile>.service`. Tab-complete with `tunnel-client-` to see all. Run `daemon-reload` after creating any new service file.

## Verification checklist

```bash
# 1. Profile loads
tunnel-client doctor --profile <name> | grep -q "RESULT ok" && echo "PASS" || echo "FAIL"

# 2. Daemon started
HEALTH_URL=$(cat ~/.local/state/tunnel-client/health/<name>.url 2>/dev/null)

# 3. Health endpoints
curl -sf "$HEALTH_URL/healthz" | grep -q "live" && echo "HEALTHY" || echo "UNHEALTHY"
curl -sf "$HEALTH_URL/readyz" | grep -q "ready" && echo "READY" || echo "NOT READY"

# 4. Tunnel metadata
curl -sf "$HEALTH_URL/metrics" | grep -q "commands_poll" && echo "POLLING" || echo "NOT POLLING"
```
