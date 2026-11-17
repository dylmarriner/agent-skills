---
name: mcp-sse-endpoint-troubleshooting
description: Diagnose and verify MCP servers exposed over SSE, including host/port mismatches, reverse-proxy issues, and client config updates.
metadata:
  category: mcp
---

# MCP SSE Endpoint Troubleshooting

Use this skill when connecting an MCP server over SSE and you need to verify that clients can actually reach the live endpoint, not just that config files exist.

## When to use
- An MCP client is configured but tools do not appear
- A server URL returns 404 or another unexpected response
- The server works in code/docs but not from the client machine
- You suspect the wrong host port, reverse proxy, or container mapping
- You need to update multiple agent configs consistently

## Steps
1. Read the server docs and source to confirm the expected transport and paths.
   - Verify the SSE endpoint path, usually `/sse`.
   - Verify whether a separate message endpoint exists and whether it is session-specific.

2. Inspect every configured client file.
   - Record the exact URL, transport type, and any auth/header requirements.
   - Make sure every client points to the same intended endpoint.

3. Verify network reachability before assuming the app is wrong.
   - Check that the host and port are reachable.
   - If possible, SSH into the host and inspect running services.

4. Identify the actual process bound to the target port.
   - Use `ss -ltnp`, `lsof`, or `docker ps` to map host port to service.
   - Do not assume the requested port is the one actually exposed.

5. Probe the real SSE endpoint directly.
   - A healthy MCP SSE endpoint should return HTTP 200 and `text/event-stream` headers.
   - A 404 usually means the wrong host, port, or path.
   - A 404 on `/messages` can be normal before a session is established.

6. Correct the client configs to the verified endpoint.
   - Update all relevant agent configs together so they stay consistent.
   - Prefer one canonical URL across Claude, Cline, Gemini/Antigravity, Windsurf, and other clients.

7. Re-test after the fix.
   - Re-probe the SSE endpoint.
   - If possible, confirm a real MCP handshake or tool listing from at least one client path.

## Pitfalls
- The root URL returning HTML does not mean the MCP endpoint is working.
- Port 3000 is often occupied by another service; always confirm the binding.
- `/messages` may return 404 until the SSE handshake creates a session-specific channel.
- A config file can be correct while the deployed service is still pointed at a different port.
- **Auth tokens go stale.** A token in a client config may have been rotated. Cross-check against the actual service `.env` or secret store, not just other config files.
- **Not all MCP servers use `/sse`.** Some serve JSON-RPC directly at the base path (e.g. `/mcp`). A curl GET returning 405 (Method Not Allowed) is expected — use POST instead.
- **Same config format ≠ same config path.** Codex CLI (v0.142+) uses `codex mcp add` (config in `config.toml`), Cline uses `~/.cline/data/settings/cline_mcp_settings.json`, other tools may use `~/.codex/mcp_config.json`. They can diverge. Check each tool's own config mechanism.
- **Multi-machine configs drift.** An MCP server config on one machine (e.g. kubuntux) may be stale or outdated on another (e.g. macuntu). Always `ssh` and check the remote files.
- **Codex CLI v0.142.x: streamable HTTP + bearer token permission bug.** When Codex connects to a remote MCP server via `--bearer-token-env-var` or `http_headers`, tool calls may fail with `"pretooluse hook returned unsupported permission decision: allow"`. Codex's PreToolUse hook system doesn't recognise `"allow"` as a valid permission decision. **Workaround:** use a local stdio MCP proxy instead — a script that reads JSON-RPC from stdin, forwards via HTTP POST to the remote server, and writes responses to stdout. Codex launches it as a child process (stdio transport), which avoids the bug entirely.
- **Plugin PreToolUse hooks returning `"allow"` break Codex CLI.** The `agentforce-adlc` plugin's `guardrails.py` returns `"permissionDecision": "allow"` for non-blocking Bash commands. This format works in Claude Code but not in Codex (expects `"bypass"`, `"reject"`, or `"ask"`). Every safe Bash command triggers the error. **Fix:** remove the `PreToolUse` block from the plugin's `hooks/hooks.json` (cache, re-downloaded on update, non-destructive).
- **Codex CLI ignores raw `mcp_config.json` files.** Unlike Claude Code or Cline, Codex v0.142+ does NOT read `~/.codex/mcp_config.json`. Config lives in `~/.codex/config.toml` under `[mcp_servers.*]`, managed via `codex mcp add`. Writing a raw JSON file silently does nothing.

