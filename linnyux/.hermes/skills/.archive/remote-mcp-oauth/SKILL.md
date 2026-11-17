---
name: remote-mcp-oauth
description: "Use when a remote MCP server needs OAuth login — Cloudflare, Linear, Sentry, a hosted relay, or any 401-on-initialize endpoint. Covers discovery, the one-bind PKCE login script, the token-store shape, and driving the provider's consent screen from a headless shell."
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
3. **Configure — check the catalog first.** `hermes mcp catalog` lists Nous-approved entries and
   `hermes mcp install <name>` writes url + `auth: oauth` + any curated `tools.exclude` list in one
   shot. Entry flags carry intent: Cloudflare's pins `?codemode=false` so the provider's
   `search()/execute()` layer does not stack a second discovery hop under `tool_search` — do not
   "fix" it back. Installing is **not** authenticating: the server lands enabled and unusable until
   step 4. Otherwise: `hermes mcp add <name> --url <url> --auth oauth`, then
   `hermes config set mcp_servers.<name>.auth oauth` and
   `mcp_servers.<name>.oauth.flow browser|device`. Leave it disabled until tokens exist.
4. **Log in with the skill's script.** `python3 scripts/oauth_pkce_login.py <name>` — one listener,
   one bind, one exchange, writes the token file itself. Reach for this instead of
   `hermes mcp login <name> --flow browser` the moment the built-in flow has failed once with
   `[Errno 98] Address already in use`, and **do not hand-roll a replacement listener**: this
   script is that replacement. Pin `mcp_servers.<name>.oauth.redirect_port` when running any
   hand-rolled flow, so the port you bind is the port Hermes re-uses on refresh and re-auth.
5. **Confirm.** `hermes mcp test <name>`, then
   `hermes config set mcp_servers.<name>.enabled true`, then a **full** Hermes restart, then one
   real tool call.

Full detail, config table, token-store shape, verification snippets and device-agent pairing:
`references/oauth-remote-mcp.md`. Getting a human through the provider's consent screen on the
agent's own host: `references/browser-consent-handoff.md`. Single-flow PKCE login:
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
- **Restart is part of the install.** MCP servers are discovered at startup only; `/reset` is not
  enough. Report the job unfinished until a real tool call succeeds.
- **Tell the user which manual step applies, never both.** With a listener bound on the host, the
  browser redirect completes the flow untouched; only a genuinely remote browser needs the
  paste-the-`code=` fallback. Handing over both wastes their time.
- **Open the consent screen in the user's own browser session; never hand them a URL to paste.**
  An agent shell is headless (`DISPLAY`/`WAYLAND_DISPLAY` empty, `XDG_SESSION_TYPE=tty`, `SSH_CLIENT`
  set) even when a full desktop session is live on `:0` — which is also why the built-in flow prints
  "Remote session detected" and opens nothing. Launch the browser into that session yourself and
  drive the page. Mechanics: `references/browser-consent-handoff.md`.
- **Never type the user's password, keyring passphrase, or 2FA code, and never ask for one in
  chat.** Stop at the credential boundary, hand off the one step that needs them, and keep the
  listener alive across it — the handoff is asynchronous, not a race.
- **A browser that looks logged out may be unable to decrypt its cookie store, not signed out.**
  On Linux the browser needs the desktop keyring to read cookies; a locked keyring leaves every
  authenticated site rendering a login page while the cookie rows sit intact on disk. Confirm
  before asking the user to log in again, and leave the unlock to them.

## Pitfalls

- `hermes mcp login --flow browser` starts the authorization flow twice in one process when
  headless: it prints a URL and binds the callback port, prints a second URL with a new `state`,
  then re-binds and dies with `[Errno 98] Address already in use` — taking the advertised nonce
  with it. The symptom is a login that printed a usable-looking URL and then failed.
  `scripts/oauth_pkce_login.py` exists because one listener / one bind / one flow is the reliable
  shape.
- That failing port can be one nothing else has ever used, and `ss -ltn | grep <port>` will show it
  free — it is the same process re-binding, so a clean port is not evidence the flow is healthy;
  only a *stable* listener is. The advertised `state` dies with the process, so a page already open
  in a browser becomes stale: re-run the login and re-open the URL rather than clicking through the
  copy on screen.
- `lsof` and `fuser` show nothing for another user's process without root; `ss -ltnp` does print
  the owning pid for the callback port.
- Dynamic client registration happens on the first attempt, so `<name>.client.json` survives a
  failed flow. Reuse it: the registered `redirect_uris` must match the redirect you send, so
  changing the callback port means re-registering.
- Hosted relay device agents pair with a printed URL + code, need no TTY, and persist credentials
  to disk — run them as a `systemd --user` unit with `Restart=always` (linger enabled) rather than
  trusting the docs' "keep this terminal open" instruction, which dies at logout.
- Pairing a device agent does NOT authenticate the client. The hosted `/mcp` endpoint still needs
  its own OAuth login with the same account; they are two independent authorizations.
- A device agent that was offline across a token rotation cannot resume from its saved session —
  the journal logs `Invalid Refresh Token: Already Used` and it silently drops into a fresh device
  pairing instead of failing. That is a re-approval, not a broken install: read the new user code
  out of the journal and approve it.
- Approve that pairing as the account that OWNS the device, never by guessing which row to click in
  the provider's account chooser. The owning identity is inside the agent's own saved credentials:
  base64-decode the `sub`/`email` claims of the JWT in `~/.desktop-commander-device/device.json`
  (payload is the middle dot-segment) and pick the matching account.
- `oauth.flow: device` in the config is a landmine for hosted relays: check discovery for
  `device_authorization_endpoint` before trusting it. Desktop Commander advertises none, so the
  configured device flow can never succeed and must be flipped to `browser` (with `redirect_port`
  pinned to the port in the registered `redirect_uris`).
- DCR on such a server may answer `token_endpoint_auth_method: client_secret_post` and issue a
  `client_secret` even though the request asked for `none`. Store the secret in
  `<name>.client.json` — the login script sends it as a form field, and the token exchange fails
  without it.
- Installing the agent package with `npm i -g` warns that postinstall scripts were skipped (npm's
  `allowScripts` gate). That is not automatically a broken install: check the prebuilt platform
  packages actually load (`require('sharp')`, the bundled `@vscode/ripgrep-linux-x64/bin/rg`, the
  `~/.cache/puppeteer` browser) before reopening the install with `--allow-scripts` — the package's
  own `dist/npm-scripts/verify-ripgrep.js` is a ready-made check for one of them.
- The agent's default already prevents the machine from sleeping; add `--disable-no-sleep` to
  `ExecStart` if that is not wanted on the host.
