# Linode MCP Server (@takashito/linode-mcp-server)

Package: `@takashito/linode-mcp-server` v0.4.0
Global binary: `linode-mcp-server` (at `~/.npm-global/bin/linode-mcp-server`)

## Environment Variable

```
LINODE_API_TOKEN  ← correct (NOT LINODE_TOKEN)
```

The server errors with: `"Linode API token is required for stdio transport"` if you use the wrong variable name.

## Setup

### Install globally (cached, faster startup)
```bash
npm install -g @takashito/linode-mcp-server
```

### Wrapper script for Hermes
```bash
cat > ~/.hermes/scripts/linode-mcp.sh << 'EOF'
#!/bin/bash
export LINODE_API_TOKEN="<your-token>"
exec /home/macuntu/.npm-global/bin/linode-mcp-server "$@"
EOF
chmod +x ~/.hermes/scripts/linode-mcp.sh
```

Register with Hermes:
```bash
hermes config set mcp_servers.linode.command /home/macuntu/.hermes/scripts/linode-mcp.sh
hermes config set mcp_servers.linode.enabled true
```

### Discovering available categories
```bash
LINODE_API_TOKEN="<token>" linode-mcp-server --list-categories
```
Returns: instances, volumes, networking, nodebalancers, regions, placement, vpcs, objectStorage, domains, databases, kubernetes, images, stackScripts, tags, support, longview, profile, account, monitor

### Tools count
416 tools across 19 categories.

### Verify connection
```bash
hermes mcp test linode
```

## CLI Options (from commander)
- `--token, -t <token>` — Linode API token override
- `--categories <categories>` — comma-separated tool categories to enable
- `--list-categories` — list available categories and exit
- `--transport <type>` — stdio (default) or http
- `--port <port>` — HTTP server port (default 8080)
- `--host <host>` — HTTP server host (default 127.0.0.1)
- `--endpoint <endpoint>` — HTTP endpoint path (default /mcp)
