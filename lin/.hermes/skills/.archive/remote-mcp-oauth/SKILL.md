---
name: remote-mcp-oauth
description: "Use when a remote MCP server needs OAuth login."
version: 1.0.0
metadata:
  hermes:
    tags: [MCP, OAuth, Integrations, Remote Access]
    related_skills: [native-mcp, mcporter]
---

# OAuth-Protected Remote MCP Servers

Connecting Hermes to a remote MCP endpoint that demands OAuth (401 `Authorization header
required`), plus the hosted relay device agents that expose a whole machine instead of a single
API. Covers the login, the token store the login must leave behind, and the verification that
proves the install landed.

Config plumbing (transports, `mcp_servers` keys, tool naming, restart rules) lives in the
`native-mcp` skill — read it for the config surface. This skill is the auth half.

## Procedure

1. **Probe the endpoint before touching config.** POST `initialize` with
   `Accept: application/json, text/event-stream`. `401 ... Authorization header required`
   means OAuth; `200` means just add `url:` and stop here.
2. **Discover the auth server.** `GET <issuer>/.well-known/oauth-authorization-server` for
   `authorization_endpoint` / `token_endpoint` / `registration_endpoint`; note whether
   `device_authorization_endpoint` is present — that alone decides if a device-code flow exists.
3. **Configure.** `hermes mcp add <name> --url <url> --auth oauth`, then
   `hermes config set mcp_servers.<name>.auth oauth` and
   `mcp_servers.<name>.oauth.flow browser|device`. Leave it disabled until tokens exist.
4. **Log in.** `python3 scripts/oauth_pkce_login.py <name>`, or
   `hermes mcp login <name> --flow browser` when a browser on this host can reach the
   `127.0.0.1:<port>/callback` redirect.
5. **Confirm.** `hermes mcp test <name>` — on success it prints the full discovered tool list, so
   the exact callable names are known before any restart. Then
   `hermes config set mcp_servers.<name>.enabled true`, then restart every process that must see the
   tools, then one real tool call.

Full detail, config table, token-store shape, verification snippets and device-agent pairing:
`references/oauth-remote-mcp.md`. Single-flow PKCE login:
`scripts/oauth_pkce_login.py <server-name>`.

## Always-on rules

- **Never wire a session JWT into `headers: Authorization`.** Hand-pasted tokens expire
  (Supabase-backed relays ship ~1h access tokens) and nothing refreshes them, so the server
  silently drops disconnected later. Run the login so Hermes stores a `refresh_token` and owns
  renewal.
- **A token file without `refresh_token` is a broken install.** `$HERMES_HOME/mcp-tokens/<name>.json`
  is an `OAuthToken` JSON: `access_token`, `token_type`, `expires_in`, `scope`, `refresh_token`,
  mode 0600. When hand-writing one, assert the refresh token is present before declaring success.
- **`hermes mcp add --auth oauth` failing in a non-interactive shell is expected, not a bug.** It
  cannot complete OAuth with no TTY, so it saves the server disabled; the login step follows.
- **A login that printed a URL and then failed did not necessarily lose the port to another
  process.** Check `ss -ltnp | grep <port>` and the exit line before blaming a stale listener —
  guessing wrong here costs a whole retry cycle.
- **Check the capability before promising the flow.** No `device_authorization_endpoint` in the
  discovery payload means `--flow device` cannot work at all; say so instead of retrying it.
- **Restart is part of the install, and it is per-process.** Discovery happens at process startup —
  `/reset` is not enough, and restarting one Hermes process does not load tools into another.
  Restart the long-lived gateway (`systemctl --user restart hermes-gateway.service`) *and* tell the
  user to restart their interactive session: a session already running keeps the tool catalog it
  started with, so restarting a service cannot make the tools appear inside the live session.
  Report the job unfinished until a real tool call succeeds.
- **Tell the user which manual step applies, never both.** With a listener bound on the host, the
  browser redirect completes the flow untouched; only a genuinely remote browser needs the
  paste-the-`code=` fallback. Handing over both wastes their time.

## Pitfalls

- `hermes mcp login --flow browser` starts the authorization flow twice in one process when
  headless: it prints a URL and binds the callback port, prints a second URL with a new `state`,
  then re-binds and dies with `[Errno 98] Address already in use` — taking the advertised nonce
  with it. The symptom is a login that printed a usable-looking URL and then failed.
  `scripts/oauth_pkce_login.py` exists because one listener / one bind / one flow is the reliable
  shape.
- `lsof` and `fuser` show nothing for another user's process without root; `ss -ltnp` does print
  the owning pid for the callback port.
- Dynamic client registration happens on the first attempt, so `<name>.client.json` survives a
  failed flow. Reuse it: the registered `redirect_uris` must match the redirect you send, so
  changing the callback port means re-registering.
- **Tool names longer than 64 characters are registered under a hash-suffixed alias.** Startup logs
  `exceeds the 64-char provider limit; shortened to a deterministic hash-suffixed name`; the tool is
  still callable, so when an expected name is absent, search by the server prefix instead of
  concluding the tool was dropped.
- Hosted relay device agents pair with a printed URL + code, need no TTY, and persist credentials
  to disk — run them as a `systemd --user` unit with `Restart=always` (linger enabled) rather than
  trusting the docs' "keep this terminal open" instruction, which dies at logout.
- Pairing a device agent does NOT authenticate the client. The hosted `/mcp` endpoint still needs
  its own OAuth login with the same account; they are two independent authorizations.
