# Cloudflare remote MCP (mcp.cloudflare.com)

## Which surface to configure

| Endpoint | Auth | Tools | Notes |
|---|---|---|---|
| `https://mcp.cloudflare.com/mcp?codemode=false` | OAuth or bearer | ~3,500 (real JSON Schema each) | Full API. **Use this.** Hermes' `tool_search` already defers the surface, so provider-side Code Mode would stack two discovery layers. |
| `https://mcp.cloudflare.com/mcp` | same | 2 (`search()`, `execute()`) | Provider Code Mode; only if the host has no tool-search of its own. |
| `https://docs.mcp.cloudflare.com/mcp` | none | few | Public docs search, no auth. |
| `observability|browser|radar|logs|ai-gateway|auditlogs|dns-analytics|graphql|dex|containers|builds|casb.mcp.cloudflare.com/mcp` | OAuth | per-product | Product-specific; each has its own AS/DCR. |

Nous catalog entry: `hermes mcp install cloudflare` (writes url + `auth: oauth` + a 34-pattern
`tools.exclude` list that drops enterprise/org-fleet/radar families: 3,541 raw → 1,976 registered).

## OAuth (interactive host)

The built-in flow uses CIMD, not DCR: `client_id=https://nousresearch.github.io/hermes-agent/docs/oauth/client-metadata.json`,
whose registered redirect URIs are **only** `http://127.0.0.1:{27890..27894}/callback`. A
`oauth.redirect_port` outside that range is rejected by Cloudflare; pick from the registered set.

**Known bug:** the built-in flow prints the authorize URL, then on any retry re-binds a port its own
reservation still holds → `OAuthNonInteractiveError: OAuth callback port <N> is already in use`
(`[Errno 98]`), park, and the tools never register. It reproduces even on a brand-new port, so it is
not a stale socket. Workaround: run the flow by hand with a listener that outlives the CLI's timeout
and persist tokens through Hermes' own storage (`tools.mcp_oauth.HermesTokenStorage.set_tokens` /
`set_client_info` / `bind_issuer`) so the schema is exact. A working implementation lives at
`~/.hermes/scripts/mcp_oauth_handoff.py` (own PKCE + `/callback` server + token exchange + smoke test).

## API-token (headless) mode

```yaml
mcp_servers:
  cloudflare:
    url: "https://mcp.cloudflare.com/mcp?codemode=false"
    headers:
      Authorization: "Bearer ${CLOUDFLARE_API_TOKEN}"
```

`${VAR}` is interpolated from the process environment (`.env`); the literal token never belongs in
`config.yaml`. Drop `auth: oauth` / `oauth.redirect_port` when switching or Hermes keeps retrying the
browser flow.

Token requirements — both of these silently park a token that looks valid elsewhere:

- **No client-IP filter.** A filtered token returns `9109: Cannot use the access token from location: <ip>`.
- **`user:read` or `account:read`.** Without it the MCP returns `403 insufficient_scope: Token lacks required user:read or account:read scope`.

Verify in this order: `POST /accounts/{id}/tokens/verify` → `POST <mcp url>` `initialize` (expect 200 +
`serverInfo.name == "cloudflare-api"`) → `tools/list` → one real `tools/call`.

## Rotating a leaked token via the API

Two Cloudflare constraints bite when cloning an existing token:

1. `Reusing existing policies is not supported by token creation` — strip the policy `id` and rebuild
   `{effect, resources, permission_groups:[{id}]}`.
2. `sub-token is not allowed to have permissions to manage other tokens` — drop any `Account API Tokens
   Read/Write` group. Expect the replacement to hold ~277 of 279 groups.

Order that never leaves you without a working credential: mint replacement → write to `.env` → verify
(REST + real MCP `initialize`) → only then `DELETE` the exposed token. The deleted token's R2 S3
credentials are issued alongside it and die with it.
