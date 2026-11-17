---
name: hermes-web-dashboard
description: Start, verify, and register the Hermes Agent web dashboard — local dashboard launches, machine-level vs profile-level behavior, and Nous Portal OAuth client setup for self-hosted/public access.
---

# Hermes Web Dashboard

Use this skill when the user wants to start, debug, or register the Hermes Agent web dashboard, especially when OAuth or local-vs-remote access is involved.

## Trigger cases
- "start the dashboard"
- "open Hermes web portal"
- "connect local Hermes to the dashboard"
- "register the dashboard OAuth client"
- "why did it open Obelisk instead of Hermes?"

## Core workflow
1. Confirm the target is Hermes, not a different project with a web UI.
2. Start the dashboard with `hermes dashboard --no-open` for a local browser UI.
3. Verify the server actually responds in a browser at `http://127.0.0.1:9119/` unless a different port was requested.
4. If the user needs OAuth registration for a self-hosted or public dashboard, run `hermes dashboard register`.
5. For public access, use `--redirect-uri` only for the full HTTPS callback URL. For localhost-only use, omit it.
6. Set `dashboard.oauth.client_id` (or `HERMES_DASHBOARD_OAUTH_CLIENT_ID`) from the registration result.

## Important distinctions
- `hermes dashboard` is the browser web UI.
- `hermes serve` is the same backend, headless.
- The dashboard is machine-level; profile launches can preselect a profile, but the server is still shared unless explicitly isolated.
- `hermes setup --portal` is for Nous Portal provider onboarding, not the dashboard itself.

## Verification
- Use a browser or HTTP check against the dashboard URL.
- Confirm the page title and navigation load, not just that a process exists.
- If the page returns 500, inspect server logs before assuming the launch succeeded.

## Pitfalls
- Do not assume a background process means the dashboard is usable; verify the HTTP response.
- Do not confuse Obelisk or another local web app with Hermes.
- For localhost use, do not over-specify the redirect URI. For public use, register the HTTPS callback explicitly.
- `dashboard.oauth.client_id` is the config key that matters for the local dashboard login gate; the registration command writes it to `~/.hermes/.env` as `HERMES_DASHBOARD_OAUTH_CLIENT_ID`.

## References
- See `references/hermes-dashboard-portal.md` for the session-derived setup notes and exact command sequence.
