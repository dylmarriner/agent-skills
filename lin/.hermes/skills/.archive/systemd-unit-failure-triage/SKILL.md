---
name: systemd-unit-failure-triage
description: Use when a Linux host has failed units or boots slowly.
version: 1.0.0
metadata:
  hermes:
    tags: [linux, systemd, boot, mounts, triage, performance]
    related_skills: [linux-thermal-throttling-triage, linux-laptop-performance-tuning]
---

# systemd Unit Failure & Boot Stall Triage

Use when a Linux host is reported slow, unresponsive, or slow to boot **and** something is in a
failed state — the usual real answer to "speed up my PC/box" on a machine that is not obviously
resource-starved. Covers failing systemd units, blocking network mounts, and stale GRUB env blocks.

Scope split (do not duplicate the siblings):
- CPU clocks, EPP/turbo, thermals, RAPL ceiling, load-test verdict → `linux-thermal-throttling-triage`.
- Tuning actions (sysctl, service trims, compositor, Wi-Fi, zram, Docker RAM hogs) →
  `linux-laptop-performance-tuning`.
- This skill: **what is failing, why the boot is waiting, and how to fix it in place.**

Hard rule: a failed unit is diagnosed from *live values*, never from the unit's name, description, or
intent. A tuning unit that says "turbo enabled, EPP balance_performance" may have applied none of it.

## When to Use

- "Speed up my PC / box" on a machine that is not obviously resource-starved.
- The user reports slowness that started "a while ago" and never recovered (a boot-time oneshot that
  stopped applying, not a resource change).
- Anything shows up under `systemctl --failed`.
- Boot feels slow, or a network share is slow/dead to reach.
- After a hostname, share, device, or GPU change — the previously written boot-time config may now be
  pointing at something that no longer exists.

## 1. Enumerate before tuning

```bash
systemctl --failed --no-legend                 # the highest-yield single command
systemd-analyze blame | awk 'NR<=12'
systemd-analyze                                # firmware + loader + kernel + userspace split
```

Only after that go looking at `ps`/`free`/pstate. On a half-configured machine the failure is the
cause; process load is a symptom you can explain later.

## 2. Read `systemd-analyze blame` correctly

- Blame reports wall time the unit was *active*, **including time it spent waiting on dependencies**.
  A suspiciously large number (e.g. `zramswap.service 8.8s`, `containerd 7.6s`, `tailscaled 7.6s`)
  is usually serialization behind another unit — fix the blocker, do not "optimize" the number.
- A **failed `.mount`** in blame is a genuine stall: the boot waits out the mount timeout, and every
  later traversal of that mountpoint blocks again. This is the one blame entry that is always worth
  fixing.
- `sudo systemctl reset-failed <unit>` only clears the red state; it is not a fix — re-run it after
  the real repair, then confirm `systemctl --failed --no-legend | wc -l` is 0.

## 3. Fix a tuning/safety oneshot in place (never delete it)

A hand-written oneshot that writes sysfs/procfs at boot is the classic root cause: it fails, stops
re-asserting its settings on later boots, and the machine quietly gets slower. Repair, do not remove:

- Patch the `ExecStart` line; keep the old values in a comment in that unit so re-tuning is one edit.
- **A failed oneshot has usually applied half its chain.** `bash -c` with `;` continues after an
  error, so a unit exiting 1 can leave `no_turbo=0` / `max_perf_pct=100` set while a later loop died.
  Check the live sysfs values to learn what actually landed.
- Make it un-failable: `|| true` on each optional path and `exit 0` as the last statement. One stale
  path — a PCI address for a dGPU that has been removed, a device that no longer exists — must not be
  able to mark the whole profile `failed`.
- Never write an interface the power manager already owns: `.../energy_performance_preference` can
  return `EBUSY` while power-profiles-daemon holds it. Set the profile with
  `powerprofilesctl set <profile>` and let ppd write EPP (details in the thermal skill).

```bash
sudo systemctl daemon-reload && sudo systemctl restart <unit> && systemctl is-active <unit>
```

## 4. Dead network mounts in fstab

`nofail` stops a bad entry from blocking boot into emergency mode, but it does **not** stop the entry
from failing: the unit lands in `failed`, boot eats the mount timeout, and later tooling that walks
that mountpoint stalls or errors.

Fix with the options a *working sibling line already has* — copy, do not invent:

```
//HOST/SHARE /mnt/point cifs guest,uid=USER,gid=USER,vers=3.1.1,_netdev,nofail,x-systemd.automount,x-systemd.idle-timeout=300,x-systemd.device-timeout=5 0 0
```

