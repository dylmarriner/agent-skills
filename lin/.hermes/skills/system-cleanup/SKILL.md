---
name: system-cleanup
description: "Diagnose and recover disk space on Linux. Use when: (1) user reports drive is full or running low on space, (2) user asks to 'clean up' or 'free up space', (3) user wants to understand what's eating disk space."
---

# System Cleanup

Recover disk space by diagnosing usage, categorizing candidates, and executing a tiered cleanup plan. Always prefer moving user data to secondary drives over deletion unless the user explicitly says otherwise.

## Process

- [ ] **1. Diagnose** — Check current state and identify the drive to clean
- [ ] **2. Find big items** — Locate top space consumers using `du` and `find`
- [ ] **3. Categorize** — Sort findings into safety tiers
- [ ] **4. Confirm** — Present the plan to the user before deleting
- [ ] **5. Execute** — Clean, move, or compress
- [ ] **6. Verify** — Confirm free space increased as expected

For immediate relief while a project backup runs, clean only measured, regenerable caches outside the project tree; report that delta separately. Never remove project files until the backup and remote commit are verified.

## Process-Level Resource Investigation

When the user asks "what's using all my resources" or reports system slowdown, check processes before disk.

### Reference Files

This skill ships with support files for deep-dive scenarios:

- `references/v8-code-cache-cleanup.md` — V8 `.d8b*` code cache files that hide as dotfiles in /tmp
- `references/paperclip-temp-accumulation.md` — Paperclip's unstoppable temp directory generation pattern
- `references/worked-example.md` — Full walkthrough cleaning 99% → 76% in one session
- `references/worked-example-2026-05-30.md` — Full walkthrough cleaning 100% → 92% (18G freed: uv cache, old kernels, paperclip temps, apt/apt source fixes)
- `references/worked-example-2026-05-30-pass2.md` — Second pass: 92% → 89% (snapd cache, uv local share, cached zips, systemd error fixes)
- `references/worked-example-2026-05-30-pass4.md` — Fourth pass: 87% → 77% (paperclip backup avalanche 18G, server log bloat, stale source clone node_modules, workspace artifacts)
- `references/worked-example-2026-07-09.md` — 88% → 79% in one session (21.5G freed: uv cache 6.1G, Chrome AI model 4G, Rust build artifacts 8.1G, Docker 1.4G, old Claude versions, pip cache, Chrome cache)
- `references/worked-example-2026-07-19.md` — 97% → 90% in one session (15G freed: 6.2G CUDA packages on AMD system, 3.9G Rust target, 1.5G old project node_modules, old kernels, Claude/Devin old versions)

### CPU Hogs

```bash
ps aux --sort=-%cpu 2>/dev/null | head -15
# Or fallback:
ps aux 2>/dev/null | sort -k3 -rn | head -15
```

### Memory Hogs

```bash
ps aux --sort=-%mem 2>/dev/null | head -15
# Or fallback:
ps aux 2>/dev/null | sort -k4 -rn | head -15
```

### Common Culprits

| Pattern | Typical Impact | What They Are |
|---------|---------------|---------------|
| `opencode run` | 20-27% CPU, 300-630MB RAM each | AI agent processes — can accumulate to 10-15+ orphans |
| `codex run` | Similar to opencode | Orphaned coding agents left behind after Paperclip shutdown |
| `claude code` | Similar | Anthropic agent runners |
| `litellm` | 0.1% CPU, ~500MB RAM, long-lived | LLM proxy — expected, keep running |
| `hermes chat` | Variable CPU, 100-200MB RAM | Hermes agent sessions — expected while active |
| Chrome renderers | 200-400MB RAM each | Browser tabs — expected but can accumulate |

### Orphaned Agent Cleanup

When Paperclip (or any agent orchestrator) is killed, its spawned AI agent processes survive as orphans. They continue consuming CPU and RAM indefinitely.

**Find them:**
```bash
ps aux | grep -E "opencode run|codex run|claude code" | grep -v grep
```

**Kill them — send SIGTERM first (graceful), then SIGKILL if they survive:**
```bash
pkill -f "opencode run"          # kill all opencode runners
pkill -f "codex"                 # kill all codex runners  
# Or check the count first:
ps aux | grep "opencode run" | grep -v grep | wc -l
```

