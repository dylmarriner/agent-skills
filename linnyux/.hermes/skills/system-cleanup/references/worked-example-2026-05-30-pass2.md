# Worked Example: Second Pass — 92% → 89%, +6G from Deep Hidden Hogs

**Date**: 2026-05-30 (second pass, same session)  
**Starting state**: 92% full (18G free)  
**Ending state**: 89% full (24G free)  
**Recovered**: ~6G more

The user asked "can you clear more space" after the first pass. This pass found targets that are not immediately obvious — the kind an agent that hasn't learned them yet will miss.

## Targets Found

### 1. Snapd Blob Cache — 5.4G

**Location**: `/var/lib/snapd/cache/`

This is **not** the snap installation data — it's cached snap package blobs. Snaps re-download them on refresh. There is no built-in cleanup command like `apt clean`. Files are named by SHA hash, 50MB-600MB each.

```bash
# Check size first
sudo du -sh /var/lib/snapd/cache/
# Clean safely
sudo find /var/lib/snapd/cache/ -type f -delete
```

**Why it was missed in pass 1**: The initial `du -sh /var/cache` only showed 1.1G, missing `/var/lib/snapd/cache/` because snapd cache lives under `/var/lib/`, not `/var/cache/`.

### 2. uv Local Share Store — ~992M

**Location**: `~/.local/share/uv/`

The `uv cache clean` command (pass 1) cleaned `~/.cache/uv/archive-v0` (13G), but uv also maintains a separate virtual environment store at `~/.local/share/uv/` that can hold another ~1G.

```bash
rm -rf ~/.local/share/uv
```

### 3. Hidden Application Installs — IDA Free 9.3 (556M)

**Location**: `~/.local/share/applications/IDA Free 9.3/`

`.local/share/applications/` is normally a directory of small `.desktop` shortcut files. But some applications (IDA Free, some Electron apps) install their entire binary tree there. The `du -sh` on this directory won't flag it as unusual unless you check for subdirectories specifically.

```bash
# The test that caught it:
du -sh ~/.local/share/applications/*/ 2>/dev/null | sort -rh | head -5
```

In this session, IDA Free was an actual installed disassembler, not cache — so it was left in place. But this pattern is worth knowing because a stale/broken app install in this location could be 500M+ of dead weight.

### 4. Multi-Python Version Site-Packages — 400-500M each

**Check**:
```bash
sudo du -sh ~/.local/lib/python3.*/ 2>/dev/null | sort -rh | head -5
```

On this system: both python3.12 (471M) and python3.13 (456M) site-packages existed. The system default was python3.12. The python3.13 packages (PyQt5, sympy, etc.) came from pipx/uv installs. We left them to avoid breaking pipx tools.

### 5. Cached ZIPs in Tool Directories — ~338M

Check for large `.zip` files that are cached installers left behind after extraction:

```bash
find ~/.vscode ~/android-studio ~/Downloads -name '*.zip' -size +50M -exec ls -lh {} \;
```

Recovered:
- `cloudcode_cli.zip` (191M) — VS Code Gemini extension cached installer
- `cmdline-tools.zip` (147M) — Android SDK command line tools cached installer

### 6. Stuck Snap Auto-Refresh Blocking `snap remove`

**Problem**: `snap remove cups` and `snap remove firefox` failed with "snap has auto-refresh change in progress". The disabled snaps (cups, firefox) were stuck because `snap changes` showed change #97 in "Abort" status with operations stuck in "Abort" → "Hold".

```bash
snap changes           # see stuck change
snap change 97         # see operation details
snap abort 97          # may not work if already in Abort state
```

**Workaround tested**: `sudo systemctl restart snapd` timed out. The snapd blob cache could still be independently cleaned. `sudo systemctl reset-failed snapd.failure.service` cleared the failure unit. The actual snap removal required either a successful daemon restart or a system reboot.

### 7. Systemd Failure Service from Snapd

After the stuck snap operation, `systemctl --failed` showed:
```
● snapd.failure.service    loaded failed failed Failure handling of the snapd snap
```

Fix:
```bash
sudo systemctl reset-failed snapd.failure.service
```

## Lessons for Future Passes

1. **Snapd cache is invisible to `du /var/cache`** — must check `/var/lib/snapd/cache/` explicitly, or at minimum include `/var/lib` in the initial scan.
2. **uv has TWO stores** — cache (`~/.cache/uv/archive-v0`) is the big one (13G), but the virtual env store (`~/.local/share/uv/`) adds another ~1G.
3. **`.local/share/applications/` is not just .desktop files** — treat any subdirectory >10M as TIER 3 and investigate.
4. **Docker volume prune won't clean volumes tied to a docker-compose project** — volumes referenced by a compose file in any directory on disk persist. Need `docker compose down -v` in the project's dir for full cleanup.
5. **Multi-Python version creep** — pipx and uv can install packages under non-default Python versions, each accumulating 400-500M. Worth checking if the non-default version can be pruned.
