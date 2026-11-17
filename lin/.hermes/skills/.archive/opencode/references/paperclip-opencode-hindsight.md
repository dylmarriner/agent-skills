# Paperclip OpenCode Adapter + Hindsight MCP

When Paperclip runs OpenCode through its `opencode_local` adapter, it creates a temporary copy of `~/.config/opencode/` with an injected `permission.external_directory = "allow"` config. The adapter now also injects a `hindsight-memory` MCP server when `HINDSIGHT_API_URL` is set in the process environment.

## How it works

1. Paperclip copies `~/.config/opencode/` to a temp dir (`/tmp/paperclip-opencode-config-XXXXXX/`)
2. Reads the copied `opencode.json`
3. Injects `permission.external_directory = "allow"` (existing behavior)
4. Reads `HINDSIGHT_API_URL` and `HINDSIGHT_API_KEY` from env
5. If `HINDSIGHT_API_URL` is set and no `hindsight-memory` MCP entry already exists in the copied config, injects one:
   ```json
   {
     "hindsight-memory": {
       "type": "remote",
       "url": "{HINDSIGHT_API_URL}/mcp",
       "enabled": true,
       "headers": {
         "Authorization": "Bearer {HINDSIGHT_API_KEY}"
       }
     }
   }
   ```
6. The user's own config `hindsight-memory` entry takes precedence — the adapter only injects if not already user-configured

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HINDSIGHT_API_URL` | Yes (to activate) | Base URL of Hindsight instance, e.g. `https://api.hindsight.vectorize.io` |
| `HINDSIGHT_API_KEY` | No | API key for authenticated access, passed as Bearer token |

Set these in the shell where Paperclip runs, or in the Paperclip agent's `env` config field.

## Code Location

The injection logic is in:
`packages/adapters/opencode-local/src/server/runtime-config.ts`

Function `buildHindsightMcpEntry()` reads env vars and returns an MCP config entry or null.

## Official Paperclip Plugin

In addition to the adapter-level MCP injection, there's an official Hindsight Paperclip plugin on npm:

`@vectorize-io/hindsight-paperclip` v0.2.1

Installed at `~/.paperclip/plugins/node_modules/@vectorize-io/hindsight-paperclip/`.

This plugin hooks into Paperclip's event system to:
- Auto-recall context on `agent.run.started` (with issue title/description as query)
- Auto-retain agent output on `agent.run.finished`
- Register `hindsight_recall` and `hindsight_retain` agent tools for mid-run use

The plugin uses the Hindsight REST API (not MCP) — it calls:
- `POST /v1/default/banks/{bankId}/memories/recall`
- `POST /v1/default/banks/{bankId}/memories`

Bank format: `paperclip::{companyId}::{agentId}` (configurable bank granularity).