**Important:** `pkill -f` matches process name anywhere in the command line. Be specific enough to avoid killing your own session. On Hermes CLI, `ps aux | grep -v grep` is safer for inspection; `pkill` is fine for bulk kill once confirmed.

### Syncthing Watching a Live-Write Directory (hidden CPU hog)

Sustained 30-175% CPU with no obvious culprit: check for Syncthing syncing a directory the user's tooling writes to every second (e.g. `~/.hermes`, `~/.config`, a live repo). With `fsWatcherEnabled=true` + short `rescanIntervalS`, every file write triggers a full rescan.

```bash
grep -o '<folder[^>]*>' ~/.local/state/syncthing/config.xml   # find folder paths
K=$(grep -oP '(?<=<apikey>)[^<]*' ~/.local/state/syncthing/config.xml)
curl -s -H "X-API-Key: $K" 'http://127.0.0.1:8384/rest/db/status?folder=<id>'
```

Fix (persistent, keeps sync working):
1. `<folder>/.stignore` — exclude churn dirs (`cache/`, `logs/`, `sessions/`, `installs/`, `.git/`, `node_modules/`) and hot files (`state.db*`, `*.heartbeat`, `*.json` rewritten continuously).
2. In `config.xml` `<options>`: add `hashers=1`, `maxFolderConcurrency=1` (caps CPU), and set `fsWatcherEnabled="false"` + `rescanIntervalS="3600"` on the folder.
3. Also set `natEnabled=false`, `globalAnnounceEnabled=false`, `relaysEnabled=false` if UPnP parse timeouts fill the log.
4. Restart with `systemctl --user restart syncthing`. Verify with a two-sample `/proc/PID/stat` delta — `ps %CPU` is a lifetime average and lies right after a restart.

### Dead Network Mounts Blocking Boot

`systemctl --failed` showing `mnt-*.mount` for CIFS/NFS shares = boot waits on unreachable hosts. Convert them to lazy automounts in `/etc/fstab` (add `nofail,x-systemd.automount,x-systemd.idle-timeout=60,x-systemd.device-timeout=5` to the options field), `sudo systemctl daemon-reload`, `sudo systemctl reset-failed`. Shares still mount on first access; boot stops waiting. Also `sudo systemctl disable <failing>.service` for any unit that can never succeed (e.g. virtualbox.service with missing kernel modules).

### Swap Hogs in a Notification Daemon

`plasma-discover --notifier` (KDE Discover) can sit on 500M+ of zram. `pkill -x plasma-discover` frees it instantly, and `~/.config/autostart/org.kde.discover.notifier.desktop` with `Hidden=true` stops it returning. NOTE: `pkill -f plasma-discover` matches your own shell's command line and kills your session — always `pkill -x`.

### Disk Cleanup After Killing Agents

Killing agent processes often frees 1-3GB of disk immediately (memory-mapped files and temp data). Check with `df -h /` before and after.

### Step 1: Diagnose Disk

```bash
df -h /                                           # Root drive usage
df -h /media/kubuntux/DEVELOPMENT1 2>/dev/null    # Secondary drive
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE | grep -v loop  # All drives
```

**Check for ext4 reserved blocks trap:** `df -h` reports "Avail" (blocks available to unprivileged users), which excludes ext4 reserved blocks (default 5% for root). When the filesystem has many free blocks but df shows 0 available, reserved blocks are consuming all remaining free space. Diagnose with:

```bash
python3 -c "import os; s=os.statvfs('/'); gb=lambda b: b*os.statvfs('/').f_frsize/1024/1024/1024; print(f'Total: {gb(s.f_blocks):.0f}G, Free: {gb(s.f_bfree):.0f}G, Avail: {gb(s.f_bavail):.0f}G, Reserved: {(s.f_bfree-s.f_bavail)*s.f_frsize/1024/1024/1024:.1f}G')"
```

If Reserved is large (e.g. 11G on a 219G drive) and Avail is near zero, fix with:

