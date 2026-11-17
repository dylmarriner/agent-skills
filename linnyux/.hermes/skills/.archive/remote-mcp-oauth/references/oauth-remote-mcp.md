# OAuth-Protected Remote MCP Servers — Detail

## 1. Identify the auth requirement first

```bash
curl -sS -i -X POST <mcp-url> -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

- `401 {"error":"Unauthorized","message":"Authorization header required"}` → OAuth needed.
- `200` with `serverInfo` → plain endpoint, add `url:` and stop.

Re-running with `-H "Authorization: Bearer $TOK"` validates the bearer and the transport in one
call (a `200` plus `serverInfo.name` is the evidence).

## 2. Discover the auth server

```bash
curl -sS <issuer>/.well-known/oauth-authorization-server
curl -sS <issuer>/.well-known/oauth-protected-resource
```

Yields `authorization_endpoint`, `token_endpoint`, `registration_endpoint`,
`grant_types_supported`, `token_endpoint_auth_methods_supported`, and — only when supported —
`device_authorization_endpoint`. The protected-resource document names the `authorization_servers`
and `scopes_supported` — take the `resource` and `scope` values for the authorization request from
there, since servers that advertise `resource_indicators_supported` expect them.

## 3. Configuration

```bash
hermes mcp add <name> --url <mcp-url> --auth oauth
hermes config set mcp_servers.<name>.auth oauth
hermes config set mcp_servers.<name>.oauth.flow browser    # or device
hermes config set mcp_servers.<name>.oauth.redirect_port <port>   # occupied port, or to pin a hand-rolled flow
hermes config set mcp_servers.<name>.enabled true          # AFTER tokens exist
```

In a non-interactive shell `hermes mcp add --auth oauth` reports *"non-interactive environment and
no cached tokens found"*, fails its probe, and saves the server **disabled**. Expected: save it,
log in, then enable.

Only edit `mcp_servers` through `hermes config set` — direct config edits are blocked.

Not every provider uses dynamic client registration. When the authorization server advertises
`client_id_metadata_document_supported: true`, the `client_id` is a **hosted JSON document**
(Hermes' is `https://nousresearch.github.io/hermes-agent/docs/oauth/client-metadata.json`) instead
of a DCR-issued id, and its `redirect_uris` enumerate a *closed set of fixed ports* (27890-27894 for
that document). Consequences: `<name>.client.json` still lands after the first attempt, but the
callback port is not free-form — a hand-rolled listener must bind a port that document lists, and
`oauth.redirect_port` should be set to the same port so the flow Hermes runs later reuses the
registered redirect.

## 4. Token store — the shape a login must leave behind

`HermesTokenStorage` (`tools/mcp_oauth.py`) keeps per-server state in `$HERMES_HOME/mcp-tokens/`:

| File | Contents |
|------|----------|
| `<name>.client.json` | DCR'd client: `client_id`, `client_secret`, `redirect_uris[0]`, `token_endpoint_auth_method`, `issuer`, `scope` |
| `<name>.json` | `OAuthToken`: `access_token`, `token_type`, `expires_in`, `scope`, `refresh_token` |
| `<name>.meta.json` | authorization-server metadata (written during discovery) |
| `<name>.cimd-off` | marker when CIMD client metadata was refused |

The SDK owns refresh at runtime, which is why the stored `refresh_token` (not the access token) is
the thing that makes an install durable.

## 5. Login flows

**Browser PKCE** — works headless on the same host (the `127.0.0.1:<port>/callback` redirect lands
on the listener). Over SSH, either forward the port
(`ssh -N -L <port>:127.0.0.1:<port> <host>`) or paste the failed redirect URL back at the prompt.

```bash
hermes mcp login <name> --flow browser
```

**One-shot PKCE (preferred when the built-in flow misbehaves)** — one listener, one bind, writes the
token file directly:

```bash
python3 ~/.hermes/skills/mcp/remote-mcp-oauth/scripts/oauth_pkce_login.py <name>
```

It reads `$HERMES_HOME/mcp-tokens/<name>.client.json` and `mcp_servers.<name>.url`, derives the auth
server from the client's `issuer`, and refuses to write a token set without a `refresh_token`.

**Device code** — only when discovery advertises `device_authorization_endpoint`; otherwise the grant
does not exist on that server and there is no fallback.

## 6. Verification

1. `hermes mcp test <name>` — connection and tool discovery.
2. `hermes config set mcp_servers.<name>.enabled true`.
3. Full Hermes restart, then one real tool call. Only then is the install done.
4. Without a client at hand, `curl` `initialize` with the stored bearer proves the token end.

## 7. Hosted relay device agents

Shape: a hosted MCP server relays tool calls to a small agent running on the target machine, so any
AI app that supports remote MCP connectors (Claude, ChatGPT, Cursor, Gemini CLI, Hermes) can drive
that box from anywhere. Remote Desktop Commander (`https://mcp.desktopcommander.app/mcp`) is one
instance; its agent ships in the npm package `@wonderwhy-er/desktop-commander` as
`desktop-commander remote`.

- Install the agent from the ecosystem package manager (`npm i -g @wonderwhy-er/desktop-commander`)
  instead of `npx` on every start. Flags: `--logout`, `--no-persist-session`, `--disable-no-sleep`,
  `--debug`.
- Pairing is an RFC 8628-style check: the agent prints a URL **and** a code, opens no browser itself,
  and needs one approval from an account signed in to that service. It therefore works under systemd
  — read the code from the journal.
- Credentials persist (Remote Desktop Commander: `~/.desktop-commander-device/device.json` with
  Supabase `access_token` + `refresh_token`), so a restart logs `Session restored` and the device
  returns online without re-pairing.
- Run it as a `systemd --user` unit with `Restart=always` and linger enabled. The docs' "leave this
  terminal window open" instruction does not survive a logout.
- Verify from the agent side: the journal prints `Device marked as online` / `Device ready` with the
  device id, device name, and account — proof the relay accepted the pairing.
- The agent's own session JWT also authenticates against the hosted `/mcp` endpoint, but it is a
  short-lived (~1h) token — fine as a diagnostic probe, never as a configured `headers:` entry.

## 8. Bearer-token alternative, and diagnosing a failing token

Many hosted MCP servers that front a provider's own API accept that provider's **API token** as a
static bearer (Cloudflare's does, user- and account-owned both). Unlike a session JWT this does not
rot, so it removes the refresh cycle entirely:

```yaml
mcp_servers:
  <name>:
    url: "<mcp-url>"
    headers:
      Authorization: "Bearer ${PROVIDER_TOKEN}"
```

Distinguish the failure modes before touching config — each points somewhere different:

- **User-scoped token-verify says "Invalid API Token"** → it may be an *account-owned* token
  (`cfat_…` prefix for Cloudflare), verified through the account-scoped endpoint, not
  `/user/tokens/verify`. A failed user-scoped check alone does not mean the token is fake.
- **MCP endpoint returns `insufficient_scope` naming a missing scope** (e.g. `user:read`,
  `account:read`) → a provider-side permissions problem; re-mint the token, do not touch Hermes.
- **Provider API rejects with a location/permission error while the MCP endpoint authenticates**
  (Cloudflare: `Cannot use the access token from location: <ip>`) → the token carries an IP
  allowlist. No scope change will help from this host.
- **Plain 401 with no scope or location detail** → genuinely expired or revoked.

A token sitting in a project `.env` is not evidence it works *now*: verify it against the provider
before recommending the bearer path or wiring it into `headers:` — and treat a bearer install as a
fallback, not an equivalent substitute, since it cannot be scoped down per-account the way the
consent screen can.
