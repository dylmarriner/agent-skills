---
name: self-hosted-app-setup
description: 'Install and configure Docker Compose-based self-hosted applications: CLI install, stack bootstrap, port conflict recovery, dev auth bypass, and direct token injection to skip browser OAuth flows.'
tags: [docker, docker-compose, self-host, dev-auth, devops]
---

# Self-Hosted App Setup

Guide for installing and configuring Docker Compose-based self-hosted applications. Covers the full lifecycle: CLI install, stack bootstrap, auth setup, workspace creation, and daemon configuration.

## Prerequisites

- Docker and Docker Compose
- Git (for cloning app repos)
- ~/.local/bin/ in PATH (for sudo-less CLI installs)

## Step 1 — CLI Installation

If the install script fails due to sudo requirements in non-interactive contexts:

```bash
# Download the release tarball manually
curl -fsSL https://github.com/<owner>/<repo>/releases/download/<tag>/<binary>-<version>-linux-amd64.tar.gz -o /tmp/app.tar.gz

# Extract
cd /tmp && tar xzf app.tar.gz

# Install to local bin
mkdir -p ~/.local/bin
cp /tmp/<binary> ~/.local/bin/
chmod +x ~/.local/bin/<binary>
```

## Step 2 — Stack Bootstrap

Clone the repo and start services:

```bash
git clone --depth 1 https://github.com/<owner>/<repo>.git /tmp/app-server
cd /tmp/app-server
make selfhost    # or: docker compose -f docker-compose.selfhost.yml up -d
```

## Step 3 — Port Conflict Recovery

If Docker fails with "address already in use", identify and resolve:

```bash
# Find what's on the port
sudo ss -tlnp | grep <PORT>

# Stop conflicting service (e.g., system PostgreSQL)
sudo systemctl stop postgresql
sudo systemctl disable postgresql

# Retry
make selfhost
```

## Step 4 — Dev Auth Bypass

For local development/testing without email infrastructure:

1. Set dev verification code and environment in `.env`:
   ```
   APP_ENV=development
   MULTICA_DEV_VERIFICATION_CODE=888888
   ```
2. Recreate the backend container (`.env` changes require full `up -d`, not `restart`):
   ```bash
   docker compose -f docker-compose.selfhost.yml up -d
   ```
3. Enter the code `888888` at the verification prompt.
   **Security warning:** Never set `MULTICA_DEV_VERIFICATION_CODE` on a publicly reachable instance — anyone with any email can log in.

## Step 5 — Direct Token Injection (Skip Browser OAuth)

If the CLI login opens a browser that can't complete in a headless context:

1. Call the auth API directly with curl to get a JWT:
   ```bash
   # Send verification code
   curl -s -X POST http://localhost:8080/auth/send-code \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.local"}'

   # Get code from backend logs
   docker compose logs backend | grep "Verification code"

   # Exchange for token
   curl -s -X POST http://localhost:8080/auth/verify-code \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.local","code":"<CODE>","flow":"signup"}'
   ```

2. Write the token directly to the CLI config file at `~/.multica/config.json`:
   ```json
   {
     "server_url": "http://localhost:8080",
     "app_url": "http://localhost:3000",
     "token": "<JWT_TOKEN>"
   }
   ```

3. Start the daemon:
   ```bash
   multica daemon start
   ```

## Step 6 — Workspace Creation & Configuration

Create a workspace via API (if the web UI auto-create didn't trigger on signup):

```bash
curl -s -X POST http://localhost:8080/api/workspaces \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{"name":"My Workspace","slug":"my-workspace"}'
```

Set the active workspace:

```bash
multica config set workspace_id <WORKSPACE_ID>
```

## Verification

```bash
multica daemon status
multica workspace list
```

## Remote Access via Tailscale / Private Mesh

Self-hosted apps often need to be reachable from other machines on a private mesh (Tailscale, ZeroTier, Nebula) while keeping the local daemon/CLI working on the same host.

### Pattern: Dual Port Binding (127.0.0.1 + Tailscale IP)

Docker Compose files typically bind to `127.0.0.1` for safety (the comment often warns against `0.0.0.0` since Docker bypasses host firewalls). The safe middle ground for private mesh access is binding to both:

```yaml
ports:
  # Local access (daemon/CLI on same machine)
  - "127.0.0.1:${PORT:-8080}:8080"
  # Remote access via private mesh
  - "<TAILSCALE_IP>:${PORT:-8080}:8080"
```

Get the Tailscale IP with: `tailscale ip -4`

### Environment Variables to Update for Remote Access

When switching from `localhost` to a Tailscale IP, update these env vars (exact names vary per app):

| Variable | Old Value | New Value |
|---|---|---|
| `FRONTEND_ORIGIN` | `http://localhost:3000` | `http://<TAILSCALE_IP>:3000` |
| `MULTICA_APP_URL` / `APP_URL` | `http://localhost:3000` | `http://<TAILSCALE_IP>:3000` |
| `NEXT_PUBLIC_API_URL` | (empty / localhost) | `http://<TAILSCALE_IP>:8080` |
| `NEXT_PUBLIC_WS_URL` | (empty / localhost) | `ws://<TAILSCALE_IP>:8080/ws` |
| `CORS_ALLOWED_ORIGINS` | (empty / localhost) | `http://<TAILSCALE_IP>:3000,http://localhost:3000` |
| `MULTICA_PUBLIC_URL` | (empty) | `http://<TAILSCALE_IP>:8080` |
| `LOCAL_UPLOAD_BASE_URL` | `http://localhost:8080` | `http://<TAILSCALE_IP>:8080` |

After changing env vars, restart the stack: `docker compose -f docker-compose.selfhost.yml up -d`

The local daemon continues working because `127.0.0.1` bindings are preserved.

## Pitfalls

- **Rate limiting on auth:** If you hit 429 on `/auth/send-code`, wait ~60s before retrying.
- **Old daemon.id persists:** After a failed auth attempt, delete `~/.multica/daemon.id` and `~/.multica/daemon.log` before restarting the daemon with a valid token.
- **Browser login hangs:** If `multica login` opens a browser but the callback server doesn't start, use the direct token injection approach instead.
- **`config set token` not exposed:** The CLI's `config set` command does not accept a `token` key even though the JSON schema has one. Write the token field directly to `~/.multica/config.json`.
- **Dev code ignored:** If `MULTICA_DEV_VERIFICATION_CODE` is set but returns "invalid or expired code", ensure `APP_ENV` is actually set to `development` (not empty) and recreate containers with `docker compose up -d` after the change.
- **Docker port conflicts:** Always check for system-installed services on the same ports before starting the Docker stack.
- **Env var changes require `up -d`, not `restart`:** Docker Compose reads `.env` at startup. After modifying `.env`, run `docker compose -f docker-compose.selfhost.yml up -d` to recreate affected containers. `docker compose restart` does NOT re-read the `.env` file.
- **Frontend port change cascading:** If the default frontend port (3000) is taken, you must update EVERY reference to the old port in `.env` AND `docker-compose.selfhost.yml`. Common misses: `MULTICA_APP_URL`, `CORS_ALLOWED_ORIGINS`, the FRONTEND_PORT default in the compose file, and the Tailscale IP binding line. Use `ss -tlnp | awk '{print $4}' | grep -oP ':\\K\\d+' | sort -nu` to find a free port before picking one.
- **Port conflict chaining:** When moving frontend off 3000, the replacement port (3100) might also be taken by another service. Check with `ss -tlnp` and pick a port in a completely different range (e.g., 4100) if needed.


