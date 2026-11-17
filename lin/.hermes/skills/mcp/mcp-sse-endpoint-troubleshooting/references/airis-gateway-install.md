# AIRIS MCP Gateway + SuperClaude install notes

Session-verified recovery and install notes for the AIRIS MCP Gateway and SuperClaude in Claude Code.

## Verified install flow

1. Install SuperClaude via pipx:
   - `pipx install superclaude`
   - `superclaude install`
   - `superclaude doctor`

2. Inspect AIRIS gateway docs:
   - repo: `https://github.com/agiletec-inc/airis-mcp-gateway`
   - quick install path: `scripts/quick-install.sh`
   - source install path: `docker compose up -d`

3. Run quick install with optional API keys set in the shell:
   - `TAVILY_API_KEY`
   - `MAGIC_API_KEY` (21st.dev)

4. Register the gateway with Claude Code.
   - The installer adds an SSE server named `airis-mcp-gateway` to `~/.claude.json`.
   - The effective endpoint is `http://localhost:9400/sse`.

5. Verify with:
   - `claude mcp list`
   - `superclaude doctor`
   - `docker ps`
   - `curl http://localhost:9400/health`

## Important pitfall: config path collision

The AIRIS quick install expects the config file path to be a file.
If `/home/<user>/.local/share/airis-mcp-gateway/mcp-config.json` already exists as a directory, the installer fails when it tries to mount it as `/app/mcp-config.json`.

Recovery:

```bash
rm -rf /home/<user>/.local/share/airis-mcp-gateway/mcp-config.json
cp /tmp/airis-mcp-gateway/mcp-config.json.example /home/<user>/.local/share/airis-mcp-gateway/mcp-config.json
```

Then rerun the quick install.

## Verified behavior

- `airis-mcp-gateway` registers in Claude Code successfully.
- The API container came up healthy on `localhost:9400`.
- The gateway proxy container became healthy on `9390`, but the public health check from the host did not always answer immediately during startup.
- `claude mcp list` shows both `airis-gateway` and `airis-mcp-gateway` entries when registration succeeds.

## CocoIndex note

For semantic code search on CocoIndex repos, the project docs recommend the `cocoindex-code` skill and the `ccc` CLI rather than registering a separate MCP server.
