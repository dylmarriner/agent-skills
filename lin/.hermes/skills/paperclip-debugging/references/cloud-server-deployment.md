# Paperclip Cloud Server Deployment

Setting up Paperclip, LiteLLM, and OpenCode on a fresh Ubuntu cloud server (24.04).

## Prerequisites

- Ubuntu 24.04 cloud server with Tailscale connected
- Node 22+, pnpm 10+
- Paperclip repo cloned (the forked version at `HenkDz/paperclip`)
- Root SSH access
- GCP Vertex AI project with credentials for LiteLLM

## Step 1: Install PostgreSQL

```bash
apt-get install -y postgresql postgresql-client
systemctl start postgresql

# Create database and user
su - postgres -c "psql -c \"CREATE USER paperclip WITH PASSWORD 'paperclip';\""
su - postgres -c "psql -c \"CREATE DATABASE paperclip OWNER paperclip;\""
```

## Step 2: Set Up LiteLLM

LiteLLM runs in Docker. The critical part is mounting GCP Vertex AI credentials INTO the container.

### Create LiteLLM config

```yaml
# /root/.litellm/config.yaml
model_list:
  - model_name: gemini-3.1-pro-preview
    litellm_params:
      model: vertex_ai/gemini-3.1-pro-preview
      vertex_project: ai-system-495310
      vertex_location: global
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: ai-system-495310
      vertex_location: global
  # ... add other models as needed

general_settings:
  master_key: sk-litellm-local
  database_url: null
```

### Create GCP service account key

If running under a GCP service account, create a key:

```bash
gcloud iam service-accounts keys create /tmp/key.json \
  --iam-account your-sa@project.iam.gserviceaccount.com
```

### Run LiteLLM Docker container

```bash
# Must mount the creds file into the container
docker run -d --name litellm --restart always \
  -p 4000:4000 \
  -v /root/.litellm/config.yaml:/app/config.yaml \
  -v /root/.config/gcloud:/root/.config/gcloud:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  ghcr.io/berriai/litellm:main-latest \
  --config /app/config.yaml --port 4000
```

**Pitfall:** OAuth refresh tokens from `gcloud auth application-default login` do NOT survive being copied to another machine. Always use a service account key for server deployments.

### Verify LiteLLM

```bash
curl -s -H 'Authorization: Bearer sk-litellm-local' http://localhost:4000/v1/models
```

## Step 3: Configure OpenCode

### Config

```json
{
  "model": "vertex/gemini-3.1-flash-lite",
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "sk-litellm-local"
      },
      "models": {
        "gemini-3.1-flash-lite": { "name": "Gemini 3.1 Flash Lite" },
        "gemini-2.5-pro": { "name": "Gemini 2.5 Pro" },
        ...
      }
    }
  }
}
```

Write to both `/root/.config/opencode/opencode.json` and `/root/.opencode/opencode.json`.

### Verify

```bash
export PATH=$PATH:/root/.opencode/bin
opencode models  # Should show vertex/* models from LiteLLM
```

## Step 4: Install & Configure Paperclip

### Database migrations

Run migrations with the DATABASE_URL explicitly set:

```bash
DATABASE_URL=postgres://paperclip:paperclip@localhost:5432/paperclip pnpm db:migrate
```

### Config file location

Paperclip looks for `.paperclip/config.json` by searching ancestor directories from `process.cwd()`. The correct location is the **repo root**:

```
/root/paperclip/.paperclip/config.json
/root/paperclip/.paperclip/.env
```

**NOT** at `~/.paperclip/instances/default/config.json` — that's the default fallback only if no config is found via ancestor search.

### Config file schema validation

The config must pass a Zod schema (`paperclipConfigSchema`). Common validation failures:

| Error | Fix |
|-------|-----|
| `secrets.provider: "local"` | Must be `"local_encrypted"` |
| `server.exposure must be private when deploymentMode is local_trusted` | Set `exposure: "private"` when mode is `local_trusted` |
| Any `$meta` escape issue | Write JSON properly (`\$meta` in heredocs gets corrupted — use `python3 -c "import json; ..."` piped to the file) |

