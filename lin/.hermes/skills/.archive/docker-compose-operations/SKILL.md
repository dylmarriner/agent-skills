---
name: docker-compose-operations
category: devops
tags: [docker, compose, healthcheck, watchdog, monitoring, resilience]
description: Covers Docker Compose health check patterns, automatic watchdog scripts, and resilience configuration for keeping stacks healthy. Not about building images — about operating running stacks.
---

# Docker Compose Operations

Patterns for operating Docker Compose stacks in production-like environments — health checks, automatic recovery, and resilience.

## Healthcheck Patterns

### Generic Proc-Based Healthcheck (slim containers)

Slim Docker images (`python:*-slim`, `alpine`) often lack `ps` and `pgrep`. Use Python reading `/proc/1/cmdline` instead:

```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"exit(0 if 'expected_process_name' in open('/proc/1/cmdline').read() else 1)\""]
  interval: 30s
  timeout: 10s
  start_period: 15s
  retries: 3
```

Replace `expected_process_name` with a unique substring from the container's entrypoint/command (e.g. `'src.deriver'`, `'uvicorn'`, `'gunicorn'`).

### HTTP Healthcheck

For web services that expose a `/health` endpoint:

```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"]
  interval: 30s
  timeout: 10s
  start_period: 5s
  retries: 3
```

### Database/Redis Healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres -d postgres"]  # PostgreSQL
  test: ["CMD-SHELL", "redis-cli ping"]                         # Redis
  interval: 5s
  timeout: 5s
  retries: 5
```

### Overriding Built-in Dockerfile Healthchecks

When a shared Dockerfile has a healthcheck that only works for some services (common in monorepo stacks), override it in `docker-compose.yml`:

```yaml
services:
  worker:
    build: .
    entrypoint: ["python", "-m", "src.worker"]
    healthcheck:
      test: ["CMD-SHELL", "python -c \"exit(0 if 'worker' in open('/proc/1/cmdline').read() else 1)\""]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

The compose-level healthcheck takes precedence over the Dockerfile's HEALTHCHECK instruction.

## Dependency Ordering

Use `depends_on` with conditions to ensure services start in the right order:

```yaml
services:
  api:
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    depends_on:
      api:
        condition: service_started      # worker needs API running
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
```

## No-Agent Cron Watchdog

For automatic recovery without LLM overhead per tick:

1. Create a bash script at `~/.hermes/scripts/<name>.sh`:

```bash
#!/bin/bash
# Watchdog for <stack-name> Docker Compose stack.
# Silent exit 0 = all healthy. Exit 1 + message = problems.

COMPOSE_DIR="/path/to/compose"
cd "$COMPOSE_DIR" || { echo "ERROR: cannot cd"; exit 1; }

UNHEALTHY=$(docker compose ps --format '{{.Name}} {{.Status}}' | grep -i 'unhealthy' | awk '{print $1}')
EXITED=$(docker compose ps --format '{{.Name}} {{.Status}}' | grep -i 'exited' | awk '{print $1}')

MESSAGES=""
for c in $UNHEALTHY; do
    echo "Restarting unhealthy: $c"
    docker compose up -d --no-deps "${c%%-1}" | tail -1
    MESSAGES="$MESSAGES restarted:$c"
done
for c in $EXITED; do
    echo "Restarting exited: $c"
    docker compose up -d --no-deps "${c%%-1}" | tail -1
    MESSAGES="$MESSAGES restarted:$c"
done

if [ -n "$MESSAGES" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') $MESSAGES"
    exit 1
fi
exit 0
```

2. Schedule as no-agent cron:

```python
cronjob(
    action='create',
    name='<name>-watchdog',
    schedule='every 1m',
    script='<name>.sh',
    no_agent=True,
    deliver='local'  # or omit for in-chat notification on events
)
```

Advantages of no-agent mode:
- Zero token cost per tick when healthy
- Only fires output when something is wrong
- Script can do arbitrary Docker inspection

### Full-Stop Recovery

If a container stays broken after individual restart, the watchdog should escalate:

```bash
# In the watchdog script, after individual restarts:
if echo "$MESSAGES" | grep -q 'still-broken\|missing'; then
    docker compose down && docker compose up -d
fi
```

## Pitfalls

### `--no-deps` Network Isolation

When restarting a single service with `docker compose up -d --no-deps <service>`, the container may **not join the Docker network** if it was created during a previous compose lifecycle (e.g., after a `docker compose down` that destroyed the network).

```bash
# This may produce a container with no network:
docker compose up -d --no-deps api

# Result: inspect shows empty NetworkSettings
docker inspect <container> --format '{{json .NetworkSettings.Networks}}'
# Output: {}
```

The container can't resolve `database` or other service hostnames. **Fix**: always do a full `docker compose down && docker compose up -d` when services were previously stopped. Only use `--no-deps` when the compose stack is already running and the service has an established network.

### Shared Dockerfile Healthcheck on Non-HTTP Services

When a monorepo Dockerfile has a HEALTHCHECK that checks `localhost:8000/health`, it works fine for the API/web service but **always fails** for worker/deriver processes that don't run an HTTP server.

**Fix**: Override the healthcheck in docker-compose.yml per-service. The compose-level healthcheck takes precedence over the Dockerfile's HEALTHCHECK.

### Cascading Unhealthy State

One unhealthy container can make others appear unhealthy due to resource contention. Each health check retry consumes CPU. When multiple containers are failing health checks simultaneously, the system can enter a death spiral. See `references/cascade-failure-diagnostics.md`.

## Troubleshooting

### Diagnosing System-Level Saturation

The rtkit-daemon canary thread is the strongest indicator of complete CPU exhaustion:

```
journalctl -b -1 --no-pager 2>/dev/null | grep 'canary thread.*starving'
```

If this message appears, the real-time scheduler couldn't get CPU — the system was fully saturated and a hard freeze was imminent.

Other saturation signals in journalctl:
- `containerd: context deadline exceeded` — container runtime timing out
- `dockerd: copy stream failed` / `reading from a closed fifo` — Docker losing container I/O
- Multiple simultaneous `Health check timed out` messages across unrelated containers

## Port Conflict Resolution

When a Docker Compose service fails to start with `Bind for 0.0.0.0:XXXX failed: port is already allocated`:

1. Find the occupant: `sudo ss -tlnp | grep <port>`
2. Check if it's another container: `docker ps --format '{{.Names}} {{.Ports}}' | grep <port>`
3. If the occupant should keep the port, **change the victim's port mapping** in docker-compose.yml
4. If the occupant can move, change its port instead

Note that `127.0.0.1:8000:8000` and `0.0.0.0:8000:8000` cannot coexist — docker-proxy binds all addresses per port.

**Real-world example:** Portainer binds `0.0.0.0:8000→8000/tcp`. If another compose service (e.g. a Honcho API) declares `127.0.0.1:8000:8000`, it fails with `Bind for 0.0.0.0:8000 failed: port is already allocated` because docker-proxy from portainer already occupies port 8000 on ALL interfaces. The fix is to map the Honcho API to a different port (`127.0.0.1:8001:8000`) and update any consumers that reference the old port.

## Verification

After changes, verify the stack is healthy:

```bash
docker compose ps
# All services should show "(healthy)" or "(up)"
```

Check health check logs for a specific container:

```bash
docker inspect <container-name> --format '{{range .State.Health.Log}}{{.Output}}{{"\n---\n"}}{{end}}'
```

## Reference Examples

- `references/cascade-failure-diagnostics.md` — How to diagnose a system-level cascade freeze (rtkit starvation, containerd timeouts, death spiral mechanics)
- `references/honcho-stack-recovery.md` — Complete worked example: Honcho memory stack recovery (port conflict, healthcheck override, depends_on fix, watchdog deployment)
- `references/slim-container-healthchecks.md` — Tool availability by base image, alternatives when Python isn't available
- `templates/watchdog.sh` — Reusable bash watchdog template (fill in COMPOSE_DIR, PROJECT_NAME, EXPECTED_SERVICES)
