---
name: linux-host-performance-triage
description: "Use when a Linux host feels slow, hot, or mis-tuned."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [linux, performance, systemd, power-management, triage]
    related_skills: [change-verification]
---

# Linux Host Performance Triage

## When to Use

- The user says a machine is slow, sluggish, laggy, hot, or "feels underpowered".
- A host got slower after a power, mount, boot, or hardware change.
- The user asks to "clean up", "optimise", or "speed up" a Linux host.
- Any systemd Linux host; `/proc/pressure` needs kernel 4.20+ and degrades gracefully without it.

Measure first, fix the actual offender, report numbers. A performance sweep that touches twenty things is unverifiable and usually makes a machine worse.

## 1. Collect evidence (read-only)

Run `scripts/probe.sh` from this skill — it gathers every number below in one pass, no sudo, no writes. Key pieces if you run the checks by hand:

- `uptime`, `free -h`, `df -h -x tmpfs -x devtmpfs -x squashfs`
- `/proc/pressure/{cpu,io,memory}` — `some` high with `full` near zero is latency, not saturation; quote both.
- `ps -eo pcpu,pmem,rss,comm --sort=-%cpu` and the `--sort=-%mem` variant, both limited to the top ten.
- Per-process swap from `/proc/<pid>/status` (`VmSwap`) before suggesting anyone kill a process.
- `systemctl --failed`, `systemd-analyze`, `systemd-analyze blame`.
- CPU state: `scaling_driver`, `scaling_governor`, `energy_performance_preference`, `scaling_cur_freq`, `no_turbo`, `max_perf_pct`, `min_perf_pct`, `powerprofilesctl get`.
- `sensors` for the package temperature and its `crit` value.

## 2. Work in cause order

Failed units → CPU power state → boot-blocking mounts → thermal ceiling → disk headroom → memory → what the user is actually running. Earlier rows cause later ones; skipping ahead means fixing symptoms.

See `references/symptom-fix-table.md` for the symptom → check → fix lookup table.

## 3. CPU power state

- On `intel_pstate`, a governor of `powersave` is the normal HWP mode — the meaningful knob is `energy_performance_preference` (EPP). A box pinned at low EPP sits far below its rated clock while showing no load problem at all.
- Change it through the power-profile daemon (`powerprofilesctl set performance|balanced|power-saver`). The daemon owns EPP and the platform profile, so a hand-rolled sysfs writer competes with it and can return `EBUSY` on a write that looks harmless.
- A custom systemd oneshot that pins CPU state must end with `exit 0` and must not fail on a sysfs path that may not exist on this machine (onboard graphics means no discrete-GPU `power/control` path). One failed write marks the whole unit failed and **skips every write after it** — so the tuning silently never applies while the failed unit is the only trace.
- After raising clocks, verify with a short load test and read the temperature. If it pins near `crit`, the sustained limit is thermal and physical; keep the documented way back (`powerprofilesctl set balanced`) and say so.

## 4. Boot and failed units

- `systemd-analyze blame` reports how long a unit was active, **including waiting on dependencies**. Do not chase an offender that is merely waiting.
- A network mount in fstab that has `_netdev,nofail` but lacks `x-systemd.automount` still blocks boot for the full timeout and then stays permanently failed. Match the options its siblings already use rather than inventing a new style.
- Prove the export exists before editing anything: list the server's shares (`smbclient -L //HOST -N -g`) instead of assuming a connection problem. `mount error(2)` is a missing share name; `error(101)` is an unreachable host.
- When a stale entry can never work because the share is gone, comment it out with the reason inline and keep the original line — do not delete configuration the user may still want to repair.

## 5. Application startup blocked by automounts

For a slow file manager or file picker, inspect the exact process state before tuning previews or indexing: `ps -o pid,stat,wchan:32,etime,args -p PID`, `/proc/PID/wchan`, `findmnt -t autofs`, and the matching systemd automount/mount status and journal. `D` state with `autofs_wait` plus repeated automount requests identifies a blocked path lookup; attribute the trigger PID from the automount journal rather than assuming the file manager itself is CPU-bound. Check application Places/bookmarks and desktop portals for the path being touched.

If a remote mount is deliberately retained but server unavailability must not stall interactive browsing, set a bounded `x-systemd.mount-timeout=5s` on that specific fstab entry, preserve a permission-restricted backup, run `systemctl daemon-reload`, verify the generated unit's `TimeoutUSec`, then trigger one bounded access with `timeout` and time a fresh application-open request. This bounds mount establishment only; it does not make the remote share available or guarantee fast I/O on an already-mounted, disconnected filesystem. Keep the automount and share definition intact unless the user asks to remove them.

## 6. Pitfalls that cost real time

- Never truncate a listener list with a fixed line count (a `ss -ltnp` listing cut to its first 25 lines): the port you care about is the one that gets cut, and a live service looks dead. Filter the full output by port, or probe the port and read the status code.
- A shim or wrapper earlier in `PATH` can shadow a standard flag (`grep -h`, `--max`) and print its own usage text. Usage text in a command's output means the command did not run — use a different flag or a structured search tool, and never read that dump as file content.
- Do not kill the user's own stack (agents, containers, editors, sync daemons) to free memory or CPU. Report the consumers and their sizes; let the user decide.

## Report shape

- Before/after numbers for each thing you changed, plus the revert command on the same line.
- One line per fix; no feature tour.
- What you deliberately left alone and why, separated from what you changed.
- Whether a reboot is needed for the fix to take effect (boot-path changes and userspace units differ).

## One-line rule

Profile the offender, fix the offender, quote the numbers — never sweep a box with unrequested "optimisations".
