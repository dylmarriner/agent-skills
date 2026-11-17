# Devin CLI Reference

## Installation Paths

| Source | Path | Version |
|--------|------|---------|
| Bundled in Windsurf | `/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin` | `2026.5.26-0` |
| Bundled in Devin Desktop | `/home/lin/Downloads/Devin/resources/app/extensions/windsurf/devin/bin/devin` | `2026.5.26-2` |
| Symlinked in PATH | `~/.local/bin/devin` (→ Windsurf version) | — |

## Credentials Format

**File:** `~/.local/share/devin/credentials.toml`

```toml
windsurf_api_key = "<api-key>"
devin_api_url = "https://api.devin.ai"
devin_webapp_host = "app.devin.ai"
api_server_url = "https://api.devin.ai"
```

The credential field is `windsurf_api_key`, not `api_key`. Using `api_key` results in "missing field `windsurf_api_key`" parse error.

## Auth Flow

### Standalone CLI Auth
```
devin auth login --force-manual-token-flow
# Prints URL → user browses → user pastes code back
```

The code is a **PKCE authorization code**, not a persistent API key. It must be exchanged via the CLI's local callback server. You cannot write the code directly as `windsurf_api_key` — it will fail with "invalid api key".

### Windsurf-ACP Auth
When Windsurf spawns Devin via `devin acp`, it passes the API key through the ACP `authenticate` RPC with `method_id: "windsurf-api-key"`. The key is stored in Windsurf's internal state, not the credentials file.

## ACP Mode

Devin supports the Agent Client Protocol (ACP) over stdio:

```bash
devin acp  # starts ACP server, waits for JSON-RPC on stdin
```

Initialize with auth:
1. Send `initialize` → get `authMethods` including `windsurf-api-key`
2. Send `authenticate` with `method_id: "windsurf-api-key"` and `api_key` in meta
3. Proceed with session creation

## Skills Directory

Installed skills at `~/.config/devin/skills/` — synced from Windsurf.

## Known Issues

- `devin -p "prompt"` hits the API server for inference. If the API URL is wrong, returns 404.
- The standalone `devin auth login` flow opens a browser via system default. In headless/SSH sessions, use `--force-manual-token-flow` and paste the URL.