```bash
# Check current reserved percentage:
sudo tune2fs -l /dev/sdX | grep -E "Reserved block count|Block count"
# Reduce to 1% (leaves ~2G for root on a 200G+ drive):
sudo tune2fs -m 1 /dev/sdX
```

This is safe on any non-system-critical filesystem. For rootfs (/) on a desktop, 1% is plenty — root only needs reserved blocks when the drive is full for emergency `sudo rm` operations, and 1% (2G+) is enough for that. The change is immediate — run `df -h /` again to see freed space.

### Step 2: Find Big Items

**Slow filesystem fallback:** If `du` times out (common on filesystems with millions of small files or slow drives), skip recursive du and use targeted approaches:
- `find / -xdev -type f -size +500M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -30` — finds only the largest files directly, no directory recursion overhead
- `ncdu -x / -o- 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); [print(v[0]['asize']//1024//1024,'MB',v[0]['name']) for v in d[3] if isinstance(v,list) and v[0].get('asize',0)>1048576]"` — ncdu JSON export avoids TTY requirement and is faster than du
- Check known space hog locations individually instead of scanning from root

```bash
# Top-level directories
sudo du -sh /home /var /usr /opt /tmp /snap 2>/dev/null

# Biggest directories in home (visible + hidden)
sudo du -sh /home/kubuntux/* 2>/dev/null | sort -rh | head -20
sudo du -sh /home/kubuntux/.[!.]* 2>/dev/null | sort -rh | head -20

# Also check major hidden runtime data dirs individually
# (.paperclip, .codeium, etc. are hidden but can be 10G+)
for d in /home/kubuntux/.paperclip /home/kubuntux/.codeium /home/kubuntux/.ollama /home/kubuntux/.local; do
  if [ -d "$d" ]; then du -sh "$d" 2>/dev/null; fi
done

# Largest files over 500MB
sudo find /home /var /opt -xdev -type f -size +500M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -30

# Stray large media files in home dir (often overlooked 200M+ videos)
find ~ -maxdepth 2 -type f -size +50M \( -name '*.mp4' -o -name '*.mkv' -o -name '*.mov' \) 2>/dev/null

# Drill down into suspicious directories
sudo du -sh /home/kubuntux/.config/* 2>/dev/null | sort -rh | head -10
sudo du -sh /home/kubuntux/.local/share/* 2>/dev/null | sort -rh | head -20
# .local/share/applications is normally .desktop files only, but
# some apps (IDA Free, Electron) install binaries there — check for
# subdirectories over 10M:
sudo du -sh /home/kubuntux/.local/share/applications/*/ 2>/dev/null | sort -rh | head -5

# Check for multiple python versions in ~/.local/lib — each can be 400-500M
# and one might be unused (e.g. python3.13 if system uses 3.12)
sudo du -sh /home/kubuntux/.local/lib/python3.*/ 2>/dev/null | sort -rh | head -5

# Check for stale source clones — same project on both root and secondary drive
# Active process paths reveal which clone is live
ps aux | grep -E "(paperclip|codex|opencode|hermes)" | grep -v grep | head -5
# Then compare: do repos exist in both /home/kubuntux/<project>/ and /media/.../<project>/?
```

### Step 3: Safety Tiers

**TIER 1 — Always Safe (caches, temp, trash):**  
Before Docker cleanup: if disk is critically low (< 2GB free), Docker daemon itself may hang or timeout on container/image operations. Clean apt cache, journal, logs, and user caches first (this tier), then retry Docker cleanup after space is freed.

