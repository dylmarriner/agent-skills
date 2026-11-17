# Paperclip Temp Directory Accumulation

## Problem

Paperclip (and related tooling like OpenCode adapter) creates temporary directories in `/tmp` for every operation and **never cleans them up**. Each directory is named `paperclip-<operation>-<randomId>` and contains ~70 MB of runtime artifacts.

Over a development session spanning days to weeks, **hundreds** of these accumulate — 508 observed in one case, totaling over 35 GB.

## Directory Types

| Pattern | Typical Size | Content |
|---------|-------------|---------|
| `paperclip-vitest-*` | 137 MB each | Test runner workspaces |
| `paperclip-heartbeat-*` | 70-74 MB each | Heartbeat recovery, stale queue, etc. |
| `paperclip-workspace-runtime-*` | 70 MB each | Workspace runtime snapshots |
| `paperclip-routines-service-*` | 70 MB each | Routines service state |
| `paperclip-issues-*` | 69-70 MB each | Issue create / recovery / service state |
| `paperclip-opencode-config-*` | 58 MB each | OpenCode config copies with node_modules |
| `paperclip-feedback-service-*` | 70 MB each | Feedback service state |
| `paperclip-worktree-repo-*` | Variable | Git worktree clones (adds up fast) |
| `paperclip-worktree-ports-*` | Variable | Port allocation state |

Each directory typically contains a small PostgreSQL data directory (with `pg_wal`), temporary files, npm modules, and config copies.

## Cleanup

```bash
# Count them first
sudo find /tmp -maxdepth 1 -name 'paperclip-*' -type d | wc -l

# Show their total footprint
sudo du -sch /tmp/paperclip-* 2>/dev/null | tail -1

# Delete all stale Paperclip temp dirs
sudo find /tmp -maxdepth 1 -name 'paperclip-*' -type d -exec rm -rf {} +
```

## Considerations

- These are safe to delete even while Paperclip is running — the active server creates new temp dirs as needed, and the old ones are stale artifacts from past operations
- Check `mtime` if unsure: all Paperclip temp dirs older than 1 day are likely stale
- Actual Paperclip runtime data lives under `~/.paperclip/` — that directory should NOT be touched
- The accumulation rate depends on how heavily Paperclip's features (heartbeat, vitest, routines, issues, opencode config) are exercised
