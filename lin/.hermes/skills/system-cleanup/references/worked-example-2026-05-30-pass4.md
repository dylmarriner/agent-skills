# Worked Example: Fourth Pass — 87% → 77%, Paperclip Runtime Data Avalanche

**Date**: 2026-05-30 (fourth pass, same session)  
**Starting state**: 87% full (29G free)  
**Ending state**: 77% full (49G free)  
**Recovered**: ~20G

The user said "what about the other big folders" and specifically called out a 39G paperclip folder. This pass uncovered the paperclip runtime data directory as the single biggest remaining space hog, with explosive backup accumulation, unbounded logs, stale source node_modules, and workspace artifacts.

## Targets Found & Cleaned

### 1. Paperclip Backups Avalanche — 18G → 1.2G

`~/.paperclip/instances/default/data/backups/` contained **165 database backups** totaling **18G**. The most recent uncompressed backup alone was 912M. Backups were being taken every 30-60 minutes and never pruned.

```bash
# Detection
du -sh ~/.paperclip/instances/default/data/backups/      # → 18G
ls ~/.paperclip/instances/default/data/backups/ | wc -l  # → 165 files

# Age distribution
ls -lt ~/.paperclip/instances/default/data/backups/ | head -20
ls ~/.paperclip/instances/default/data/backups/ | tail -20

# Prune — keep 3 most recent
cd ~/.paperclip/instances/default/data/backups
ls -t | tail -n +4 | xargs rm -f
```

**Key insight**: Paperclip's backup system has no retention policy. It creates hourly+ backups indefinitely. A future session should check this first when disk is full and paperclip is running.

### 2. Paperclip Server Log — 567M → 50M

`~/.paperclip/instances/default/logs/server.log` had grown to 567M with no log rotation.

```bash
tail -c 50M server.log > /tmp/server.log.tail && mv /tmp/server.log.tail server.log
```

The log was actively being written to (paperclip server was running from the DEVELOPMENT1 drive). Tail-truncation is safe while the server is running because the file handle persists — the server keeps writing to the inode even after the file is replaced.

**Key insight**: Paperclip doesn't rotate its server.log. Manually truncate with `tail -c 50M` to keep recent context without the full history.

### 3. Paperclip Run Logs — 405M → 6.3M

`~/.paperclip/instances/default/data/run-logs/` contained old agent execution run logs per company UUID. Some dated back weeks.

```bash
cd ~/.paperclip/instances/default/data/run-logs
ls -t | tail -n +4 | while read d; do rm -rf "$d"; done
```

Kept the 3 most recent company run dirs.

### 4. Stale Paperclip Source Clone — 3.1G (node_modules)

There were two paperclip clones:
- `/home/kubuntux/paperclip/` — on root filesystem (stale)
- `/media/kubuntux/DEVELOPMENT1/paperclip/` — on secondary drive (active, running)

The active server was running from the DEVELOPMENT1 clone. The root clone's node_modules (3.1G) were completely unused.

```bash
# Detection — check which clone is running
ps aux | grep -i paperclip | grep -v grep
# → process paths show /media/kubuntux/DEVELOPMENT1/paperclip/

# Check both clones
git -C /home/kubuntux/paperclip remote -v
git -C /media/kubuntux/DEVELOPMENT1/paperclip remote -v
# → Both point to same remotes — root clone is stale

# Clean
rm -rf /home/kubuntux/paperclip/node_modules   # keep source files, just drop deps
```

### 5. Paperclip Workspace node_modules — 858M

`~/.paperclip/workspace/Automation-suite/node_modules` held npm dependencies from a workspace checkout. Not actively needed.

```bash
rm -rf ~/.paperclip/workspace/Automation-suite/node_modules
```

### Total Paperclip Recovery

| Target | Before | After | Gain |
|--------|--------|-------|------|
| `.paperclip/.../backups/` | 18G | 1.2G | 16.8G |
| `server.log` | 567M | 50M | 517M |
| `run-logs/` | 405M | 6.3M | 399M |
| `~/paperclip/node_modules` | 3.1G | 0 | 3.1G |
| `.paperclip/workspace/node_modules` | 858M | 0 | 858M |
| **Total** | ~23G | ~1.3G | **~21.7G** |

## Detection Commands for Paperclip-Specific Cleanup

```bash
# Find paperclip runtime data
du -sh ~/.paperclip
du -sh ~/.paperclip/instances/default/*/   # see instances breakdown

# Check if paperclip is running from primary or secondary drive
ps aux | grep -i paperclip | grep -v grep | head -3

# Backup avalanche
ls ~/.paperclip/instances/default/data/backups/ | wc -l

# Log bloat
ls -lh ~/.paperclip/instances/default/logs/server.log

# Run logs age
ls -lt ~/.paperclip/instances/default/data/run-logs/

# Stale clone detection (same repo on two drives)
find /home -maxdepth 3 -name paperclip -type d 2>/dev/null
find /media -maxdepth 3 -name paperclip -type d 2>/dev/null
```

## Key Lessons for This Pass

1. **Paperclip runtime data is the single biggest non-cache space hog** — backup avalanche alone can be 18G+ on a system running paperclip for a few weeks.
2. **Check which drive the running service uses** — if the active process lives on the secondary drive, the root clone is stale and its node_modules can go.
3. **Paperclip creates workspace checkouts with their own node_modules** — check `~/.paperclip/workspace/*/node_modules`.
4. **Always check `.paperclip` dir size early** — it's hidden from standard `du -sh ~/*` commands and can silently consume 24G+ without being obvious.
5. **Log truncation with `tail -c` is safe on actively-written files** — the file handle remains valid after the file is swap-moved.
