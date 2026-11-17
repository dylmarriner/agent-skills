# Multica Self-Hosted Setup — Session Reference

**Version:** v0.3.5 (commit cb90249e, 2026-05-21)
**Stack:** Go backend + Next.js 16 frontend + PostgreSQL 17 with pgvector
**Self-host install path:** Docker Compose via `make selfhost`
**Images:** ghcr.io/multica-ai/multica-backend:latest, ghcr.io/multica-ai/multica-web:latest, pgvector/pgvector:pg17

## Hardware / OS

- Linux x86_64 (6.8.0-111-generic)
- Docker 29.4.3, Docker Compose v5.1.3
- Tailscale IP: 100.93.75.87
- User: kubuntux

## Install Summary

1. **CLI installed manually** — the install script failed on `sudo` in non-interactive context. Downloaded v0.3.5 tarball from GitHub Releases, extracted to `~/.local/bin/multica`.
2. **Self-host stack** — cloned repo to `/tmp/multica-server`, ran `make selfhost`.
3. **Port 5432 conflict** — local system PostgreSQL (pg 16, systemd service) was already bound to 127.0.0.1:5432. Resolved by `sudo systemctl stop postgresql && sudo systemctl disable postgresql`, then retried `make selfhost`.
4. **Dev auth** — Set `APP_ENV=development` and `MULTICA_DEV_VERIFICATION_CODE=888888` in `.env`, restarted backend.
5. **Token injection** — Instead of browser OAuth, sent curl requests to `/auth/send-code` and `/auth/verify-code`, got JWT, wrote it to `~/.multica/config.json` as the `token` field.
6. **Workspace** — POST to `/api/workspaces` with `{"name":"My Workspace","slug":"my-workspace"}`, set `workspace_id` via `multica config set`.
7. **Daemon** — `multica daemon start` ran in background. Logs at `~/.multica/daemon.log`.
8. **Tailscale remote access** — Added dual port bindings (127.0.0.1 + 100.93.75.87) in `docker-compose.selfhost.yml` for backend (8080) and frontend (3000). Updated env vars to point to Tailscale IP (FRONTEND_ORIGIN, MULTICA_APP_URL, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL, CORS_ALLOWED_ORIGINS, MULTICA_PUBLIC_URL, LOCAL_UPLOAD_BASE_URL). Restarted containers with `docker compose up -d`.

## Tailscale-Specific Config Changes

### docker-compose.selfhost.yml

Added dual bindings to the `backend` and `frontend` services while keeping localhost:

```yaml
services:
  backend:
    ports:
      - "127.0.0.1:${PORT:-8080}:8080"
      - "100.93.75.87:${PORT:-8080}:8080"
  frontend:
    ports:
      - "127.0.0.1:${FRONTEND_PORT:-4100}:3000"
      - "100.93.75.87:${FRONTEND_PORT:-4100}:3000"
```

### Frontend port changes (3000 → 3100 → 4100)

The default frontend port 3000 was taken by Grafana, then 3100 was taken by Paperclip. Final port: **4100**.

When changing the frontend port, ALL these references must be updated:

- **docker-compose.selfhost.yml**: The `FRONTEND_PORT:-<OLD>` default in both port binding lines
- **.env**: `FRONTEND_PORT`, `FRONTEND_ORIGIN`, `MULTICA_APP_URL`, `CORS_ALLOWED_ORIGINS`
- Restart with `docker compose up -d` (not `restart` — doesn't re-read .env)

### .env changes for Tailscale

```
FRONTEND_PORT=4100
FRONTEND_ORIGIN=http://100.93.75.87:4100
MULTICA_APP_URL=http://100.93.75.87:3000
NEXT_PUBLIC_API_URL=http://100.93.75.87:8080
NEXT_PUBLIC_WS_URL=ws://100.93.75.87:8080/ws
CORS_ALLOWED_ORIGINS=http://100.93.75.87:3000,http://localhost:3000
MULTICA_PUBLIC_URL=http://100.93.75.87:8080
LOCAL_UPLOAD_BASE_URL=http://100.93.75.87:8080
```

## Useful API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/send-code` | POST | Request verification code (body: `{"email":"..."}`) |
| `/auth/verify-code` | POST | Exchange code for JWT (body: `{"email":"...","code":"...","flow":"signup"}`) |
| `/api/workspaces` | POST | Create workspace (body: `{"name":"...","slug":"..."}`, needs `Authorization: Bearer <token>`) |
| `/api/config` | GET | Public app config (no auth needed) |
| `/api/me` | GET | Current user info (needs auth) |

## Detected Agents

When the daemon started, it auto-detected these agent CLIs on PATH: gemini, pi, kiro, codex, opencode, openclaw, hermes.

## Quick Commands

```bash
# Check daemon
multica daemon status

# Workspace
multica workspace list
multica config set workspace_id <id>

# Issues (requires workspace set)
multica issue list
multica issue create

# Restart backend after .env changes
cd /tmp/multica-server && docker compose -f docker-compose.selfhost.yml restart backend

# View auth code (when no email configured)
docker compose -f docker-compose.selfhost.yml logs backend | grep "Verification code"

# Stop everything
cd /tmp/multica-server && docker compose -f docker-compose.selfhost.yml down
```
