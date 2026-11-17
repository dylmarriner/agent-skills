# Orphaned OpenCode Agent Cleanup

## When to Use

Paperclip was killed (or crashed) but OpenCode agent processes it spawned are still running. They consume CPU and RAM indefinitely — often for hours or days — until manually cleaned.

## Symptoms

- System feels sluggish or CPU usage is persistently high
- `ps aux | grep "opencode run" | wc -l` returns 5+ (10-15+ on a busy board)
- Each opencode process shows 300-630MB RSS and 20-27% CPU
- Server log at `~/.paperclip/instances/default/logs/server.log` shows no recent agent activity (processes survived the server)

## Process Tree Anatomy

Paperclip spawns agent processes through the opencode adapter. A typical orphaned process looks like:

```
/usr/local/bin/opencode run --format json --model vertex/gemini-3.1-flash-lite-preview
```

Or from the global npm install:

```
/home/kubuntux/.npm-global/lib/node_modules/opencode-ai/bin/.opencode run --format json --session ses_xxx --model ...
```

There can also be a mix of versions if both `opencode` (local install at `/usr/local/bin/opencode`) and the npx-cached opencode coexist.

## Cleanup Procedure

### CRITICAL SAFETY — `pkill -f` pattern dangers

`pkill -f` matches against the **full command line** of every process on the system, not just agent processes. Short patterns like `"pi"`, `"code"`, or `"run"` will match hundreds of critical system services (dbus-daemon, pipewire, mysqld with `--pid-file`, gpu-process, ssh-agent, etc.) and **crash the machine**. NEVER use a pattern shorter than two unique words.

Always verify the pattern with `ps aux | grep` BEFORE running `pkill`:

```bash
# ❌ DANGEROUS — will kill pipewire, dbus-daemon, at-spi, mysql, and more
pkill -f "pi"

# ✅ SAFE — specific to known agent CLI names
pkill -f "opencode run"
pkill -f "codex run"
pkill -f "claude-code"
```

### 1. Dry-run — verify pattern matches only intended processes

Before killing anything, check what `pkill` would match:

```bash
# Dry-run: see what the pattern catches (should only show agents)
ps aux | grep -E "opencode run|codex run|claude-code" | grep -v grep
echo "Target count: $(ps aux | grep -E 'opencode run|codex run|claude-code' | grep -v grep | wc -l)"
```

If any non-agent processes appear in the output, refine the pattern.

Alternatively, use the automated script which has safe patterns built in:

```bash
bash ~/.paperclip/scripts/cleanup-orphaned-agents.sh
```

### 2. Inventory

```bash
# Count all opencode runners
ps aux | grep "opencode run" | grep -v grep | wc -l

# Check their total memory (approximate)
ps aux | grep "opencode run" | grep -v grep | awk '{sum+=$6} END {printf "%.1f GB\n", sum/1024/1024}'

# Check how long they've been running (START column)
ps aux | grep "opencode run" | grep -v grep | awk '{print $9, $11}'
```

### 3. Send SIGTERM (graceful shutdown)

```bash
pkill -f "opencode run"
```

Wait 3-5 seconds for processes to shut down cleanly.

### 4. Kill survivors with SIGKILL

```bash
sleep 3
ps aux | grep "opencode run" | grep -v grep | awk '{print $2}' | xargs -r kill -9
```

### 5. Verify cleanup

```bash
ps aux | grep "opencode run" | grep -v grep | head -3
echo "Survivors: $(ps aux | grep 'opencode run' | grep -v grep | wc -l)"
```

Should be 0 survivors.

### 6. Confirm disk / memory recovered

```bash
df -h /
free -h
```
```

## Prevention

### Agent concurrency limit
The root cause of system overload is the `AGENT_DEFAULT_MAX_CONCURRENT_RUNS` constant in `packages/shared/src/constants.ts`. Upstream sets this to 20 — on a 4C/8T machine with 16GB RAM, even 5 concurrent OpenCode agents (each 300-630MB RAM, 20-27% CPU) can saturate resources. **Reduce to 2** on low-end hardware.

```bash
# Edit: packages/shared/src/constants.ts
# Change: AGENT_DEFAULT_MAX_CONCURRENT_RUNS from 20 to 2
# Then rebuild: pnpm --filter @paperclipai/shared build
```

### Orphaned agents
Orphaned agents are a design consequence of Paperclip spawning long-lived child processes that don't inherit the server's PGID. The only prevention is ensuring Paperclip processes (dev-runner, dev-watch, postgres) are killed cleanly in the right order...

1. Kill the dev-runner/tsx process first (stops spawning new agents)
2. Kill dev-watch chain (stops file watcher)
3. Kill postgres last (no more agents to serve)
4. Then clean up orphaned agents

In practice, step 4 is always needed because the orphaned processes are independent grandchildren of the dev-runner.

## Related

- [OpenCode Model Discovery Timeout](opencode-model-discovery-timeout.md) — when `opencode models` itself fails
- [OpenCode Adapter SQLite Lock Failure](opencode-sqlite-lock-pattern.md) — another opencode process-related failure mode
- `~/.paperclip/scripts/cleanup-orphaned-agents.sh` — automated script with safe, pre-verified kill patterns