```bash
sudo systemctl daemon-reload
sudo systemctl reset-failed mnt-<point>.mount
sudo systemctl start mnt-<point>.automount     # mounts on first access instead of at boot
sudo mount /mnt/point                          # FAILS with ENOENT on a live autofs point
ls /mnt/point                                  # trigger the automount instead
```

Confirm the share exists **before** touching options — otherwise the network gets blamed for a
missing resource:

```bash
smbclient -L //HOST -N -g | awk -F'|' '/Disk/{print $2}'   # does the share name exist at all?
```

| mount.cifs error | Meaning |
|---|---|
| `error(2) No such file or directory` | share **name does not exist** on the server — fix the name, not the network |
| `error(101) Network is unreachable` | link/VPN not up yet at that point in boot — automount is the fix |
| `error(13) Permission denied` | credentials/`sec=` mismatch in the fstab options |
| `error(112) Host is down` | server itself unreachable — verify with `ping <host>` before editing fstab |

When the share is genuinely retired, comment the fstab line out with the original kept inline in the
comment. Re-enabling stays a one-line edit and the intent survives.

## 5. GRUB: `invalid environment block`

A GRUB "record successful boot" unit failing with `grub-editenv: invalid environment block` leaves
`recordfail` set, which can hold the boot menu. Rebuild the block instead of masking the unit:

```bash
sudo cp /boot/grub/grubenv /boot/grub/grubenv.bak
sudo grub-editenv /boot/grub/grubenv create
sudo grub-editenv /boot/grub/grubenv unset recordfail
sudo systemctl restart grub2-common.service   # or the distro's grub-common equivalent
```

Also check `/boot/efi/EFI/*/grubenv` when GRUB reads its environment from the ESP rather than from
`/boot/grub`.

## 6. Probe bundle

`scripts/host-perf-probe.sh` prints load, PSI, memory, top CPU/RAM, swap hogs, disk, **failed units**,
boot blame, pstate/EPP, thermals, zram and network mounts in one read-only pass. Run it first, then
drill into whatever it flags.

## Pitfalls

- **Honor the user's literal canonical path when relocating application data.** Never infer “main drive” from a mount label, capacity, or symlink; compare `readlink -f` and `findmnt -T` for the requested path, the current data directory, and the service's actual executable. Stop the service, preserve target-only state, move the data to the exact requested path, update every launcher/unit reference (`ExecStart`, `WorkingDirectory`, environment, and embedded wrapper paths), then verify the CLI, service, and database there. A successful mount or symlink lookup does not prove the data lives at the user's requested location.
- **`systemctl --failed` before any tuning.** Assuming "bloat" and disabling services while a
  misconfigured oneshot sits in a failed state is how a 2-line fix becomes an afternoon of churn.
- **Do not chase the biggest blame number.** It includes dependency wait time; check
  `systemd-analyze critical-chain` before attributing a slow unit to its own work.
- **`nofail` is not `automount`.** Without `x-systemd.automount` a dead mount still costs the boot
  timeout and stays `failed` forever.
- **A failed `.mount` unit is recreated on every trigger attempt**, so "it keeps coming back" after
  `reset-failed` means the mount itself is still broken — fix the source, not the state.
- **Never delete or overwrite the user's unit file or fstab line wholesale.** Patch in place, back up
  first (`cp <file> <file>.bak.$(date +%s)`), and keep the original values visible in a comment.
- **Disk "optimization" that destroys data is not optimization.** Prune dangling docker images and
  build cache only (`docker image prune -f`, `docker builder prune -f`); report `docker system df`
  reclaimable bytes instead of running `-a` on images you did not build.
- **Reading sysfs in a batched probe:** `printf '%s = %s\n' "$(basename "$f")" "$(<"$f")"` rather
  than piping it through a text filter — a shell wrapper or a filter alias can intercept the pipeline
  and you will silently get the wrapper's usage text instead of the value.

## Report shape that lands

1. Before/after table of what changed (`failed units: 3 → 0`, `EPP: balance_power → balance_performance`).
2. One line per fix: root cause, the command applied, the rollback path or backup file.
3. The evidence for whatever bottleneck remains, and the physical constraint if there is one.
4. **What you deliberately did not touch, and why** — the residual load is often the user's own
   stack (agent gateways, editors, browser, Docker mesh). Name it and give the opt-in one-liner
   (`systemctl --user stop <unit>`, `docker image prune -a`) instead of killing their work.
5. No menu of options, no permission requests, no tour of rejected ideas.