### Config file example

```json
{
  "$meta": {
    "version": 1,
    "updatedAt": "2026-05-15T17:39:00.000Z",
    "source": "configure"
  },
  "database": {
    "mode": "postgres",
    "connectionString": "postgres://paperclip:paperclip@localhost:5432/paperclip"
  },
  "logging": {
    "mode": "file",
    "logDir": "/root/.paperclip/instances/default/logs"
  },
  "server": {
    "deploymentMode": "authenticated",
    "exposure": "private",
    "bind": "tailnet",
    "host": "0.0.0.0",
    "port": 3100,
    "allowedHostnames": ["100.102.4.39", "100.93.75.87"],
    "serveUi": true
  },
  "telemetry": { "enabled": true },
  "auth": { "baseUrlMode": "auto", "disableSignUp": false },
  "storage": { "provider": "local_disk", "localDisk": { "baseDir": "..." } },
  "secrets": { "provider": "local_encrypted" }
}
```

### Required env vars (`.paperclip/.env`)

```
DATABASE_URL=postgres://paperclip:paperclip@localhost:5432/paperclip
BETTER_AUTH_SECRET=paperclip-dev-secret
```

Without `BETTER_AUTH_SECRET`, the server exits with: `BETTER_AUTH_SECRET (or PAPERCLIP_AGENT_JWT_SECRET) must be set.`

### Systemd service

```ini
[Unit]
Description=Paperclip dev server
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory=/root/paperclip
ExecStart=/usr/bin/pnpm --filter @paperclipai/server dev
Restart=always
RestartSec=5
Environment=DATABASE_URL=postgres://paperclip:paperclip@localhost:5432/paperclip
Environment=PAPERCLIP_MIGRATION_PROMPT=never
Environment=PAPERCLIP_MIGRATION_AUTO_APPLY=true
Environment=HOME=/root
Environment=PATH=/usr/local/bin:/usr/bin:/bin:/usr/lib/node_modules/.bin:/root/.local/share/pnpm

[Install]
WantedBy=multi-user.target
```

**Pitfall:** Verify `which pnpm` — it may be at `/usr/bin/pnpm`, not `/usr/local/bin/pnpm`.

### Tailnet binding

The `npm_config_bind=tailnet` env var only works with the **dev-runner** script (`scripts/dev-runner.ts`), which is invoked by `pnpm dev`. When running `pnpm dev:server` (which directly runs `tsx src/index.ts`), the dev-runner is NOT involved.

To bind to Tailscale when using `pnpm dev:server`, set `bind: tailnet` in the config file instead. The `PAPERCLIP_TAILNET_BIND_HOST` env var is also read by the server.

## Step 5: Running as Root

Running Paperclip as root requires:
- `secrets.provider: local_encrypted` (not `local`) in the config
- Embedded PostgreSQL is NOT supported as root (`createPostgresUser` option needed)
- Use external PostgreSQL (DATABASE_URL) instead

## Step 6: Access

The server will be accessible at `http://<tailscale-ip>:3100`. On first access, the user needs to:
1. Sign up (creates first company)
2. Configure adapter plugins
3. Create agents

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `BETTER_AUTH_SECRET must be set` | Missing env var | Add to `.paperclip/.env` |
| `Using embedded PostgreSQL` when DATABASE_URL is set | Env not propagating to pnpm subprocess | Set in systemd `Environment=` OR in `.paperclip/.env` file |
| `createPostgresUser` error | Running as root, embedded postgres | Use `database.mode: postgres` with `DATABASE_URL` instead |
| Config silently ignored | Schema validation failure | Run through `paperclipConfigSchema.safeParse()` manually to find issues |
| Server on 127.0.0.1 not Tailscale IP | `bind: tailnet` not in config | Add to config file `server.bind` — don't rely on `npm_config_bind` env |
