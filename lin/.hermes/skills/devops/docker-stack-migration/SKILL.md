---
name: docker-stack-migration
description: Migrate a multi-service Docker Compose stack between hosts, including cross-architecture transitions (x86 → ARM), data migration via pg_dump/restore, and compose adaptation per target.
author: Hermes
metadata:
  tags: [docker, compose, migration, arm, pi, postgres, pg_dump, cross-arch]
---

# Docker Stack Migration

Migrate a running Docker Compose stack from one host to another, handling architecture differences, data transfer, and compose adaptation.

## When to use

- Moving a Docker Compose stack from one machine to another
- Migrating from x86 (AMD64) to ARM (Raspberry Pi, Apple Silicon)
- Host A has GPU services that host B doesn't (or vice versa)
- Need to preserve PostgreSQL/Redis data during migration
- Setting up a new instance of an existing service on a Pi

## Instructions

### Phase 1 — Architecture Assessment

```bash
# Check target architecture
ssh <target> "uname -m"
# aarch64 = ARM64 (Pi 5, Apple M-series)
# x86_64 = AMD64/Intel

# Check Docker and Compose versions
ssh <target> "docker --version && docker compose version"

# Check what's already using target ports
ssh <target> "ss -tlnp | grep <port>"
ssh <target> "docker ps -a --format '{{.Names}} {{.Ports}}' | grep <port>"

# Check existing Docker services on target
ssh <target> "docker compose ls"
```

### Phase 2 — Compose Adaptation

Create a **target-specific compose file** (e.g. `docker-compose.<target>.yml`) that adapts the original for the new host:

**2.1 — Strip GPU-dependent services**

ARM (Pi) has no NVIDIA/AMD GPU. Remove or disable:
- `llama-server` (custom GPU images)
- Any service with `devices: [/dev/dri, /dev/kfd]`
- Any service with `runtime: nvidia`
- Any service referencing CUDA/cuDNN

**2.2 — Check image architecture support**

For each image in the compose file:
- `pgvector/pgvector:0.8.0-pg17` — multi-arch ✅
- `redis:8.2.2-alpine` — multi-arch ✅
- `python:3.11-slim` — multi-arch ✅
- Custom-built images → build on target (Dockerfile)

**Pre-check images on source:**
```bash
docker pull --platform linux/arm64 <image> 2>&1 | tail -3
```

**2.3 — Adjust environment for architecture differences**

- If GPU-dependent LLM service is removed, switch mind/reasoning models to external APIs:
  - `MIND_FALLBACK_MODEL` → cloud model (e.g. `deepseek-chat`)
  - `OLLAMA_BASE_URL` → empty or remove
  - `MIND_LLM_MODEL` → cloud model
- Check for `ENVIRONMENT=production` + `NEXUS_DISABLE_AUTH=true` combo — the app may refuse to start with auth disabled outside development. Set `ENVIRONMENT=development` in that case.

**2.4 — Fix depends_on**

After removing services, update the `depends_on` lists of remaining services to remove references to removed services.

### Phase 3 — Transfer Code

```bash
# Rsync the repo, excluding data dirs (handled separately)
rsync -av --progress \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='node_modules' \
  --exclude='data/postgres' \
  --exclude='data/redis' \
  /path/to/source/ \
  <target>:/path/to/target/
```

**Path placement on Pi:**
- Services go on SSD: `/opt/docker/<service-name>/`
- Bulk data (videos, large files) goes on NAS: `/srv/nas/main/`
- Do not put Docker stacks on the NAS drive — I/O latency and contention

### Phase 4 — Data Migration (PostgreSQL)

**4.1 — Dump on source:**

```bash
docker exec <source-postgres-container> pg_dump -U <user> -d <db> \
  --no-owner --no-acl > /tmp/<dump-name>.sql
```

NOTE: pg_dump from PostgreSQL 17 generates `\restrict <token>` metadata commands. These are harmless during dump but can block restore on a different server instance.

**4.2 — Transfer:**

```bash
rsync /tmp/<dump-name>.sql <target>:/path/to/target/data/
```

**4.3 — Restore on target:**

The easiest approach for pg17 dumps with `\restrict` commands:

```bash
# On target — first stop any services connected to the DB
# Drop and recreate the database
ssh <target> "docker exec <postgres-container> psql -U <user> -d postgres \
  -c 'DROP DATABASE IF EXISTS <db>;' && \
  docker exec <postgres-container> psql -U <user> -d postgres \
  -c 'CREATE DATABASE <db>;'"

# Import the dump
ssh <target> "docker cp /path/to/target/data/<dump-name>.sql \
  <postgres-container>:/tmp/dump.sql && \
  docker exec <postgres-container> psql -U <user> -d <db> \
  -f /tmp/dump.sql"
```

