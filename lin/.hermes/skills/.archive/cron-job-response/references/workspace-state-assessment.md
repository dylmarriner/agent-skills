# Workspace State Assessment for Cron/Headless Jobs

When a cron job or scheduled tick runs, the agent must autonomously assess workspace
state. There is no user to clarify with. Use this multi-source probe pattern.

## The Four-Probe Pattern

```
1. CONFIG  → What components are supposed to exist?
2. GIT     → What changed since last session?
3. FILES   → What's the current content of state documents?
4. SERVICES→ What infrastructure is reachable?
```

## 1. Config Probe

Check the runtime config for hints about what's wired up:

```bash
grep -i 'cron\|subconscious\|heartbeat\|scheduled' ~/.hermes/config.yaml
```

Look for:
- `cron:` section — list of registered cron jobs
- `auto_decompose_per_tick` — whether auto-decomposition is on
- Any `heartbeat` or `interval` keys

## 2. Git Probe (workspace)

```bash
cd ~/.openclaw/workspace && git status --short    # untracked + modified
git diff HEAD --stat                               # tracked-only changes
git log --oneline -5 --all                         # recent activity
git stash list                                     # stashed work
```

**Key distinction**: Untracked files (`??`) are usually init artifacts. Modified
tracked files (`M`) are real workspace drift — worth investigating.

## 3. File Probe

Read the canonical state files in order:

```
1. HEARTBEAT.md        — Explicit tasks OR comments-only = skip
2. memory/YYYY-MM-DD.md— Today's session log
3. openclaw-workspace-state.json — Boot timestamp, seed state
```

### HEARTBEAT.md Convention

```
Comments-only content  → No work pending. Reply [SILENT].
Actual content (tasks) → Execute each listed item.
```

Detection: if the file only contains HTML comments (`<!-- ... -->`) or is
effectively empty, treat as "no heartbeat tasks".

### Memory Probe

Check `memory/` directory for the most recent dated file. Also read `MEMORY.md`
for long-term context (project status, active goals, critical facts).

## 4. Service Probe

Check whether backend services are responsive:

- **Synapse Memory**: `synapse_health()` tool or direct HTTP check
- **Nexus Memory**: `mcp__nexus_memory__nexus_status()` tool
- **RAGFlow**: `ragflow_health()` tool
- **CodeGraph**: `mcp__codegraph__codegraph_explore()` for codebase context

## When to Report vs. Stay Silent

| Assessment | Output |
|---|---|
| No git diffs, no heartbeat tasks, services offline | `[SILENT]` |
| Git diffs found, or heartbeat tasks exist, or notable state change | Full report with summary |
| Service down but no pending work | `[SILENT]` — environment state alone isn't news |

## Common Pitfalls

- **Reporting no-change as news**: "No active goals, nothing changed" is `[SILENT]`.
  Only produce a report when there was actual meaningful work or detected change.
- **Assuming module existence**: Never assume a Python module exists because it's
  named in config. Verify `__init__.py` presence before import attempts.
- **Garbage-in timestamps**: File modification times may drift across reboots.
  Use git diff as primary change detector, timestamps as secondary signal.
