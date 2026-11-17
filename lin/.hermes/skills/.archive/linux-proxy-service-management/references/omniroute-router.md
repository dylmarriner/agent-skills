# OmniRoute Router Operating Reference

Self-hosted AI router (dashboard/playground + OpenAI-compatible /v1 plane) on lin, installed as a global npm binary `omniroute` (v3.8.50). 352-provider router with RTK/Caveman compression, auto-fallback, MCP/A2A. Independent server — separate from the Bifrost default gateway.

## Lifecycle

```bash
# start daemonized, no browser
omniroute serve --daemon --no-open
# stop
omniroute stop
# status / restart
omniroute restart
# live logs: run foreground with --log
```

Install is already global (`~/.nvm/.../bin/omniroute`). `npm view omniroute` to see the current version if an update is requested.

## Endpoints (Tailscale reachable)

- Dashboard: `http://100.91.55.113:20128`  (root `/` returns 307 → dashboard)
- API base:  `http://100.91.55.113:20128/v1`
- Health:    `curl -s http://100.91.55.113:20128/api/health` → `{"status":"ok","timestamp":...}`
- Session probe: `/api/auth/session` returns `AUTH_001 Authentication required` when not logged in (dashboard auth is on even when the inference plane allows no-key).

## Files

| Path | Role |
|---|---|
| `~/.omniroute/.env` | User env overrides. Loaded FIRST; a var set here wins over the install `.env` (e.g. its `STORAGE_ENCRYPTION_KEY` is ignored if `~/.omniroute/.env` set one). |
| `~/.omniroute/storage.sqlite` (+ `-shm`/`-wal`) | All server state: auth, providers, quota, telemetry. `db_backups/` holds pre-migration dumps. |
| `~/.omniroute/logs/`, `server/`, `supervisor/` | Server data dirs. |
| `<node_modules>/omniroute/.env` | Install-time defaults: `INITIAL_PASSWORD`, `JWT_SECRET`, `API_KEY_SECRET`, `STORAGE_ENCRYPTION_KEY`, `REQUIRE_API_KEY`, `PORT=20128`, OAuth client IDs, per-tool user agents. |

## Dashboard auth & password recovery

- Login: username `admin`, password = current dashboard password.
- The password is NOT stored in plaintext anywhere. It lives in `storage.sqlite` key_value store as `settings|password` → a bcrypt hash (`$2b$12$...`), with `settings|setupComplete` = `true` once first-run setup ran.
- The plaintext that a fresh install accepts is the `INITIAL_PASSWORD` value from `<node_modules>/omniroute/.env` (bootstrap = `CHANGEME`). The stored hash was created from that value at setup unless it was changed since.
- To recover/verify WITHOUT guessing blind, bcrypt-compare candidates against the stored hash using the tool's own bundled bcryptjs (no global dep needed):

```bash
cd ~/.omniroute
HASH=$(sqlite3 storage.sqlite "SELECT value FROM key_value WHERE key='settings|password';")
# ^ key/value columns confirmed: rows are `settings|setupComplete` and `settings|password`
NODE_PATH=$HOME/.nvm/versions/node/v24.15.0/lib/node_modules/omniroute/node_modules \
  node -e '
    const b = require("bcryptjs");
    const h = process.argv[1];
    for (const c of ["CHANGEME","admin","omniroute","password"]) console.log(c, b.compareSync(c,h) ? "MATCH" : "no");
  ' "$HASH"
```

- If the bootstrap/default candidates don't match, the operator changed the password → it is unrecoverable; reset it (re-run setup / edit the stored value) rather than brute-forcing.
- No separate `users`/`accounts` table stores dashboard creds — the sqlite schema has no admin-password column; auth is JWT-cookie from the login against this single bcrypt hash. There IS a plaintext `password` column on `proxy_registry` (upstream proxy creds) — unrelated to the dashboard login.

## Security posture

Server starts with `REQUIRE_API_KEY=false` bound to `0.0.0.0` — the /v1 inference plane is reachable by ANY device that can route to the host and bills to the configured providers. Dashboard has the `CHANGEME` bootstrap password. On anything beyond a trusted single-user box, set `REQUIRE_API_KEY=true` and change the dashboard password. The `storage.sqlite` auth/state DB is plaintext SQLite (its STORAGE_ENCRYPTION_KEY only protects provider creds/API keys at rest in the store).