The `\restrict` commands in the dump are database-level security metadata that psql -f handles when connected to the specific database. If backslash-restrict errors appear, they're usually non-fatal — the actual INSERT/COPY statements still execute.

**4.4 — Verify:**

```bash
ssh <target> "docker exec <postgres-container> psql -U <user> -d <db> \
  -c 'SELECT count(*) FROM <main-table>;'"
```

### Phase 5 — Build and Start on Target

**5.1 — Build on ARM is slow:**

Python/ML images with torch, transformers, scikit-learn can take **10-15 minutes** on a Pi 5. Use background mode:

```bash
ssh <target> "cd /path/to/target && docker compose -f docker-compose.<target>.yml build <service>" &
# Or via terminal(background=true, notify_on_complete=true)
```

**5.2 — Image naming pitfall:**

Docker Compose with a `name:` field (e.g. `name: nexus`) expects images named `<name>-<service>:latest` (hyphen-separated). If `docker compose build` fails partway, or you build with a different compose file first, the image tag may differ.

Check what images exist and tag if needed:

```bash
ssh <target> "docker images | grep <project>"
# If tagged as <project>-<source>-<service>:latest but compose expects <project>-<service>:latest
ssh <target> "docker tag <bad-tag> <project>-<service>:latest"
```

**5.3 — Start with --no-build to use existing images:**

```bash
ssh <target> "cd /path/to/target && docker compose -f docker-compose.<target>.yml up -d --no-build"
```

If the image name mismatch isn't fixable, remove the `name:` from compose and let Docker auto-generate the project name.

**5.4 — Check health:**

```bash
ssh <target> "docker compose -f docker-compose.<target>.yml ps"
# All services should show "healthy" or "Up"
curl -s http://<target-ip>:<port>/health
```

### Phase 6 — Stop Source and Update Clients

```bash
# Stop the old stack
cd /path/to/source && docker compose down

# Update any client configs pointing to old IP
# e.g. ~/.hermes/nexus.env NEXUS_URL, MCP configs, etc.
```

### Phase 7 — Verify MCP/REST Endpoints

```bash
# Test HTTP health
curl -s http://<new-ip>:<port>/health

# Verify tool count via MCP
curl -s http://<new-ip>:<port>/mcp -X POST \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Tools: {len(d[\"result\"][\"tools\"])}')"
```

## Pitfalls

- **pg17 dump has `\restrict <token>` commands**: These are pg17 security metadata. psql -f handles them fine when connected to the specific database. If they error, they're usually non-fatal — data still imports. Only a problem if piping via stdin instead of psql -f.
- **Building on Pi takes 10-15 minutes**: torch, transformers, numpy, scikit-learn all compile or download large wheels. Always use background mode with notify_on_complete. Do NOT use foreground mode with default timeout.
- **Docker compose `name:` field changes image naming**: With `name: nexus`, images become `nexus-nexus-api:latest` (hyphen between project name and service name), NOT `nexus_nexus-api:latest` (underscore). Manually tag if `docker compose build` names them differently.
- **Port conflicts from old containers**: Check for stale containers from previous compose runs (`docker ps -a`), not just running ones. Old containers may hold the port even if shown as "Exited".
- **NEXUS_DISABLE_AUTH=true requires ENVIRONMENT=development**: Some apps have a safety gate that refuses auth-disabled mode in production. Set `ENVIRONMENT=development` in the target's .env.
- **SSH shell doesn't source .bashrc or .profile**: Always export PATH explicitly in SSH commands: `export PATH=$HOME/.local/bin:$PATH && <command>`.
- **Rsync excludes are critical**: Always exclude `.git/` (fast), `data/postgres/` (separate dump), `data/redis/` (cached, ephemeral) to avoid copying gigabytes of binary DB files that can corrupt across architectures.
- **Bind mount vs copy for app code**: On the source, the compose uses `.:/app:ro` (bind mount). On target, this also works — but ensure the target path exists before first `up`. The `build: .` must run first to populate the image.

## Verification checklist

- [ ] Target architecture confirmed
- [ ] Target Docker + Compose version checked
- [ ] GPU-dependent services stripped from target compose
- [ ] All remaining images support target arch (multi-arch)
- [ ] .env adjusted for arch differences (mind models, env vars)
- [ ] Data successfully dumped from source
- [ ] Data successfully imported on target (count verified)
- [ ] All containers healthy on target
- [ ] HTTP/MCP endpoints responding
- [ ] Source stack stopped
- [ ] Client configs updated to new IP
