# Integrating MCP Servers with Windsurf IDE

Windsurf (Codeium's AI IDE) supports MCP servers natively via `--add-mcp` CLI flag. This lets Windsurf's Cascade agent use any MCP server's tools.

## Adding an MCP Server to Windsurf

```bash
# Basic: stdio transport
windsurf --add-mcp '{"name":"my-server","command":"python","args":["-m","my_mcp_server","--port","8082"]}'

# WebSocket/HTTP transport
windsurf --add-mcp '{"name":"my-server","url":"http://localhost:8082/mcp"}'
```

## Verification

After adding, restart Windsurf. Cascade will automatically discover and list the server's tools. You can verify in Windsurf's MCP server panel (settings → extensions → MCP).

## Practical Example: AIOS → Windsurf Bridge

```bash
# 1. Start the AIOS core MCP server
aios start --mcp-port 8082

# 2. Connect Windsurf Cascade to it
windsurf --add-mcp '{"name":"aios-core","command":"python","args":["-m","aios.mcp.host","--port","8082"]}'

# 3. Open the project
windsurf /path/to/project --reuse-window
```

Now Cascade can call AIOS tools (device control, screen capture, memory, workflows) directly from the chat panel.

## Multiple Servers

Add multiple servers for different capabilities:
```bash
windsurf --add-mcp '{"name":"aios-core","command":"python","args":["-m","aios.mcp.host"]}'
windsurf --add-mcp '{"name":"aios-android","url":"http://android-device:8082/mcp"}'
```

## Auto-reload

Changes to MCP server code require server restart. Windsurf does NOT auto-detect MCP server changes — restart the server process then reload Windsurf.

## Pitfalls

- `--add-mcp` adds to the user profile, not per-workspace. To remove, use Windsurf's MCP settings UI.
- The server MUST be running BEFORE Windsurf starts, or Cascade won't see the tools.
- If the MCP server exits/crashes, Cascade silently loses the tools until Windsurf is restarted.
- Use `--reuse-window` to avoid opening a new window each time.
- For development, run the MCP server in the foreground in a separate terminal.
- Windsurf 1.110+ required (earlier versions lack MCP support).
