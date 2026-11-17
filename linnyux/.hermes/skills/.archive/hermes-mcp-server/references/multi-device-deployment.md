# Multi-Device MCP Bridge Deployment

## Architecture

One tunnel-client on **kubuntux** aggregates 4 machines via MCP commands:

```
kubuntux (main channel)
  ├── local bridge (venv python)
  ├── lin via SSH → lin@100.91.55.113
  ├── macuntu via SSH → macuntu@100.75.23.127
  └── rabuntu via SSH → root@100.68.0.96
```

Each machine runs `mcp_direct_bridge.py` with its own `HERMES_MCP_PREFIX`
env var so all tool names are prefixed with the device name.

## Device Identities

| Channel | Prefix | IP | User | Bridge path |
|---------|--------|-----|------|-------------|
| main | kubuntux | 100.93.75.87 | kubuntux | `/mnt/storage/kubuntux-home/.hermes/hermes-agent/venv/bin/python3 /mnt/storage/kubuntux-home/.hermes/hermes-agent/mcp_direct_bridge.py` |
| lin | lin | 100.91.55.113 | lin | `/home/lin/.hermes/hermes-agent/venv/bin/python3 /home/lin/.hermes/hermes-agent/mcp_direct_bridge.py` |
| macuntu | macuntu | 100.75.23.127 | macuntu | `/home/macuntu/.hermes/hermes-agent/venv/bin/python3 /home/macuntu/.hermes/hermes-agent/mcp_direct_bridge.py` |
| rabuntu | rabuntu | 100.68.0.96 | root | `python3 /root/.hermes/hermes-agent/mcp_direct_bridge.py` |

## SSH Setup

All 3 remote machines (lin, macuntu, rabuntu) have SSH key-based auth
from kubuntux's user account. The kubuntux user's SSH keys are at:
`/home/kubuntux/.ssh/id_ed25519`

Test each connection:
```bash
sudo -u kubuntux ssh -o BatchMode=yes <user>@<ip> 'echo ok'
```

## Tunnel Config

File: `/home/kubuntux/.config/tunnel-client/hermes-tools.yaml`

Key structure:
- One `channel: "main"` entry (required — tunnel-client rejects configs without it)
- One entry per additional device with unique channel names
- SSH commands wrap the remote bridge in quotes: `ssh host "env HERMES_MCP_PREFIX=<name> python3 ..."`
- API key embedded directly in config (survives reboot)

## Starting

```bash
# Clean log and start fresh
rm -f /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log

# Start as kubuntux user in tmux
sudo -u kubuntux bash -c 'tmux new-session -d -s tunnel-mcp__hermes-tools__9de257be \
  "/home/kubuntux/.local/bin/tunnel-client run --profile-dir \
  /home/kubuntux/.config/tunnel-client --profile hermes-tools \
  >> /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log 2>&1"'
```

## Verifying

All 4 channels are running:
```bash
# Process count (should be 7+)
ps aux | grep -E 'tunnel-client|mcp_direct' | grep -v grep | wc -l
# Expected: 1 tunnel-client + 4 bridges + SSH wrappers

# Health
curl -s $(cat /home/kubuntux/.local/state/tunnel-client/health/hermes-tools.url)/healthz
# → "live"
curl -s $(cat /home/kubuntux/.local/state/tunnel-client/health/hermes-tools.url)/readyz
# → "ready"
```

Check for failures in the log:
```bash
grep -E 'ERROR|WARN.*exit' /home/kubuntux/.local/state/tunnel-client/logs/hermes-tools.log
```
Should show zero lines. If any channel fails, the WHOLE tunnel shuts down.

## Hermes Version Compatibility

| Machine | Hermes version | Notes |
|---------|---------------|-------|
| kubuntux | 0.18.2 | Editable install, mcp package in venv |
| lin | 0.18.2 | Editable install, mcp package in venv |
| macuntu | 0.17.0 | mcp 1.28.1 installed in venv |
| rabuntu | 0.17.0 | System Python, mcp installed via pip --break-system-packages |

Rabuntu (Hermes 0.17) lacks `set_hermes_interactive_context` — handle
via try/except in the bridge. The mcp package was installed on rabuntu
with `pip3 install mcp --break-system-packages`.
