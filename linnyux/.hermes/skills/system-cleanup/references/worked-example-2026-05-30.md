# Worked Example: 100% Full → 18G Freed in One Session

**Date**: 2026-05-30  
**Drive**: 219G root (/dev/sdb3), fully blocked at 100% (0 avail)
**User**: Dylan — prefers no progress chatter, just verified results

## Starting State

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdb3       219G  208G     0 100% /
```

## Diagnostics Approach

Ran in parallel to get a complete picture fast:

1. `df -h /` — overall space
2. `du -sh /var/log /var/cache /tmp ~/.cache ~/.local/share/Trash` — key category sizes
3. `du -sh /tmp/* | sort -rh | head -20`
4. `du -sh ~/.cache/* | sort -rh | head -20`
5. `du -sh /var/cache/* | sort -rh | head -20`
6. `du -sh /var/log/* | sort -rh | head -20`
7. `dpkg -l | grep linux-image` — old kernel count

## Targets Found & Action Taken

### Tier 1 — Safe Caches (~18G total)

| Target | Size | Action |
|--------|------|--------|
| uv cache (archive-v0) | 13G | `uv cache clean` — biggest single win |
| /tmp (paperclip opencode configs, jiti, pcvt, lighthouse) | 33G → cleaned | `sudo rm -rf /tmp/paperclip-opencode-config-* /tmp/pcvt-* /tmp/node-compile-cache /tmp/jiti /tmp/lighthouse-reports` |
| npm cache | ~200M | `npm cache clean --force` |
| pnpm cache (~/.cache/pnpm) | 537M | `rm -rf ~/.cache/pnpm` |
| Go build cache | ~200M | `go clean -cache` |
| HuggingFace hub cache | ~200M | `rm -rf ~/.cache/huggingface/hub` |
| journald logs | 548M → 200M | `sudo journalctl --vacuum-size=200M` |
| old rotated logs (syslog.1, kern.log.1, auth.log.1, ufw.log.1) | ~200M | `sudo rm -f /var/log/*.1 /var/log/*.gz /var/log/*.old` |
| apt archives | 758M | `sudo apt clean` |
| apt-xapian-index | 96M | left intact (rebuilt on apt ops) |

### Tier 2 — Old Kernels (~4G total)

| Kernel | Removed |
|--------|---------|
| 6.8.0-40, -90, -94, -100, -101, -106, -107, -110, -111 | `sudo apt purge -y linux-image-... linux-headers-... linux-modules-...` |
| Retained | 6.8.0-117 (current) only |

### Errors Fixed

| Error | Fix |
|-------|-----|
| "Target Packages configured multiple times in docker.list and docker.sources" | `sudo rm /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.sources.save` |
| Failed services: session-c89.scope, man-db.service, snap.cups.cups-browsed.service | `sudo systemctl reset-failed <unit>` + `sudo systemctl disable snap.cups.cups-browsed.service` (non-existent snap) |
| man-db timer stuck with failure state | `sudo systemctl start man-db.service` to trigger fresh run |

## End State

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdb3       219G  190G   18G  92% /
```

## Key Lessons

1. **uv cache is the #1 surprise hog** — 13G in ~/.cache/uv/archive-v0. Always check with `uv cache clean` or `du -sh ~/.cache/uv/*`.
2. **Old kernels accumulate quietly** — on Ubuntu 24.04 systems that get frequent kernel updates, running `dpkg -l | grep linux-image` can reveal 10+ old kernels worth 4-5G total.
3. **Paperclip spawns unstoppable temp dirs** — `paperclip-opencode-config-*` directories in /tmp at 50-58M each, can accumulate to many GB. Clean aggressively.
4. **Docker apt source dedup** — if both `docker.list` and `docker.sources` exist, apt warns on every operation. Keep `.sources`, delete `.list`.
5. **Failed systemd services don't self-clean** — `systemctl --failed` should be a standard post-cleanup check. Non-existent snap services need explicit disable.
6. **Nothing in /tmp was critical this time** — the paperclip workspace temp files and pcvt temp files were all safe to delete from a disk-full state. No active X11 or systemd sockets were affected since those are in /tmp/.X11-unix and /tmp/systemd-private-* which we avoided.
