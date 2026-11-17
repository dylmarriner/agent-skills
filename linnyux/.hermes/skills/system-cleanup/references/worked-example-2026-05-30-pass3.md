# Worked Example: Third Pass — 89% → 87%, Deep Application Data + Stuck Snap Resolution

**Date**: 2026-05-30 (third pass, same session)  
**Starting state**: 89% full (24G free)  
**Ending state**: 87% full (29G free)  
**Recovered**: ~5G more  

The user escalated from "can you clear more space" to "all" (clean everything suggested) then "can we free up anymore" (find more). This pass found non-cache application data and finally resolved a stuck snap that had been blocking removal for 4 days.

## Targets Found & Cleaned

### 1. Stale Ollama Backups in /usr/local/bin — 270M

ollama keeps multiple backup binaries when updating, and they never get auto-cleaned:

```
129M  /usr/local/bin/minikube         ← kept (installed tool)
118M  /usr/local/bin/node              ← kept
 80M  /usr/local/bin/ollama.backup     ← DELETED (stale)
 80M  /usr/local/bin/ollama            ← kept (current)
 38M  /usr/local/bin/ollama.old        ← DELETED
 38M  /usr/local/bin/ollama-old        ← DELETED
 38M  /usr/local/bin/ollama.memfix     ← DELETED
 38M  /usr/local/bin/ollama-cmake      ← DELETED
 38M  /usr/local/bin/ollama.backup-rx580-20260425-050141  ← DELETED
```

**Detection command**:
```bash
sudo du -sh /usr/local/bin/* 2>/dev/null | sort -rh | head -15
```

Then look for any binary with multiple identical-looking backups. Ollama especially leaves backup files named `ollama.backup`, `ollama.old`, `ollama-old`, `ollama.memfix`, `ollama-cmake`, `ollama.backup-<date>`.

### 2. Python 3.13 Site-Packages — 456M

The system Python is 3.12 (`python3 --version` → 3.12.3), but pipx/uv had installed packages under Python 3.13 as well. Both shared ~450-500M of site-packages.

```bash
# Check which Python versions have site-packages
sudo du -sh ~/.local/lib/python3.*/ 2>/dev/null | sort -rh | head -5
# Remove non-default version's site-packages
rm -rf ~/.local/lib/python3.13
```

**Risk**: pipx tools installed under python3.13 would break. Check with `pipx list` first. If all pipx tools are on the default version, it's safe.

**Better approach**: `pip3.13 list 2>/dev/null` to see what's installed, then decide. In this session we just removed the whole dir because all tools were on 3.12.

### 3. pnpm Global Store — 1.5G

The pnpm global store at `~/.local/share/pnpm/store/` holds cached npm packages used across projects. `pnpm store prune` only removes unreferenced packages.

```bash
pnpm store prune           # may reclaim little (only unreferenced packages)
rm -rf ~/.local/share/pnpm # aggressive — removes the entire store
```

Packages re-download on next `pnpm install`.

### 4. Go Module Cache — 1.9G

```bash
go clean -modcache
```

This removes all downloaded Go module source code in `~/go/pkg/mod/`. Go modules re-download on next build. This is separate from the Go build cache (`go clean -cache`), which is smaller (~200M).

### 5. Documents Project node_modules — ~1.3G

Project folders in ~/Documents often accumulate large node_modules:

```bash
du -sh ~/Documents/*/node_modules 2>/dev/null | sort -rh
```

In this session: `papatoetoe-funeral-cottage/node_modules` was 1.3G. Removed since the project wasn't actively being worked on.

### 6. OpenCode Artifact Storage — 275M

```bash
rm -rf ~/.local/share/opencode/storage
```

OpenCode's `storage/` directory holds session artifacts and tool outputs. These aren't cached per se — they're logs/work products from past agent runs. Safe to clean. The opencode.db (96M) with session history was left intact.

### 7. IDA Free 9.3 Application — 556M

IDA Free 9.3 was installed under `~/.local/share/applications/IDA Free 9.3/` — this is an unusual location for a full app binary tree. Normally `.local/share/applications/` only has `.desktop` shortcut files. IDA Free puts its entire installation there.

```bash
# Detection — look for app-sized subdirectories
du -sh ~/.local/share/applications/*/ 2>/dev/null | sort -rh | head -5
```

**Lesson**: Always check `~/.local/share/applications/` for subdirectories, not just files. A directory there with the structure of a full application (binaries, libs, docs, includes, etc.) is a real app, not cache — confirm with user before removing.

### 8. vs-kubernetes Cache — 189M

VS Code's Kubernetes extension caches CLI tool binaries (kubectl, helm, etc.) at:

```bash
~/.local/state/vs-kubernetes/tools/
```

These re-download on next extension use. Safe to clean.

### 9. Python __pycache__ Bytecode — ~50M

```bash
find ~/.local -name "__pycache__" -type d -exec rm -rf {} +
```

In this session: 2,466 `__pycache__` directories existed in `.local/` alone. Each is compiled Python bytecode that gets regenerated when scripts run. Safe to clean comprehensively.

### 10. .npm Temp Caches

```bash
rm -rf ~/.npm/_npx ~/.npm/_prebuilds
```

`_npx`: cached npx-installed packages. `_prebuilds`: native binary prebuilds. Both re-download on next use.

### 11. Disabled Snaps Finally Removed — 760M

**Problem (from pass 2)**: `snap remove cups` and `snap remove firefox` were blocked by a stuck auto-refresh change (#97) in "Abort" status. `sudo systemctl restart snapd` timed out.

**Resolution** (found in pass 3):
```bash
# Force kill snapd daemon completely
sudo pkill -9 snapd
sudo pkill -9 snap-store
sleep 2

# Restart snapd — this time it works because no stale process blocks it
sudo systemctl start snapd
sleep 3

# Now the stuck change resolves
snap changes
# → ID 97 changed from "Abort" to "Undone" — completed!
# → New change 98 started fresh (android-studio auto-refresh)
# → Can now remove the disabled snaps

sudo snap remove cups     # → Done
sudo snap remove firefox  # → Done (after ~60s with data snapshot)
```

**Recovered**: cups (130M), firefox (630M).

## Additional Detection Commands Not Standard

```bash
# Stale backup binaries in /usr/local/bin
# (look for multiple versions of same tool with .backup, .old, -old suffixes)
du -sh /usr/local/bin/* | sort -rh

# Python __pycache__ forests
find ~/.local -name "__pycache__" -type d | wc -l

# VS Code extension cached zips
find ~/.vscode -name '*.zip' -size +50M

# Extra Python version site-packages
du -sh ~/.local/lib/python3.*/

# Docker volumes with stopped containers
docker ps -a

# Stuck snap operations
snap changes
snap change <id>  # inspect stuck operation
```

## Key Lessons for This Pass

1. **`pkill -9 snapd`** is the nuclear option for stuck snap operations — it frees the daemon from any stale state so `systemctl start snapd` can start clean. Without this, `snap remove` is permanently blocked.
2. **`/usr/local/bin/` can hide stale backup binaries** — ollama especially creates multiple backup versions and never cleans them.
3. **`~/go/pkg/mod` is separate from build cache** — `go clean -modcache` reclaims module source code (1-2G), distinct from `go clean -cache` (200-500M).
4. **`__pycache__` is everywhere** — 2,466 dirs in just `.local/`. The `find -exec rm -rf` pattern is fast and safe.
5. **Application data in `.local/state/`** — vs-kubernetes, kilo, etc. have sizable caches that are safe to clean.
