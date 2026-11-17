# MCP Server Integration Patterns

Patterns for connecting third-party MCP servers to Hermes Agent, covering
discovery, configuration, and known integration quirks.

## Finding the MCP Server Binary

Many MCP servers ship as VS Code/Cursor/Windsurf extensions. The binary is
bundled inside the extension and can be used directly as a `--command` MCP
server.

### Discovery Pattern

1. Install the extension in Windsurf or Cursor via CLI:
   ```bash
   windsurf --install-extension <publisher.extension>
   ```

2. Find the installed extension path:
   ```bash
   ls ~/.windsurf/extensions/<publisher>.<name>*/
   ```

3. Look for the MCP server entrypoint — typically `dist/mcp-server.js`,
   `dist/server.js`, or referenced in `.mcp.json`:
   ```bash
   cat ~/.windsurf/extensions/<publisher>.<name>*/.mcp.json
   ```

4. Check what tools it exposes:
   ```bash
   grep -oP 'mcp_[a-z]+_\w+' dist/mcp-server.js | sort -u
   ```

### Add to Hermes

Via `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  <name>:
    command: node
    args:
      - /path/to/extension/dist/mcp-server.js
    enabled: true
```

Or via CLI:
```bash
echo 'y' | hermes mcp add <name> --command node --args /path/to/mcp-server.js
```

## IDE-Coupled MCP Servers

Some MCP servers (like **BrainSync**) are tightly coupled to their IDE
extension. They require the IDE to be running with a project open to function.

### How to Identify

Signs of an IDE-coupled MCP server:
- The server logs "waiting for VS Code to open a project" or "offline mode"
- The server has no `--help` or `--version` flags
- The extension's `package.json` lists `activationEvents: onStartupFinished`
- The `.mcp.json` includes IDE-absolute paths (e.g. `C:\\Users\\...`)

### Known IDE-Coupled Servers

| Server | Command | IDE Required | Tool(s) |
|--------|---------|-------------|---------|
| BrainSync | `node .../dist/mcp-server.js` | Windsurf/Cursor/VS Code | `mcp_brainsync_shadow_run` |

### Workaround

The MCP server will register and connect, but tools will return errors or
empty results unless the IDE is open with a project. Accept this limitation
— the server is intentionally designed as an IDE companion.

## Testing an MCP Server

Quick smoke test via stdin/stdout:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  | timeout 5 node /path/to/mcp-server.js 2>/dev/null
```

## Verification

After configuring:
```bash
hermes mcp list              # should show the server as enabled
hermes mcp test <name>       # test connection
```

Then start a new session (`/reset`) and check that the tools are available
via `/tools` or `hermes tools list`.
