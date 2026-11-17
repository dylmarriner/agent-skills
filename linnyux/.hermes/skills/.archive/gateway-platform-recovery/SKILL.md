---
name: gateway-platform-recovery
description: Recover from Hermes gateway platform adapter failures — stale messaging session locks, platform-specific reconnection procedures, and cron DB corruption that compounds gateway symptoms.
---

# Gateway Platform Recovery

Diagnose and recover when a Hermes gateway platform adapter (Telegram, Discord, Slack, etc.) fails to connect or has permanently parked due to exhausted retries.

## When to Use

- User says "Telegram/Discord/etc. isn't working" or "messages aren't getting through"
- `hermes gateway status` shows platform-specific failure messages
- Gateway starts but a particular platform shows no activity
- `hermes gateway restart` hangs or times out
- Gateway logs show repeated platform connection retries followed by permanent parking

## Common Failure: Stale Session Lock

**Signal:** `hermes gateway status` output includes:

```
⚠ telegram: Telegram polling could not recover after 5 retries (200s total wait). The previous gateway session is still held open on Telegram's servers...
```

**Cause:** Most messaging platforms (Telegram especially) allow only ONE active polling connection per bot token. When the gateway restarts without cleanly closing the previous connection, the old session remains held open on the platform's servers. The new gateway process's connection attempt is rejected.

**Recovery (kill → wait → start):**

```bash
# 1. Find the gateway PID
systemctl --user status hermes-gateway  # shows Main PID

# 2. Kill it hard (systemctl stop may hang)
kill <PID>
sleep 2
kill -0 <PID> 2>/dev/null && kill -9 <PID>

# 3. Wait for platform to release the session
sleep 5

# 4. Start fresh
systemctl --user start hermes-gateway

# 5. Verify after 15-20 seconds
sleep 15
hermes gateway status
```

The sleep after kill is important — the platform's server needs time to detect the dropped connection before it accepts a new one.

**Root cause:** The gateway process didn't close the polling connection cleanly on shutdown. This can happen when:
- The process received SIGKILL (e.g., OOM killer) instead of SIGTERM
- The previous session was from a different Hermes/OpenClaw instance sharing the same bot token
- `systemctl --user stop` timed out waiting for graceful shutdown

## Secondary Signal: Cron Executions DB Corruption

**Signal:** Gateway logs show `sqlite3.DatabaseError: database disk image is malformed` with a stack trace from `cron/executions.py`.

**Relevance:** A corrupted cron executions DB can compound gateway issues — cron job failures may appear as gateway platform problems because the gateway logs both types of errors.

**Recovery:**

```bash
# Locate, backup, and recreate:
find ~/.hermes -name "*.db" -path "*/cron/*"
cp <db_path> <db_path>.corrupted
rm <db_path>
# Gateway will recreate it on restart
systemctl --user restart hermes-gateway
```

## `hermes gateway restart` Hangs

If `hermes gateway restart` or `systemctl --user stop` hangs indefinitely:

1. Don't wait — it's not going to recover
2. Interrupt with Ctrl+C and use the kill → wait → start pattern above
3. The hang is usually caused by the Telegram polling thread blocking on a network call that never completes

## Verification

After recovery, confirm the platform reconnected by checking:
1. `hermes gateway status` — should show no platform-specific failure indicators
2. Gateway logs at `/home/lin/.hermes/logs/gateway.log` — check for `set_my_commands OK` (Telegram) or similar platform-specific "connected" messages
3. Send a test message from the affected platform
