# Cascade Failure Diagnostics for Docker Compose Stacks

When a Docker Compose stack locks up a machine, the root cause is often a dead upstream service causing downstream thrash. Here's how to identify and break the cycle.

## The Honcho Cascade (Real-World Example)

**Scenario**: Honcho API exited → deriver couldn't connect → deriver entered crash-restart loop → CPU pinned → Docker health checks timed out → containerd itself stopped responding → system frozen → user held power button.

### Timeline of a Cascade

```
T+0m   API container exits (process crash, OOM, etc.)
T+1m   Deriver health check fails — can't reach API at localhost:8000/health
T+2m   Deriver restarts — still can't connect, loop begins
T+5m   Docker health checks on ALL containers start timing out
       (no CPU left to run the health check processes)
T+7m   rtkit-daemon: "The canary thread is apparently starving. Taking action."
       (KERNEL-LEVEL SIGNAL — the real-time scheduler itself can't get CPU)
T+8m   containerd: "context deadline exceeded"
       (container runtime timing out — the daemon managing your containers)
T+9m   dockerd: "copy stream failed" / "reading from a closed fifo"
       (Docker daemon losing streams — containers in zombie state)
T+10m  System UI unresponsive, power button hold required
```

### Smoking Guns (Check These First)

| Log Message | Meaning |
|---|---|
| `rtkit-daemon: The canary thread is apparently starving. Taking action.` | **Complete CPU exhaustion.** The real-time scheduling watchdog can't run. The system is fully saturated — nothing is getting CPU time. |
| `containerd: "context deadline exceeded"` | Container runtime timing out — it's so overloaded it can't even check container states. |
| `dockerd: "copy stream failed"` / `"reading from a closed fifo"` | Docker daemon is losing its I/O streams to containers. They're effectively zombies. |
| `Docker health check timed out starting` for ALL containers | Not just one container failing — the entire health check subsystem is starved. This means system-wide saturation, not a single-service issue. |
| `rtkit-daemon: Demoting known real-time threads.` | The system is so backed up it's demoting RT priority threads to try to recover. This happens right after the canary starvation. |

### How to Check

```bash
# Previous boot's logs
journalctl -b -1 --no-pager -p err -p crit 2>/dev/null | head -40

# Check for rtkit starvation
journalctl -b -1 --no-pager 2>/dev/null | grep -i 'canary thread.*starving'

# Check for containerd timeouts
journalctl -b -1 --no-pager 2>/dev/null | grep -i 'context deadline exceeded'

# Check for Docker stream failures
journalctl -b -1 --no-pager 2>/dev/null | grep -i 'copy stream failed'
```

### Breaking the Cycle

1. **Fix the root cause** — Usually a port conflict, config error, or dead upstream service
2. **Add `depends_on` conditions** so downstream services wait for upstream to be healthy first
3. **Add per-service healthchecks** specific to each service (not a shared Dockerfile healthcheck)
4. **Deploy a watchdog** — no-agent cron script that catches and restarts unhealthy containers quickly (see the watchdog template)

## Key Principles

1. **Unhealthy containers don't just affect themselves** — Docker Compose health checks consume resources on every tick. Multiple unhealthy containers compound.
2. **containerd timeouts are the last warning** — if the container runtime itself is timing out, a hard reset is imminent.
3. **rtkit canary starvation is the absolute last signal** — if you see this in logs, the system was seconds from being unrecoverable without a power button hold.
4. **Health check failures cascade UP the chain** — a crashed API makes the deriver unhealthy makes the database/redis appear unhealthy when they're actually fine.
