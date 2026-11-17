# Tailscale MCP — worked example

A concrete instance of the onboarding workflow: several competing servers for one
upstream API, a tier/toolset system to narrow, and non-mutating validation subcommands.

## The three candidates

All three wrap the same Tailscale v2 control-plane API. Surveyed once so a future
session does not have to:

| Repo | Dist | Surface | Notes |
|---|---|---|---|
| `tailscale-mcp/tailscale-mcp` | npm `@tailscale-mcp/tailscale-mcp`, `cargo install tailscale-mcp`, `ghcr.io/tailscale-mcp/tailscale-mcp`, Homebrew tap, platform `.mcpb` | ~186 tools | Rust. Prebuilt static binaries + `SHA256SUMS` for x86_64/arm64 Linux, macOS, Windows. The npm wrapper downloads the release binary and refuses to run it unless the release's own checksum list vouches for it. Drives both the local `tailscale` CLI and the tailnet REST API; either surface being absent is non-fatal. |
| `YawLabs/tailscale-mcp` | npm `@yawlabs/tailscale-mcp` | ~89 admin-API tools + 4 CLI + 4 resources | MIT. Full v2 API coverage. |
| `HexSleeves/tailscale-mcp` | npm `@hexsleeves/tailscale-mcp-server`, Docker Hub, GHCR | ~40 tools | Read-only by default, localhost binding, risk-gated via `TAILSCALE_ALLOWED_TOOL_RISK` (`read` / `write` / `admin`). |

Chosen: the first — most complete, and a static binary with no runtime to install beats
an npm wrapper. The other two are the same API with less surface; skip them and say so.

## Environment variables

| Var | Effect |
|---|---|
| `TAILSCALE_API_KEY` | `tskey-api-…` bearer token. Belongs to a person, carries their whole account, expires. |
| `TAILSCALE_OAUTH_CLIENT_ID` + `TAILSCALE_OAUTH_CLIENT_SECRET` | Tailnet-scoped, non-expiring, mints hour-long tokens. Preferred for anything kept. |
| `TAILSCALE_TAILNET` | Defaults to `-`, the tailnet the credential belongs to. |
| `TAILSCALE_MCP_ALLOW_WRITE` | Offer config-changing tools. Off by default — the server is read-only without it. |
| `TAILSCALE_MCP_ALLOW_DESTRUCTIVE` | Offer remove/expose tools. Implies write. **Required for `tailnet_policy_set`** — policy replacement is classed destructive. |
| `TAILSCALE_MCP_PRESET` | `minimal` / `core` (default) / `full`. |
| `TAILSCALE_MCP_TOOLSETS` | Bare list replaces the preset's selection; a list where every entry starts `+`/`-` adjusts it. |
| `TAILSCALE_MCP_NO_LOCAL` / `_NO_TAILNET` | Suppress the CLI-driven or control-plane-driven tools respectively. |

## Toolsets

`local-status`, `local-prefs`, `local-serve`, `local-files`, `local-lock`, `local-debug`,
`local-passthrough`, `tailnet-devices`, `tailnet-invites`, `tailnet-logging`,
`tailnet-dns`, `tailnet-keys`, `tailnet-policy`, `tailnet-posture`, `tailnet-users`,
`tailnet-settings`, `tailnet-webhooks`, `tailnet-services`, `tailnet-oauth-apps`,
`tailnet-org`.

`local-debug` is in no preset and must be named explicitly.

Sizing: `tailnet-policy` is 4 tools (`tailnet_policy_get`, `_preview`, `_set`,
`_validate`), `tailnet-devices` is 15. Those two together are **19 of 186** — the
recommended starting surface for policy work.

## Non-serving subcommands

```bash
tailscale-mcp diagnose [--json]        # tailscale binary, credential, control plane
tailscale-mcp tools                    # what this preset + tier would offer
tailscale-mcp policy check <file>      # ask the control plane to parse a policy; changes nothing
tailscale-mcp policy deploy <file>     # write it, guarded by the version read immediately before
```

`policy check` printing nothing means it passed — the same empty-body-means-valid trap
as the REST validate endpoint.

## Install used

```bash
printf 'y\n' | hermes mcp add tailscale \
  --command npx \
  --connect-timeout 180 \
  --env TAILSCALE_API_KEY='tskey-api-…' \
        TAILSCALE_MCP_ALLOW_WRITE=true \
        TAILSCALE_MCP_ALLOW_DESTRUCTIVE=true \
        TAILSCALE_MCP_TOOLSETS=tailnet-policy,tailnet-devices \
  --args -y @tailscale-mcp/tailscale-mcp
```

Omitting `TAILSCALE_MCP_ALLOW_DESTRUCTIVE` removes `tailnet_policy_set` from the
discovered list entirely, so the first attempt reports 15 tools and no way to write a
policy. That reads as a bug and is not one.

## When not to install it at all

A single ACL or policy edit is one authenticated `curl` against
`https://api.tailscale.com/api/v2/tailnet/-/acl`. No install, no config, no credential
on disk, no reload. Install the MCP only when tailnet access should persist across
sessions — and prefer the OAuth client env vars over the API key when it does, because
the key ends up in `~/.hermes/config.yaml` in plaintext.
