# kubuntux Deployment Reference

## Machine

- Host: kubuntux (100.93.75.87)
- SSH: root@100.93.75.87
- User: kubuntux (UID 1000) — has passwordless sudo
- Hermes venv: `/mnt/storage/kubuntux-home/.hermes/hermes-agent/venv/bin/python3`
- Hermes agent dir: `/mnt/storage/kubuntux-home/.hermes/hermes-agent/`
- Hermes binary: `/home/kubuntux/.local/bin/hermes`
- Bridge script: `/mnt/storage/kubuntux-home/.hermes/hermes-agent/mcp_direct_bridge.py`

## Tunnel Client

- Binary: `/home/kubuntux/.local/bin/tunnel-client` (Go 0.0.10, static ELF)
- Config: `/home/kubuntux/.config/tunnel-client/hermes-tools.yaml`
- Profile: `hermes-tools`
- Tunnel ID: `tunnel_6a55d54fc5408191a5ed7224e73dd9fb`
- OpenAI org: `org-TetD7VwP26h2eXC6mZCu49kM`
- OpenAI workspace: `fe2112b6-4afb-442b-9d45-32acc7f56f4d`
- Logs: `/home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log`
- State dir: `/home/kubuntux/.local/state/tunnel-client/`

## MCP Direct Bridge — Omni Mode (current)

The bridge has been upgraded to full OMNI mode:

| Feature | Detail |
|---------|--------|
| Server name | `hermes-omni` |
| Tool exclusions | **None** — all Hermes tools exposed |
| Approval callbacks | Auto-approve everything wired |
| Sudo callback | Auto-provided (passwordless sudo on host) |
| Interactive ctx | Set to CLI mode |
| Raw exec tool | `system_exec` — subprocess shell, no guards |
| Fallback | `hermes_ask` — full Hermes agent turn |

The API key is **embedded directly** in the config file (not env:VAR),
so the tunnel survives reboots without needing env vars set.

## Hermes Gateway

- Port: `0.0.0.0:8644` (SSE transport)
- Running as systemd or long-lived python process

## Security Layers Bypassed

- Toolset exclusions → removed (empty set)
- Dangerous command guard → auto-approve callback
- Sudo password prompt → auto-provided callback
- Cron deny mode → HERMES_CRON_SESSION=approve
- Non-interactive skip path → interactive context=True

## Remaining Hard Blocks (system_exec bypasses these)

- Hardline: rm -rf /, mkfs, dd to raw device, shutdown, reboot, fork bomb
- Sudo stdin guard: piping passwords to sudo -S
- User deny rules: approvals.deny in config.yaml

## Restart

```bash
# SSH in as root
ssh root@100.93.75.87

# Start tmux session as kubuntux (no API key needed — it's embedded)
sudo -u kubuntux bash -c 'tmux new-session -d -s tunnel-mcp__hermes-tools__9de257be \
  "/home/kubuntux/.local/bin/tunnel-client run --profile-dir \
  /home/kubuntux/.config/tunnel-client --profile hermes-tools \
  >> /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log 2>&1"'
```

## Update the Bridge Code

```bash
# Write new bridge code
scp /path/to/mcp_direct_bridge.py root@100.93.75.87:/mnt/storage/kubuntux-home/.hermes/hermes-agent/mcp_direct_bridge.py

# Kill old tunnel
ssh root@100.93.75.87 "ps aux | grep -E 'tunnel-client|mcp_direct_bridge' | grep -v grep | awk '{print \$2}' | xargs kill -9"

# Restart (see restart command above)
```

## Check Health

```bash
# Tunnel health
curl -s http://127.0.0.1:<port>/healthz
# → "live"
curl -s http://127.0.0.1:<port>/readyz
# → "ready"

# Find the port from the health URL file
cat /home/kubuntux/.local/state/tunnel-client/health/hermes-tools.url
```
