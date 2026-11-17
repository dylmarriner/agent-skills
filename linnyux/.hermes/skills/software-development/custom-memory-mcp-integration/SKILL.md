---
name: custom-memory-mcp-integration
description: Configure and verify the Robbie custom memory MCP server over SSE, including client config updates for Claude, Cline, Gemini/Antigravity, and Windsurf.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# Custom Memory MCP Integration

Use this skill when connecting the Robbie custom memory MCP server to local clients or verifying that the integration is actually live.

## Verified endpoint

- SSE URL: `http://100.68.0.96:3001/sse`
- The host previously exposed Grafana on port 3000, so do not assume 3000 is the MCP port.

## Steps

1. Inspect the server host to identify the real listening port for the MCP container.
2. Probe the live SSE endpoint and confirm `200` with `text/event-stream` headers.
3. Update client configs to point to the verified SSE URL.
4. Re-read the configs and re-probe the endpoint after changes.
5. If the server is containerized, check the host-to-container port mapping before changing client configs.

## Hermes Nexus memory plugin setup on remote hosts

When setting up Nexus memory for Hermes on another machine, configure both surfaces and verify both:

1. Copy/install the `nexus-memory` plugin under `~/.hermes/plugins/nexus-memory`.
2. Ensure `plugins.enabled` in `~/.hermes/config.yaml` is a YAML list, not a JSON/string blob, then include `nexus-memory`.
3. Write plugin env vars to `~/.hermes/.env` because Hermes plugin `requires_env` checks read that file (`NEXUS_URL`, `NEXUS_SECRET`, `NEXUS_AGENT`, plus optional device/source vars).
4. Keep/update the `mcp_servers.nexus-memory` stdio adapter block if the host already uses it; refresh its `env` values too.
5. Verify `hermes plugins list --plain --no-bundled` shows `nexus-memory` enabled.
6. Verify auth mode before assuming no-auth. A live Nexus server that returns `401 Missing Bearer token` still requires the current `NEXUS_SECRET`, even if expected policy says otherwise.
7. Import the plugin's `tools.py` with the env loaded and run `nexus_health({})`; `HTTP 401 Invalid API key` means the integration is wired but the bearer secret is stale, so refresh the secret from the authoritative Nexus server/container or ask the user for the current token.
8. If HTTP MCP `tools/list` works but `tools/call` hangs/timeouts, probe REST endpoints directly. Nexus `/mcp` can self-dispatch to `/v1/...` and hang while `/health`, `/v1/memory/save`, and `/v1/memory/recall` work. In that case use the stdio adapter or patch the Hermes plugin to call REST directly.

See `references/nexus-hermes-remote-setup.md` for the remote-host checklist, failure modes, and validation commands.

## Common config locations

- Claude: `~/.claude.json`
- Cline: `~/.cline/data/settings/cline_mcp_settings.json`
- Gemini/Antigravity: `~/.gemini/antigravity/mcp_config.json`
- Windsurf: `~/.codeium/windsurf/mcp_config.json`

## Why it works

It prevents copying an assumed port/path into multiple agents before confirming the live transport endpoint.
