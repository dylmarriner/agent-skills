# Multi-Machine Hermes/OpenClaw Tunnel Setup

Profiles configured on kubuntux at `~/.config/tunnel-client/`.

## hermes-tools

Bridges Hermes MCP servers from 4 machines to ChatGPT via a single tunnel.

**Tunnel**: `tunnel_6a55d54fc5408191a5ed7224e73dd9fb` ("hemes kubuntux", "direct hermes use")
**API key**: Runtime API key from `https://platform.openai.com/settings/organization/api-keys`
**Profile**: `~/.config/tunnel-client/hermes-tools.yaml`
**Health URL file**: `~/.local/state/tunnel-client/health/hermes-tools.url`

### MCP channels

| Channel | Machine | Command |
|---------|---------|---------|
| `main` | kubuntux (100.93.75.87) | `env HERMES_MCP_PREFIX=kubuntux python3 /mnt/storage/kubuntux-home/.hermes/hermes-agent/mcp_direct_bridge.py` |
| `lin` | lin (100.91.55.113) | SSH → same bridge script with `PREFIX=lin` |
| `macuntu` | macuntu (100.75.23.127) | SSH → same bridge script with `PREFIX=macuntu` |
| `rabuntu` | rabuntu (100.68.0.96) | SSH as root → same bridge script with `PREFIX=rabuntu` |

All SSH commands use: `-o StrictHostKeyChecking=no -o BatchMode=yes`

### Common cosmetic log messages (ignore)
- `Plugin 'codegraph' has no register() function`
- `Plugin 'memory_tree' has no register() function`
- `Failed to load plugin 'nexus-memory': No __init__.py` (on any machine)
- `rtk: hermes plugin warning: rtk binary not found in PATH`
- `ragflow: RAGFLOW_API_KEY not set`

## openclaw-tools

Bridges OpenClaw MCP server to ChatGPT.

**Tunnel**: `tunnel_6a5617e3ac6c8191b38a8d923a956740`
**API key**: Same Runtime API key
**Profile**: `~/.config/tunnel-client/openclaw-tools.yaml`
**MCP channel**: `main` — runs via `node --import tsx src/mcp/openclaw-direct-bridge.ts` in the OpenClaw project dir

## Starting

```bash
# hermes-tools (4-machine bridge)
tunnel-client run --profile hermes-tools

# openclaw-tools (single OpenClaw bridge)
tunnel-client run --profile openclaw-tools
```

Read health URL from `~/.local/state/tunnel-client/health/<profile>.url` after start.

## Systemd persistence

Both tunnels are set up as systemd user services for reboot persistence:

| Tunnel | Service | Status |
|--------|---------|--------|
| Hermes | `tunnel-client.service` | Active, enabled |
| OpenClaw | `tunnel-client-openclaw.service` | Active, enabled |

**Hermes** service runs `tunnel-client run --profile hermes-tools` — bridges all 4 machines.
**OpenClaw** service runs `tunnel-client run --profile openclaw-tools` — bridges the OpenClaw Node/TSX bridge.

```bash
# Check both
systemctl --user status tunnel-client.service
systemctl --user status tunnel-client-openclaw.service

# Logs per service
journalctl --user -u tunnel-client.service -n 50 --no-pager
journalctl --user -u tunnel-client-openclaw.service -n 50 --no-pager
```

## Platform URLs

- Tunnels management: `https://platform.openai.com/settings/organization/tunnels`
- Runtime API keys: `https://platform.openai.com/settings/organization/api-keys`
- ChatGPT connectors: `https://chatgpt.com/#settings/Connectors`
