# OpenCode SQLite "database is locked" Failure

## Symptom

Paperclip run fails with `adapter_failed` (exit code 1) and stderr showing a SQLite stack trace with `database is locked`:

```
Error: database is locked
  at ...
  at #rawNoArgs ...
```

The run transcript shows the OpenCode agent was executing normally (fetching issues, checking git history) then abruptly crashed.

## Root Cause

OpenCode stores session state, tool output history, and conversation data in a global SQLite database at:

```
~/.local/share/opencode/opencode.db
```

This database uses **Better-SQLite3** (WAL mode). When a prior OpenCode process was killed uncleanly or is still running with an open write transaction, WAL/SHM lock files persist:

```
~/.local/share/opencode/opencode.db-wal
~/.local/share/opencode/opencode.db-shm
```

Paperclip spawns OpenCode sessions into temporary directories (`/tmp/paperclip-opencode-config-*`), but they all share this global database. If a stale or concurrent OpenCode process holds a write lock, all subsequent Paperclip adapter runs fail with "database is locked".

## Detection

1. Check running OpenCode processes:
   ```
   ps aux | grep opencode | grep -v grep
   ```

2. Check WAL/SHM lock files:
   ```
   ls -la ~/.local/share/opencode/opencode.db-{wal,shm}
   ```

3. Check the DB file — a large file (200MB+) with WAL/SHM present strongly suggests an unclean shutdown from a prior session.

## Fix

```bash
# 1. Kill stale OpenCode processes
pkill -f "opencode" 2>/dev/null

# 2. Remove stale lock files
rm -f ~/.local/share/opencode/opencode.db-shm ~/.local/share/opencode/opencode.db-wal

# 3. Clean up orphaned Paperclip temp configs
rm -rf /tmp/paperclip-opencode-config-*

# 4. Verify DB is accessible (should not throw error)
sqlite3 ~/.local/share/opencode/opencode.db "SELECT count(*) FROM messages;" 2>/dev/null || echo "DB may still be locked"
```

After cleanup, the next Paperclip adapter invocation should succeed.

## Prevention

- Paperclip should ensure OpenCode sessions exit cleanly (send Ctrl+C or graceful shutdown) before spawning new ones.
- If `paperclipSkillSync` includes `hindsight` or memory MCP plugins, those can trigger concurrent DB writes during initialization — consider disabling MCP/server plugins when running under Paperclip automation.
- Set `maxConcurrentRuns: 1` on the agent's `runtimeConfig.heartbeat` (already done for Cto agent).