## Common Client Config Paths

### Codex CLI (v0.142+)

**Does NOT use `~/.codex/mcp_config.json`.** Use the `codex mcp add` CLI command. Config is stored in `~/.codex/config.toml` under `[mcp_servers.*]`.

```bash
# Add an SSE/StreamableHTTP server (bearer token read from env var at runtime)
codex mcp add <name> --url <url> --bearer-token-env-var <ENV_VAR>

# Verify
codex mcp list          # shows all configured servers
codex mcp get <name>    # show single server details
codex doctor | grep mcp # health check
```

Auth uses `--bearer-token-env-var <VAR>` — the token is read from an **environment variable** at runtime, not hardcoded in config. The env var must be set in `~/.bashrc` or equivalent for interactive sessions.

**Pitfall:** Writing a raw `~/.codex/mcp_config.json` file will NOT make MCP servers appear in Codex CLI. The file is silently ignored. Always use `codex mcp add`.

### Cline CLI
`~/.cline/data/settings/cline_mcp_settings.json` — same JSON structure as Codex CLI.

```json
{
  "mcpServers": {
    "my-server": {
      "type": "sse",
      "url": "http://host:port/path",
      "headers": {
        "Authorization": "Bearer <token>"
      },
      "enabled": true,
      "description": "..."
    }
  }
}
```

### Agentmemory MCP (legacy)
`~/.codex/mcp_config.json` may have an `@agentmemory/mcp` npx entry pointing to a separate port. Replace with direct SSE to the main MCP server when `@agentmemory/mcp` is no longer active.

## Verifying With JSON-RPC (not just SSE stream)

Many MCP servers respond to standard POST requests. This is faster and more reliable than waiting for SSE stream headers:

```bash
TOKEN="<actual-token>"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://host:port/path \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

Expect a response like:
```json
{"jsonrpc": "2.0", "id": 1, "result": {"tools": [...]}}
```

If you get `"Invalid API key"` the token is wrong. If you get a 404/405, the path is wrong.

## Multi-Machine Config Sync

When an MCP server should be accessible from multiple machines:

```bash
# Check remote config
ssh remote-machine "cat ~/.codex/config.toml"      # Codex CLI (v0.142+)
ssh remote-machine "cat ~/.cline/data/settings/cline_mcp_settings.json"  # Cline
ssh remote-machine "cat ~/.codex/mcp_config.json"  # Other tools (Claude Code)

# Sync a Codex CLI server
ssh remote-machine "export PATH=\$HOME/.local/bin:\$PATH; export MY_SECRET=...; codex mcp add nexus --url <url> --bearer-token-env-var MY_SECRET"

# Sync Cline config
ssh remote-machine "cat > ~/.cline/data/settings/cline_mcp_settings.json << 'EOF'
{ ... same config ... }
EOF"
```

Always test the endpoint from the remote machine too — network routing (Tailscale IPs, VPNs) may differ.

## Verification checklist
- [ ] Server path confirmed (e.g. `/mcp` not `/mcp/sse`)
- [ ] Auth token verified against live source (not just other configs)
- [ ] Client config files use the same verified endpoint + token
- [ ] Host/port is reachable from EACH client machine
- [ ] JSON-RPC POST `tools/list` returns tool results, not error
- [ ] All agent configs updated consistently (Codex, Cline, Claude Code, etc.)
- [ ] Multi-machine configs verified via SSH
- [ ] At least one live client handshake verified

## Reference Files

For concrete, verified examples and recovery recipes, see:

- **`references/nexus-mcp-connection.md`** — covers the verified URL, auth token source, both Codex CLI and Cline config paths, common failures, multi-machine sync commands, and the legacy `@agentmemory/mcp` replacement history.
- **`references/airis-gateway-install.md`** — AIRIS MCP Gateway quick-install flow, Claude Code registration, config-path repair, and the `mcp-config.json` file-vs-directory pitfall.

## Last validated
2026-07-01