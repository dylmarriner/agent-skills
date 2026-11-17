# Cross-Machine Deployment

Setup guide for deploying an MCP server and clients across multiple machines
on the same Tailscale network.

## Architecture

- **Server machine**: Runs the MCP server (systemd, port 8765)
- **Client machines**: Run Hermes, OpenClaw, Paperclip, Windsurf, Antigravity clients
  pointing to the server's Tailscale IP

## Deploying the MCP Server

```bash
# SSH to the server machine
ssh user@<server-tailscale-ip>

# Clone the repo
git clone https://github.com/<user>/<repo>.git
cd <repo>

# Set up Python
python3 -m venv .venv
.venv/bin/pip install mcp numpy ulid-py zstandard cryptography PyJWT

# Create systemd user service
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/synapse-mcp.service << 'SERVICEEOF'
[Unit]
Description=Synapse Memory — MCP Server
After=network-online.target tailscaled.service
Wants=tailscaled.service

[Service]
Type=simple
WorkingDirectory=/home/<user>/<repo>
Environment=SYNAPSE_HOST=0.0.0.0
Environment=SYNAPSE_PORT=8765
Environment=SYNAPSE_EMBED_DIM=64
Environment=SYNAPSE_TAILSCALE_DETECT=1
Environment=SYNAPSE_TENANT_LIMIT=0
Environment=SYNAPSE_DEFAULT_TENANT=default
ExecStart=/home/<user>/<repo>/.venv/bin/python /home/<user>/<repo>/server.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
SERVICEEOF

# Enable and start
systemctl --user daemon-reload
systemctl --user enable --now synapse-mcp

# Verify
curl -s -D - http://localhost:8765/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"verify","version":"1"}}}'

# Then test tools/call for health
```

## Deploying Clients (per machine)

For each client machine on the Tailnet:

### 1. Get the server's Tailscale IP

```bash
# On the server:
echo $(tailscale ip -4)
# → 100.x.y.z
```

### 2. Install Hermes plugin

```bash
mkdir -p ~/.hermes/plugins/synapse-memory
cp ~/<repo>/plugins/hermes-synapse/* ~/.hermes/plugins/synapse-memory/
```

### 3. Configure Hermes MCP

Edit `~/.hermes/config.yaml` and add:

```yaml
mcp_servers:
  synapse:
    url: "http://<SERVER_TS_IP>:8765/mcp"
    timeout: 120
    connect_timeout: 30
```

Run `/reload-mcp` in Hermes to pick up the new server.

### 4. Configure Windsurf

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "synapse": {
      "url": "http://<SERVER_TS_IP>:8765/mcp",
      "timeout": 120
    }
  }
}
```

### 5. Configure Antigravity

Edit `~/.gemini/antigravity/mcp_config.json`:

```json
{
  "mcpServers": {
    "synapse": {
      "url": "http://<SERVER_TS_IP>:8765/mcp",
      "timeout": 120
    }
  }
}
```

### 6. Install OpenClaw plugin

```bash
cp -r ~/<repo>/plugins/openclaw-synapse ~/openclaw/extensions/synapse
```

Then restart OpenClaw.

## Cross-Machine E2E Verification

```bash
# From any machine, using the Python SDK:
python3 -c "
from synapse_sdk import SynapseClient
c = SynapseClient(server_url='http://<SERVER_TS_IP>:8765/mcp')

# Store a memory from this machine
r = c.store(kind='semantic', content='Cross-machine test from $(hostname)', tags=['e2e'])
mid = r.get('memory_id')
print(f'Stored: {mid}')

# Retrieve it (should work from any machine pointing to same server)
r = c.retrieve('Cross-machine test')
print(f'Found: {r.get(\"count\")} results')

# Verify content matches
for mem in r.get('results', []):
    print(f'  {mem[\"content_text\"][:60]}')
"
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| MCP call returns "Authentication required" | Server is in multi-tenant mode, no API key provided | Set `TENANT_LIMIT=0` or pass API key |
| MCP call returns "Tenant not found or suspended" | Default tenant doesn't exist in DB | Delete DB and restart, or register a tenant |
| Dashboard shows 0 memories but health shows count | Dashboard's MCP session is scoped to wrong tenant | Restart dashboard to get fresh server session |
| Connection timeout | Tailscale not running or wrong IP | Verify `tailscale status` on both machines |
| `sync_events` returns 0 | Events from own device are filtered by `device_id!=` param | That's by design — sync shows OTHER devices' events |