| Target | Typical Size | Command |
|--------|-------------|---------|
| `/tmp` | 1-50G | `sudo rm -rf /tmp/* /tmp/.[!.]* 2>/dev/null` — use the two-pass approach after checking what's there (see reference: `references/v8-code-cache-cleanup.md` and `references/paperclip-temp-accumulation.md`) |
| `~/.local/share/Trash` | 100M-1G | `rm -rf ~/.local/share/Trash/*` |
| `~/.cache` | 1-5G | `rm -rf ~/.cache/*` — but prefer targeted tools: `uv cache clean` (see below), `go clean -cache`, `npm cache clean --force`, `pnpm store prune` |
| **uv cache** (archive-v0) | **5-15G** | `uv cache clean` — this is the single biggest cache hit on Hermes/Paperclip systems; archive-v0 alone can be 13G+ |
| **uv local share store** (`~/.local/share/uv`) | **500M-1G** | `rm -rf ~/.local/share/uv` — separate virtual environment store from the cache; can be another ~1G |
| **snapd blob cache** (`/var/lib/snapd/cache/`) | **3-6G** | `sudo find /var/lib/snapd/cache/ -type f -delete` — cached snap package downloads; snaps re-download automatically |
| **Go build cache** | 200-500M | `go clean -cache` — separate from go/pkg/mod; this is the compiler's object cache, safe to clean |
| `~/.npm/_cacache` | 1-5G | `npm cache clean --force` or `rm -rf ~/.npm/_cacache/*` |
| `~/.npm/_npx` | 100M-1G | `rm -rf ~/.npm/_npx/*` |
| `~/.npm/_prebuilds` | 10-100M | `rm -rf ~/.npm/_prebuilds` — prebuilt native binaries, re-download on demand |
| `~/.gradle/caches` | 1-5G | `rm -rf ~/.gradle/caches/*` |
| `~/.local/share/pnpm` (global store) | 1-5G | `pnpm store prune` then `rm -rf ~/.local/share/pnpm/store/*` — note pnpm store path may differ from cache; `pnpm store path` reveals actual location |
| `~/.cache/pnpm` (pnpm cache) | 100-500M | `rm -rf ~/.cache/pnpm` |
| `~/go/pkg/mod` | 500M-2G | `rm -rf ~/go/pkg/mod/*` |
| `~/.codeium` | 500M-2G | `rm -rf ~/.codeium/*` |
| `~/.local/share/claude/*` | 100-500M | `rm -rf ~/.local/share/claude/*` |
| `~/.local/state/vs-kubernetes` | 100-500M | `rm -rf ~/.local/state/vs-kubernetes/tools` — VS Code Kubernetes extension caches CLI tools; re-downloads on next use |
| **Python __pycache__ (bytecode)** | 50-200M | `find ~/.local -name "__pycache__" -type d -exec rm -rf {} +` — compiled bytecode that regenerates on next script run; can accumulate thousands of dirs |
| **Python GPU package mismatch** | **2-8G** | On AMD/NVIDIA mismatch: `du -sh ~/.local/lib/python*/site-packages/{nvidia,flashinfer*,triton,tokenspeed*,paddle,PyNvVideoCodec,torch*}/ 2>/dev/null` — if `rocminfo` or `lspci | grep -i amd` shows AMD GPU, nvidia/trition/flashinfer packages are 100% safe to nuke. Reverse for NVIDIA systems with ROCm packages (`amd*`, `rocm*`, `flashattention_hip`). |
| `~/.local/share/opencode/*` | 100-300M | `rm -rf ~/.local/share/opencode/*` |
| `~/.local/share/kilo/log` | 500M+ | `rm -rf ~/.local/share/kilo/log/*` — kilod logs accumulate, safe to clear |
| `~/.local/share/GitKrakenCLI/*` | 50-100M | `rm -rf ~/.local/share/GitKrakenCLI/*` |
| `/var/log` | 500M-2G | `sudo journalctl --vacuum-size=200M 2>/dev/null; sudo journalctl --vacuum-time=3d 2>/dev/null; sudo find /var/log -name '*.log' -o -name '*.gz' -o -name '*.old' -delete` — if `--vacuum-size` doesn't shrink (active journals too large), `--vacuum-time` may work better |
| Chrome on-device AI model | 2-5G | `rm -rf ~/.config/google-chrome/OptGuideOnDeviceModel/*` |
| **Cached ZIPs in tool dirs** | 100-500M | `find ~/.vscode ~/android-studio ~/Downloads -name '*.zip' -size +50M -exec rm -v {} \;` — e.g. cloudcode_cli.zip (191M), cmdline-tools.zip (147M) |
| **Paperclip — backup avalanche** | **5-18G** | `~/.paperclip/instances/default/data/backups/` — paperclip creates hourly DB backups with no retention limit. 165+ files common after 2 weeks. Keep 3 most recent: `cd ~/.paperclip/instances/default/data/backups; ls -t | tail -n +4 | xargs rm -f` |
| **Paperclip — server log** | **200-600M** | `~/.paperclip/instances/default/logs/server.log` — no log rotation. Truncate to last 50M: `tail -c 50M server.log > /tmp/server.log.tail && mv /tmp/server.log.tail server.log` (safe while process is running) |
| **Paperclip — run logs** | **200-500M** | `~/.paperclip/instances/default/data/run-logs/` — old agent execution artifacts. Keep 3 most recent: `cd run-logs; ls -t | tail -n +4 | while read d; do rm -rf \"$d\"; done` |
| **Paperclip — workspace node_modules** | **500M-1G** | `~/.paperclip/workspace/*/node_modules/` — workspace checkout deps that aren't actively needed. Safe to clean, recreated on next workspace use |
| **Docker — prune all** | **1-15G** | `docker system prune -af && docker builder prune -af && docker image prune -af` |
| **Docker — delete stopped containers** | **100M-10G** | `docker container prune -f` |
| **Docker — stale image tags (`local_x` vs `x`)** | **2-5G each** | Rebuilt images leave orphan duplicate tags (e.g. `honcho_api:latest` vs `honcho-api:latest`). Compare `docker images` against `docker inspect -f '{{.Image}}' $(docker ps -q)` — any repo:tag whose ID no container uses is dead weight. |
| **Snap — disabled revisions** | **1-4G** | `snap list --all \| awk '/disabled/{print $1, $3}'` then `sudo snap remove --purge <name>` for each. Set `sudo snap set system refresh.retain=2` so future old revisions auto-purge. (Check whether the snap is *only* present as a disabled revision — removing those is free; removing an active snap's old revision keeps the app.) |
| **Docker — unused images** | **1-10G** | `docker image prune -af` |
| **Docker — orphaned volumes** | **1-5G** | `docker volume prune -f` (only after container prune; volumes referenced by docker-compose in project dirs won't be removed this way) |

**TIER 2 — Usually Safe (ask first, re-downloadable):**
| Target | Typical Size | Notes |
|--------|-------------|-------|
| Flatpak apps + runtimes | 5-15G | `flatpak list --app` to see installed apps; `flatpak uninstall --unused` removes unused runtimes. Full removal: `flatpak uninstall --all` (reinstall from flathub). Data split between `~/.local/share/flatpak/` and `/var/lib/flatpak/` |
| IDE extensions (Windsurf, VSCode, Antigravity, Marscode) | 500M-2G each | Re-download on next launch — check last-modified date with `stat`; dirs untouched 30+ days are strong cleanup candidates |
| **Stale source clones** (same repo on two drives) | **1-5G (node_modules)** | Check if active service runs from secondary drive: `ps aux | grep -i <app-name>` → process paths show which clone is live. If root clone isn't running, its `node_modules/` is removable: `rm -rf ~/<project>/node_modules` (keep source files) |
| `~/.nvm/versions/node` | 100-300M | Keep desired version only |
| Python ML libs (CUDA, Torch, nvidia) | 5-8G | `pip uninstall` or rm the dirs |
| `~/.lmstudio` | 1-3G | LM Studio app data |
| `~/.rustup/toolchains` | 1-3G | Re-download with `rustup update` |
| `~/.npm-global/lib` | 1-3G | Re-install with `npm i -g <packages>` |
| **Cargo/Rust `target/` directories** | **3-8G each** | `rm -rf ~/<project>/target` — build artifacts; safe to remove if not actively developing, recreated by `cargo build` |
| `~/.local/share/claude/versions/` (old) | 200-500M | Keep only the latest: `ls -t ~/.local/share/claude/versions/ | tail -n +2 | xargs -I{} rm -rfve "$HOME/.local/share/claude/versions/{}"` — each version file is ~240-250M |
| `~/.local/share/devin/cli/_versions/` (old) | 100-300M | Keep only `current/`: `ls -d ~/.local/share/devin/cli/_versions/*/ | grep -v current | xargs rm -rf` — old Devin CLI versions |
**TIER 3 — Keep (system-critical or user-facing):**
- `android-studio` / `android-sdk` — the IDE and SDK
- `~/.ollama` + `/usr/share/ollama/.ollama/models` — LLM models
- Firefox / Thunderbird / snapd / CUPS / mesa snaps via `snap`
- `~/.hermes` — active agent installation
- `~/.kiro* / ~/.local/bin/kiro*` — kiro-cli in use
- `~/.paperclip/instances` — active Paperclip instances
- `~/.config/google-chrome/Default` — browser profile (not cache)
- `~/.windsurf` / `~/.antigravity` — IDE config (extensions are re-installable, config is not)

**TIER 4 — Move to secondary drive (preferred over delete):**
When a secondary drive like `/media/kubuntux/DEVELOPMENT1` exists and has room:
- Large project directories (Cline, llama.cpp source, ATLAS-GATE repos, etc.)
- Archived projects (old-docs, stale repos)
- Large downloaded ZIPs/tarballs that might be needed later
- **Always offer "move to DRIVE/old-docs/" as an alternative to deletion**

### Step 5: Move Command Pattern

```bash
DEST=/media/kubuntux/DEVELOPMENT1/old-docs
mkdir -p "$DEST"
mv /home/kubuntux/Documents/BigProject "$DEST/"
mv /home/kubuntux/SomeLargeDir "$DEST/"
```

For a Git project backup, enumerate ignored files with `git ls-files -z --others --ignored --exclude-standard` from the repo root and preserve each path relative to that project. Verify the destination mount with `findmnt -T "$DEST"`; after copying, read back every manifest path and compare file sizes and symlink targets. Do not delete the source while the copy is running or when verification is partial; confirm the pushed source commit separately.

### Step 6: Verify

```bash
df -h /
echo "Freed: $((OLD_FREE - NEW_FREE))G"
```

### Step 7: Fix Errors Found During Cleanup

After freeing space, check for system errors that may have contributed to the problem:

```bash
# Check failed systemd services
systemctl --failed --no-pager
# Reset stale failures (they'll restart clean next activation)
sudo systemctl reset-failed <service-name>

# Check apt warnings (duplicated sources, broken packages)
sudo apt update 2>&1 | head -20
# Fix duplicated sources by removing one entry:
#   /etc/apt/sources.list.d/docker.list vs docker.sources — keep .sources, delete .list
ls /etc/apt/sources.list.d/
sudo rm /etc/apt/sources.list.d/<duplicate-file>

# Check for stuck snap operations that block snap remove
snap changes 2>/dev/null  # look for "Abort" or "Doing" entries
snap change <id>          # see details
# If stuck, try:
sudo snap abort <id>
# If abort doesn't work, force-kill the daemon:
sudo pkill -9 snapd
sudo pkill -9 snap-store
sleep 2
sudo systemctl start snapd
# Now the stuck change flips to "Undone" and snap remove works
# If snapd daemon itself is stuck:
sudo systemctl restart snapd
sudo systemctl reset-failed snapd.failure.service
```
\n## Time-Based Aggressive Sweep Profile\n\nWhen the user says "delete everything not used in 2-3 months that won't break my computer" (blanket cleanup directive). Do not present a plan — execute fast. This profile does NOT replace the tiered approach; it's for "just nuke it" requests.\n\n### Approach (in order)\n\n1. **Check active processes** so you don't touch a running app's dir\n2. **Nuke Tier 1 caches** (`.cache`, `uv`, `pnpm`, `npm`, `snapd cache`, Docker, `/tmp`, `/var/log`)\n3. **Nuke unused IDE configs**: `.vscode`, `.cursor`, `.kilo`, `.codex`, `.opencode`, `.claude` — they re-download\n4. **Nuke `.gradle`** (5-6G, Android build cache, dead on non-Android dev machines)\n5. **Nuke `.rustup` + `.cargo/registry`** (5-6G total, safe if no active Rust dev)\n6. **Nuke `.omp`** (1-1.5G, Oh My Posh themes — re-downloads)\n7. **Nuke abandoned project dirs** in `~/` older than 90 days (`aios`, `image-mcp`, `crypto_check`, `eporner-tool`, `token-optimizer`, etc.)\n8. **Nuke `.antigravity-ide-server`**, `.devin-server` (re-downloads)\n9. **Nuke `.openclaw/workspace` + `.openclaw/agents`** (2-3G, safe if OpenClaw not actively deployed)\n10. **Nuke `/var/lib/flatpak`** (system flatpak runtimes, 5G+)\n11. **Nuke `/srv/frigate`** (model cache, re-downloads)\n12. **Nuke snap android-studio** (3.5G, if home-dir Android Studio was already gone)\n13. **Remove/reduce oversized swapfile** — see Swap section below\n14. **Purge old snap revisions** + `apt clean` + `apt autoremove`\n\n### What NOT to touch\n\n`/usr`, `/etc`, `/boot`, `~/.ssh`, `~/.config/hermes`, `~/.config/tailscale`, `~/.hermes`, any dir belonging to an actively running process, `~/.config/google-chrome/Default` (browser profile, not cache).\n\n### Session reference: 92% → 61% (48G freed)\n\n| Target | Size | Why safe |\n|--------|------|----------|\n| `.gradle` | 5.7G | Android build cache, no Android dev |\n| `.config/google-chrome` | 6.7G | Browser cache, regenerates on open |\n| `.rustup` | 3.6G | Toolchains, re-download with rustup update |\n| `.cargo/registry` | 2.2G | Crate cache, re-fetched on cargo build |\n| `.omp` | 1.3G | Oh My Posh themes |\n| `.antigravity-ide-server` | 761M | Re-downloads |\n| `.devin-server` | 504M | Re-downloads |\n| `.claude` | 510M | Claude Desktop data |\n| `.openclaw/workspace` | 2.6G | Agent workspace |\n| `.openclaw/agents` | 749M | Agent binaries |\n| `.vscode` / `.cursor` / `.kilo` / `.codex` / `.opencode` | ~1.5G total | IDE configs, re-download |\n| `/var/lib/flatpak` | 5.2G | System flatpak runtimes |\n| `/srv/frigate` | 1.2G | AI model cache, re-downloads |\n| `/snap/android-studio` | 3.5G | Snap Android Studio |\n| Abandoned projects × ~10 | 2-3G total | Clones older than 90 days |\n| `/swapfile` | 17G → 0 | zram 7.8G sufficient with 16GB RAM (see Swap section) |\n\n### Swapfile: Removal / Reduction\n\nIf `swapon --show` shows zram active (common on Ubuntu 24.04), the disk swapfile is often redundant on 16GB+ RAM machines:\n\n```bash\n# Remove entirely and rely on zram\nsudo swapoff /swapfile 2>/dev/null && sudo rm -f /swapfile\n\n# Or shrink (slower on Patriot Burst SSDs — ~35-40MB/s write)\nsudo dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress\nsudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile\n```\n\n**Pitfall:** Patriot Burst SSDs write at ~35-40MB/s. An 8G swapfile `dd` takes 3-4 minutes and may timeout at 180s. Use a smaller `count` or run in background with `notify_on_complete=true`.\n\n## Key Rules\n\n- ALWAYS check `df -h` before and after to measure actual space recovered
- The `df -h` delta may be smaller than the sum of individual items freed — filesystem overhead, inodes, journal metadata, and reserved blocks consume the difference. This is normal, not a sign something went wrong.
- ALWAYS check `snap list` before removing snaps — don't remove Firefox, CUPS, snapd, core, mesa
- ALWAYS present a categorized plan to the user before executing deletions
- PREFER moving data to a secondary drive over deletion when the user has a DEVELOPMENT drive
- PREFER asking "how aggressive?" if the user says "delete everything" — get a cleanup profile
- NEVER delete android-studio, android-sdk, ollama models, or active snap packages without explicit confirmation
- NEVER delete directories that contain active tool configurations (~/.config, ~/.hermes, ~/.kiro)
- NEVER run `rm -rf /` or double-check paths before bulk deletes
- Use `sudo` for system-level directories (/var, /tmp, /usr)
- Keep ~/.npm-global/bin tools intact (kanban, etc.) — only clear the cache/lib

## Pitfalls

- `du -sh /*` can timeout on large filesystems — limit scope with explicit paths
- `du -sh /tmp/*` only matches visible (non-dot) files — it **misses hidden files** like `.d8b*` V8 code caches (which can be 22+ GB). After cleaning visible dirs, always run a second-pass file-count check: `sudo find /tmp -type f -printf '%s\\\\n' | awk '{sum+=$1; count++} END {printf \\\"Remaining files: %d, Size: %.1f GB\\\\n\\\", count, sum/1024/1024/1024}'`. Then clean hidden files with `sudo rm -rf /tmp/.[!.]*` (but check what's there first — .X11-unix and systemd-private dirs are system-managed).
- ncdu needs a TTY — use `-o` export mode for non-TTY operation
- Python ML libs (CUDA, Torch) can break tools that depend on them — always confirm first
- Chrome's Default directory is the browser profile (bookmarks, history, passwords) — never delete it without warning
- snap packages look deletable but Firefox, CUPS, firmware-updater, mesa are system-critical
- **Stuck snap auto-refresh operations can block `snap remove`** — if `snap change <id>` shows a change stuck in "Abort" status, snap commands fail with "snap has auto-refresh change in progress". Try `snap abort <id>`. If that fails:
  1. `sudo pkill -9 snapd` and `sudo pkill -9 snap-store` — force-kill the daemon (it respawns via systemd)
  2. `sleep 2 && sudo systemctl start snapd` — starts clean, the stuck change flips to "Undone"
  3. Now `snap remove` works. Note: `systemctl restart snapd` (without `pkill -9` first) may itself timeout.
  - As a fallback, clean around the stuck operation — the snapd blob cache (`/var/lib/snapd/cache/`) can still be safely cleaned independently. The snapd.failure.service unit may appear as failed — reset with `sudo systemctl reset-failed snapd.failure.service`.
- Docker hangs/timeouts when disk is critically full (< 2GB free on `/` where Docker root dir lives). The daemon can't allocate temp layers for new containers or prune operations. Always start with non-Docker cleanup (apt, journal, caches, logs) and retry Docker after you see free space > 3GB. Check `docker system df` first if it responds; if it hangs, skip Docker entirely until light cleanup succeeds.
- `docker run --add-host host.docker.internal:host-gateway` may be blocked by agent security policies (tirith, command_allowlist). Fallback options if blocked: `--network host` (if port conflicts don't matter) or use the host's LAN IP directly (e.g. `http://192.168.1.X:PORT` instead of `http://host.docker.internal:PORT`).
- **Snapd cache is not automatically cleaned when snaps update** — `/var/lib/snapd/cache/` accumulates old snap blob files. Unlike `apt clean`, there's no snap equivalent. Manual cleanup with `sudo find /var/lib/snapd/cache/ -type f -delete` is safe — snaps re-download on next refresh.
- **`.local/share/applications/` may hide full app installs** — normally a directory of .desktop files, but some apps (IDA Free, Electron apps) install their entire binary tree there. Check with `du -sh ~/.local/share/applications/* | sort -rh` and inspect any subdirectories over 10M. Treat them as TIER 3 — ask before removing.
- **Docker volumes persist even after container removal if docker-compose projects remain** — `docker volume prune -f` only removes volumes not referenced by *any* container (active or stopped). Volumes tied to a docker-compose project in a dir on disk persist. To fully clean: `docker compose down -v` in the project directory, or manually identify and remove with `docker volume rm <name>`.
- **`df -h` reports 0 available even when free blocks exist** — ext4 reserves 5% of blocks for root by default. On a 219G drive, that's ~11GB. When all unreserved blocks are consumed, `df -h` shows "Avail 0" even with 11G+ free. Check the true state with `python3 -c "import os; s=os.statvfs('/'); gb=lambda b: b*s.f_frsize/1024/1024/1024; print(f'Free: {gb(s.f_bfree):.1f}G, Avail: {gb(s.f_bavail):.1f}G, Reserved: {gb(s.f_bfree-s.f_bavail):.1f}G')"`. If Free > 0 and Reserved > 0 but Avail = 0, reduce reserved blocks with `sudo tune2fs -m 1 /dev/sdX`. This reclaims the reserved space for unprivileged processes (Hermes browser tool, npm installs, etc.) immediately — no reboot needed.