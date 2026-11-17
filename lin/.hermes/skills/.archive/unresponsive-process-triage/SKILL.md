---
name: unresponsive-process-triage
description: "Use when an app lags, hangs, or says Not Responding."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
category: system
tags: [diagnosis, hang, not-responding, d-state, automount, nfs, cifs, desktop, kde]
related_skills: [network-mounts, linux-crash-diagnosis, linux-laptop-performance-tuning]
metadata:
  hermes:
    tags: [diagnosis, hang, not-responding, d-state, automount, nfs, cifs, desktop, kde]
    related_skills: [network-mounts, linux-crash-diagnosis, linux-laptop-performance-tuning]
trigger: When the user says an application is slow, laggy, hangs, or "not responding"; a file manager or open/save dialog stalls or loads slowly; a directory is unlistable; a command sits with no output — and the machine is otherwise alive. Not for whole-system crashes or reboots.
---

# Unresponsive Process Triage

An app that freezes is a symptom. When the machine is otherwise alive and CPU/RAM
look unremarkable, the cause is usually a process parked in an uninterruptible
kernel wait behind a dependency that will never answer — most often a hung network
mount or automount. Restarting the app, its helpers, or the desktop does nothing,
because the wait is in the kernel.

**Not this skill:** the whole machine crashes, reboots, or hard-locks →
`system/linux-crash-diagnosis`. The app responds but everything is slow under real
load → `devops/linux-laptop-performance-tuning`. Mount setup, credentials and
exports live in `system/network-mounts`.

## When to Use

- "the file manager is so slow / lags / says not responding"
- One app freezes or a file dialog stalls while the rest of the session is fine
- Several unrelated apps hang at once (they share a directory or a service)
- A command sits with no output and no error and the box is otherwise alive

## Procedure

**1. Classify the wait, not the app.** One command separates the three cases:

```bash
ps -eo pid,user,stat,wchan:24,cmd | awk '$3 ~ /D/'
```

| Result | Meaning |
|---|---|
| `D` + `wchan autofs_wait` | Blocked on an automount trigger (the mount will never complete) |
| `D` + another fs/net wait | Blocked on that filesystem or device |
| no `D`, high CPU on the app | Genuine compute/GPU load — tune instead of debugging |

The command column names the victim (file-manager helper, `kio_*`,
`xdg-desktop-portal-*`, indexer, backup tool). The victim is the symptom; the wait
channel is the cause.

**2. Blocked or just slow?** Time the operations the app actually performs:

```bash
time ls /mnt; time ls /mnt/<mount>; time ls ~
```

Milliseconds versus ~30–90s is the whole diagnosis. A *local* parent directory that
hangs means an entry inside it is the problem.

**3. Find the failing unit.**

```bash
findmnt -t nfs,nfs4,cifs,fuse.sshfs
systemctl list-units --all 'mnt-*.mount' 'mnt-*.automount'
journalctl -b | grep -E "automount request|Mounting timed out|Failed to mount"
```

A `.mount` unit logging `Mounting timed out. Terminating.` on a ~90s cycle is the
cause; `triggered by <pid> (<cmd>)` in the automount line shows who touched the path
first. If nothing mount-related appears, widen to the device or service the app
depends on (disk health, a local daemon).

**4. Fix the dependency, server first.** The client cannot be talked out of a wait:

```bash
# server side first: is it serving at all, and does the resource exist?
ssh <server> 'systemctl is-active <share-daemon>; sudo exportfs -v; ls -ld <path>; df -h <path>'
sudo systemctl enable --now <share-daemon>        # on the server
```

Then make the client retry. fstab-generated automount unit names escape `-` as
`\x2d`:

```bash
sudo systemctl restart 'mnt-hermes\x2dprofile\x2dnfs.automount'
time ls /mnt/<mount_name>                  # expect ~0.1s and the real file list
```

**5. Confirm the block cleared.** Re-run the `D`-state query: the process returns to
`S`/`Ssl` on its own once the wait ends. Re-time the access the user complained about
and quote both numbers in the handoff.

## Rules

- **Never start by restarting the app, its portal, or the desktop.** The wait is in
  the kernel; those restarts only add noise.
- **A `D`-state process cannot be killed.** SIGKILL is a queued no-op until the kernel
  call returns. Fix the dependency and it unblocks by itself.
- **One bad entry poisons the whole parent directory.** A single failing automount
  under a shared path makes every consumer of that path slow — fix or remove the
  entry instead of auditing the apps that hang.
- **Fail-fast is progress, not a new failure.** Once the server answers, a still-broken
  mount returns `ENODEV`/`No such device` in ~0.08s instead of hanging 90s. Read the
  fast error; it names the real problem (missing resource, wrong path).
- **A config listing is not a working resource.** `exportfs -v` lists exports whose
  directory does not exist, and a share can be configured while its daemon is
  `disabled`/`inactive`. Confirm the daemon is active and the path exists with `ls -ld`.
- **`x-systemd.device-timeout` does not cap a hard NFS mount**, and `nofail` only
  spares the boot — later accesses still pay the ~90s retry.
- **Symptom returns after an idle period → suspect autofs under autofs.** An export or
  share rooted inside another `x-systemd.automount` (a disk auto-mounted under
  `/run/media/...`) re-plants the hang whenever the backing mount idles out. Pin the
  backing store as a permanent mount.
- **Don't blame the file manager.** Rebuilding caches, disabling a file indexer
  (`balooctl6 status`), or resetting a portal is wasted work while the mount hangs.
  Checking `D` state and mount timings first also tells you cheaply when the app really
  *is* the problem: no `D` process, fast `ls`, high CPU on the app itself.

## Handoff shape

Name the mechanism and the numbers (`/mnt` 90s → 6ms), list what changed on each
machine, disclose every package and file you touched outside the fix, and separate
"fixed" from "still broken but now failing fast" (with a one-line offer to finish it).
Report measured load (memory, swap, top consumers) as a separate sentence — the user
asked about one app, not for a tuning pass.
