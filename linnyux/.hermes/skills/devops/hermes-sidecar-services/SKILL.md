---
name: hermes-sidecar-services
description: "Install and manage Hermes companion sidecar services that run alongside the gateway — services installed via `hermes plugins install` that are standalone daemons (TCP servers, HTTP consoles, etc.) rather than MCP tool plugins."
version: 1.0.0
author: Hermes
---

# Hermes Sidecar Services

Some Hermes companion apps are installed via `hermes plugins install <owner/repo>` but are **not** Hermes MCP plugins — they are standalone sidecar services (TCP servers, HTTP consoles, etc.) that run alongside the Hermes gateway. This skill covers how to install, distinguish, and daemonize them.

---

## Trigger

Use when the user says:
- "install the hermes companion"
- "set up phone desktop collaboration"
- "install the mesh broker"
- `hermes plugins install` shows warning about missing `plugin.yaml`

## How Hermes Plugins vs Sidecars Differ

| Aspect | MCP Plugin | Sidecar Service |
|--------|-----------|----------------|
| Entry point | `plugin.yaml` + `tools.py` | Standalone Python module |
| Installed via | `hermes plugins install` | `hermes plugins install` |
| Provides tools? | Yes (MCP tools to the agent) | No (TCP/HTTP service to external clients) |
| Enabled via | `hermes plugins enable <name>` | N/A — won't show in plugin list |
| Runs as | Loaded by gateway | System daemon (systemd --user) |
| Example | nexus-memory, rtk-rewrite | Hermes Android Companion (mesh broker) |

## Installation Pattern

### 1. Install via Hermes (clones the repo)

```bash
hermes plugins install owner/repo-name
```

This clones the repo to `~/.hermes/plugins/<repo-name>/`. You'll see a warning like:

```
Warning: <name> doesn't contain plugin.yaml or __init__.py.
It may not be a valid Hermes plugin.
```

**This warning is expected for sidecar services** — ignore it. The plugin will NOT appear in `hermes plugins list` and `hermes plugins enable` will fail.

### 2. Create the service venv

Sidecar services need their own isolated venv to avoid PEP 668 / externally-managed-environment errors:

```bash
VENV="$HOME/.hermes/mesh/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -r handoff/requirements.txt
```

The companion app's `mesh-start.sh` creates this at `~/.hermes/mesh/venv/` automatically.

### 3. Install as a systemd --user daemon

```bash
PLUGIN_DIR="$HOME/.hermes/plugins/<repo-name>"
VENV="$HOME/.hermes/mesh/venv"
PY="$VENV/bin/python3"
LABEL="com.hermesagent.mesh"

mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/$LABEL.service" << UNIT
[Unit]
Description=Hermes Mesh broker — phone↔desktop task dispatch + handoff
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=$PY -m handoff.mesh_broker
WorkingDirectory=$PLUGIN_DIR
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable --now "$LABEL.service"
```

### 4. Verify the service

```bash
systemctl --user is-active "$LABEL.service"    # should say "active"
ss -tlnp | grep 51379                          # broker listening on fixed port
journalctl --user -u "$LABEL.service" --no-pager | grep -E "(bound|Console|device|did)"
```

## Hermes Android Companion — Specifics

- **Repo**: `HenWorks/Hermes-agent-android-PC-companion-app`
- **Port**: fixed `51379` (LAN-only bind, never 0.0.0.0)
- **Console**: random `127.0.0.1:<port>` (printed at startup)
- **Pairing**: 5-minute window opens at startup — phone scans QR to pair
- **mDNS**: advertises as `_hermes-mesh._tcp.local.`
- **Capabilities**: task dispatch (push/poll/ack) + conversation handoff (pull/push_session)
- **Security**: NaCl Box e2e, private keys never leave device, never touches auth.json/.env

### Tailscale / Cross-Network Binding

For phone-on-4G or different-WiFi scenarios, bind the broker to the Tailscale IP instead of the LAN IP:

```bash
# Pass via --host flag in ExecStart
ExecStart=/path/to/venv/bin/python3 -m handoff.mesh_broker --host 100.XX.XX.XX

# Or via MESH_HOST env var
MESH_HOST=100.XX.XX.XX /path/to/venv/bin/python3 -m handoff.mesh_broker
```

Get the Tailscale IP: `tailscale ip -4`

When bound to Tailscale, the pairing QR/host field reflects that IP so the phone app connects over the tailnet instead of the local subnet.

**Updating an already-installed systemd unit** — edit `ExecStart` in the unit file, then:
```bash
systemctl --user daemon-reload
systemctl --user restart com.hermesagent.mesh.service
```

### Providing the Pairing Code

When the user needs to pair their phone:

1. Give the **compact JSON text code** only — the phone app can paste this directly. Do not dump the full ASCII QR art (it's unreadable once the terminal fills).
2. Point them to the **browser console URL** (`http://127.0.0.1:<port>/`) for the actual QR image if they prefer scanning.
3. Retrieve both from the journal:

```bash
journalctl --user -u com.hermesagent.mesh.service --no-pager | grep -E '\{"v":1'
```

## Management Commands

```bash
# Status
systemctl --user status com.hermesagent.mesh.service

# Stop
systemctl --user stop com.hermesagent.mesh.service

# Restart
systemctl --user restart com.hermesagent.mesh.service

# Uninstall
systemctl --user disable --now com.hermesagent.mesh.service
rm -f "$HOME/.config/systemd/user/com.hermesagent.mesh.service"
systemctl --user daemon-reload
rm -rf "$HOME/.hermes/plugins/Hermes-agent-android-PC-companion-app"
```

## Pitfalls

| Issue | Fix |
|-------|-----|
| `hermes plugins enable <name>` says "not installed" | Sidecar doesn't have plugin.yaml — skip enable, run as systemd instead |
| `python: command not found` | Use `python3` explicitly (no `python` on Debian/Ubuntu without python-is-python3) |
| `pip install: externally-managed-environment` | Create an isolated venv — never use `--break-system-packages` |
| Broker bound to wrong interface | Set `MESH_HOST=<Tailscale IP>` env var for cross-network |
| Console URL port changes every restart | `companion_web.py` picks a random port. Don't bookmark it — find the current URL via `journalctl --user -u com.hermesagent.mesh.service \| grep "Console:"` |
| Port 51379 already in use | Check with `ss -tlnp \| grep 51379`; companion expects a fixed port for phone persistence |
| Pairing window expired (5-min default) | Restart the service: `systemctl --user restart com.hermesagent.mesh.service` — window reopens at startup |

## Verification

```bash
# Is the broker running?
systemctl --user is-active com.hermesagent.mesh.service

# Is it listening?
ss -tlnp | grep 51379

# Can you reach the console?
curl -s --connect-timeout 3 http://127.0.0.1:$(journalctl --user -u com.hermesagent.mesh.service --no-pager | grep -oP 'http://127.0.0.1:\K\d+' | tail -1)/ | head -20

# Check the pairing info
journalctl --user -u com.hermesagent.mesh.service --no-pager | grep -E "(\"v\":1|device|did)"
```
