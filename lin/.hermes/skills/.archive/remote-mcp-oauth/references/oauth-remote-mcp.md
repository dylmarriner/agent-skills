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
hermes config set mcp_servers.<name>.oauth.redirect_port <port>   # only if 27890 is occupied
hermes config set mcp_servers.<name>.enabled true          # AFTER tokens exist
```

In a non-interactive shell `hermes mcp add --auth oauth` reports *"non-interactive environment and
no cached tokens found"*, fails its probe, and saves the server **disabled**. Expected: save it,
log in, then enable.

Only edit `mcp_servers` through `hermes config set` — direct config edits are blocked.

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

**Driving the login for a user who is sitting at the machine.** The script binds the callback port,
prints `LISTENING on 127.0.0.1:<port>` and then the authorize URL on stdout, so background it to a
log and drive it from the log:

```bash
(timeout 300 python3 ~/.hermes/skills/mcp/remote-mcp-oauth/scripts/oauth_pkce_login.py <name> \
  > /tmp/<name>-login.log 2>&1 &)
sleep 6
grep -o 'https://[^ ]*authorize[^ ]*' /tmp/<name>-login.log | head -1   # the URL to hand over
ss -ltnp | grep <port>            # prove the listener is bound before opening anything
xdg-open "<url>"                  # the user completes sign-in in their own browser
for i in $(seq 1 60); do [ -f "$HERMES_HOME/mcp-tokens/<name>.json" ] && break; sleep 5; done
```

The token file appearing is the only proof the user finished; the script then prints
`TOKENS WRITTEN: <path> (expires_in=..., refresh present)`. Assert the `refresh present` clause —
opening the URL is not the login, and neither is a browser tab that reached the consent screen.

**Device code** — only when discovery advertises `device_authorization_endpoint`; otherwise the grant
does not exist on that server and there is no fallback.

## 6. Verification

1. `hermes mcp test <name>` — connection and tool discovery; on success it prints every discovered
tool with its description, so the exact callable names are known before any restart.
2. Assert the token file exists and carries `refresh_token` — a `.client.json` alone means an earlier
flow registered the client and never finished the login.
3. `hermes config set mcp_servers.<name>.enabled true`.
4. Restart each process that must see the tools, then confirm registration from the log:
   `journalctl --user -u hermes-gateway.service --since "2 minutes ago" | grep -i mcp` lists which
   servers connected, which parked with their error, and any tool-name shortening. No failure line
   for your server is the registration evidence; one real tool call is the completion evidence.
5. Without a client at hand, `curl` `initialize` with the stored bearer proves the token end.

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
