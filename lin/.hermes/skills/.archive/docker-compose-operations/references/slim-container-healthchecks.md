# Slim Container Health Checks

Slim Docker images (`python:*-slim-bookworm`, `python:alpine`, `node:alpine`) lack common process tools (`ps`, `pgrep`, `procps`). The `/proc/1/cmdline` Python trick is the most portable workaround.

## Available Tools by Image

| Image | Has `ps`? | Has `pgrep`? | Has Python? | Has `cat`/`ls`? |
|---|---|---|---|---|
| `python:*-slim-bookworm` | NO | NO | YES | YES |
| `python:*-alpine` | via busybox | NO | YES | YES |
| `node:*-alpine` | via busybox | NO | NO | YES |
| `ubuntu:*-latest` | YES | NO | NO | YES |

## Alternatives When Python Isn't Available

When the container has no Python (e.g. Node Alpine), use:

```yaml
healthcheck:
  test: ["CMD-SHELL", "cat /proc/1/cmdline | grep -q 'expected' || exit 1"]
  interval: 30s
  timeout: 10s
  start_period: 15s
  retries: 3
```

Or for Node.js containers specifically:

```yaml
healthcheck:
  test: ["CMD-SHELL", "node -e \"process.exit(0)\""]
```

## Docker Healthcheck Priority

1. Compose-level `healthcheck:` overrides Dockerfile `HEALTHCHECK` entirely
2. Dockerfile `HEALTHCHECK` is only used if compose doesn't specify one
3. `CMD-SHELL` runs the command via the container's shell (`/bin/sh`)
4. Exit code 0 = healthy, 1+ = unhealthy
