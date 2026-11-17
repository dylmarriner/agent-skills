# Honcho Stack Recovery — Worked Example

This documents a real recovery of the Honcho memory stack (FastAPI + Postgres + Redis + background worker) on a Kubuntu machine. All the patterns in the main skill combined into one fix.

## Problem

System froze after Honcho API exited → deriver kept hammering health checks → CPU pinned → rtkit canary starved → power button hold required.

## Root Causes Found

| Issue | Fix |
|---|---|
| **Port conflict** — Portainer bound `0.0.0.0:8000`, Honcho API declared `127.0.0.1:8000`. Can't coexist — docker-proxy occupies port 8000 on ALL interfaces. | Changed API port to `127.0.0.1:8001:8000` |
| **Wrong healthcheck on deriver** — Shared Dockerfile HEALTHCHECK hits `localhost:8000/health` which only the API runs. Deriver is a background worker — no HTTP server. | Overrode with proc-based check reading `/proc/1/cmdline` for `src.deriver` |
| **Missing depends_on** — Deriver started before API, immediately failing health checks and entering crash loop. | Added `api: condition: service_started` to deriver's depends_on |

## Port Conflict Resolution

```yaml
# BEFORE — conflicted with Portainer on 0.0.0.0:8000
services:
  api:
    ports:
      - "127.0.0.1:8000:8000"

# AFTER — moved to 8001
services:
  api:
    ports:
      - "127.0.0.1:8001:8000"
```

## Healthcheck Override (Compose-Level)

The Dockerfile's `HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` works for the API but NOT for the deriver (no HTTP server).

```yaml
services:
  deriver:
    build: .
    entrypoint: ["/app/.venv/bin/python", "-m", "src.deriver"]
    healthcheck:
      test: ["CMD-SHELL", "python -c \"exit(0 if 'src.deriver' in open('/proc/1/cmdline').read() else 1)\""]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

## Dependency Ordering

```yaml
services:
  deriver:
    depends_on:
      api:                # ← ADDED this dependency
        condition: service_started
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
```

## Watchdog Deployment

Concrete script based on the template, deployed as no-agent cron:

```bash
#!/bin/bash
COMPOSE_DIR="/home/lin/honcho"
cd "$COMPOSE_DIR" || exit 1

UNHEALTHY=$(docker compose ps --format '{{.Name}} {{.Status}}' | grep -i 'unhealthy' | awk '{print $1}')
EXITED=$(docker compose ps --format '{{.Name}} {{.Status}}' | grep -i 'exited' | awk '{print $1}')

MESSAGES=""
for c in $UNHEALTHY; do
    docker compose up -d --no-deps "${c%%-1}"
    MESSAGES="$MESSAGES restarted-unhealthy:$c"
done
for c in $EXITED; do
    docker compose up -d --no-deps "${c%%-1}"
    MESSAGES="$MESSAGES restarted-exited:$c"
done

for svc in api database deriver redis; do
    STATUS=$(docker compose ps --format '{{.Name}} {{.Status}}' | grep "honcho-${svc}-1")
    echo "$STATUS" | grep -qiE '(exited|unhealthy)' && MESSAGES="$MESSAGES still-broken:$svc"
done

if [ -n "$MESSAGES" ]; then
    echo "$(date) $MESSAGES"
    echo "$MESSAGES" | grep -q 'still-broken\|missing' && docker compose down && docker compose up -d
    exit 1
fi
exit 0
```

Scheduled with: `cronjob(action='create', name='honcho-watchdog', schedule='every 1m', script='honcho-watchdog.sh', no_agent=True, deliver='local')`

## Verification Commands

```bash
# Check all containers healthy
docker compose ps

# Inspect health check history
docker inspect honcho-deriver-1 --format '{{range .State.Health.Log}}{{.Output}}{{"\n---\n"}}{{end}}'

# Check container network attachment (was API on the compose network?)
docker inspect honcho-api-1 --format '{{json .NetworkSettings.Networks}}'

# Check if port is occupied
sudo ss -tlnp | grep 8000
```
