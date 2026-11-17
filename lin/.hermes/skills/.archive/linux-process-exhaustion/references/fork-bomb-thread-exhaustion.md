# Fork Bomb / Thread Exhaustion — Worked Remediation (Pi 5, rabuntu)

Session: 2026-08-05. User reported `sudo apt update && sudo apt upgrade -y` failing on
rabuntu (Pi 5, Tailscale 100.68.0.96). Root cause was NOT apt — it was kernel thread
exhaustion from a container zombie leak.

## Symptom

```
$ sudo apt update
WARNING: apt does not have a stable CLI interface...
FATAL -> Failed to fork.
```

No repo errors, no network errors — just fork failure. `Failed to fork` /
`fork: retry: Resource temporarily unavailable` means the kernel has run out of
task slots. This is thread/process exhaustion, not apt corruption.

## Diagnosis sequence (in order, each narrows the cause)

1. `free -h` → 1.7 GiB available (tight but not OOM), 2.8 GiB swap used.
2. `uptime` → load 5–6 (high for a Pi 5).
3. `ps -e --no-headers | wc -l` → **62,450 processes** (healthy Pi: a few hundred).
4. `cat /proc/sys/kernel/threads-max` = 63812 and `ps -eLf --no-headers | wc -l` =
   **63811** → thread count pinned at the kernel cap. Every new fork fails.
5. `ps -e --no-headers -o comm= | sort | uniq -c | sort -rn | head -10` →
   **61,604 `ssl_client`** (then 242 curl, 127 mariadb, ...).
6. `ps -e --no-headers -o user= | sort | uniq -c | sort -rn | head -10` →
   61,624 processes owned by **messagebus**.
7. Sample: `cat /proc/<pid>/status` → `State: Z (zombie)`, Uid 100 (messagebus),
   PPid = a live parent.

## Finding the spawner

- Zombie PPids (`/proc/<zombie>/status` → PPid) pointed at a live parent:
  `autonomous-control-plane` (PID 1950476), running as messagebus, parented to a
  `containerd-shim` → inside a Docker container.
- Container: `compose-autonomous-control-plane-1`, part of a 21-container compose
  project ("compose"). Every service in that stack spawned `ssl_client` children as
  the messagebus user and never called wait() → fleet-wide zombie leak over ~11 h.
- The `ssl_client` binary lived inside the container images; the container main
  processes ran as uid 100 (messagebus).

## Remediation steps that worked

1. `sudo pkill -9 -u messagebus ssl_client` → **failed**: zombies cannot be
   killed — SIGKILL is a no-op on Z state. Count unchanged.
2. `sudo kill -9 <spawner-pid>` → zombies started reparenting to init, BUT the
   container's restart policy (`unless-stopped`) respawned the process within
   seconds and the count climbed again.
3. `docker compose -p compose stop` → stopped the whole stack; init reaped the
   orphans: threads 63811 → 1786, zombie count → 0.
4. **Gotcha**: `compose-hermes-provider-1` came back up on its own (restart
   policy) and resumed spawning fresh zombies. Fix:
   ```bash
   docker update --restart=no compose-hermes-provider-1   # disable policy FIRST
   docker stop compose-hermes-provider-1                  # then stop
   ```
5. Verify: `pgrep -u messagebus ssl_client | wc -l` → 0; threads ~1200;
   `pgrep -u messagebus` → 1 (the legit dbus-daemon).
6. Original task then succeeded: apt update (72 upgrades), apt upgrade,
   install git/curl/xz-utils (all already present, verified).

## Pitfalls hit during this remediation

- **`pkill` without sudo cannot kill another user's processes** → "Operation not
  permitted" per PID. With 60K+ PIDs that's ~3.5 MB of error output — always
  `>/dev/null 2>&1` on pkill/kill across a swarm.
- **`which <bin>` returning empty + `ls -la $(which <bin>)`** → the failed command
  substitution made `ls` list the whole home directory (133 KB of mp3 listing
  dumped into the session). Guard/quote command substitution before using it in a
  path; prefer `command -v`.
- **Under fork exhaustion, pipes and subshells fail too** — even
  `ps -eLf | wc -l` gets "fork: retry". Keep remote commands to a single simple
  command per SSH call until threads free up.
- **SSH dropped mid-upgrade** (kernel upgrade restarted sshd) — reconnect and
  check `pgrep -x apt`; apt keeps running in the background and finishes. Don't
  assume the upgrade failed.
- **`docker compose stop` is not enough when restart policies exist** — always
  re-list `docker ps` after stop and disable (`docker update --restart=no`) any
  container that came back before stopping it again.

## Durable state (as of 2026-08-05)

The `compose-autonomous-control-plane` stack on rabuntu is STOPPED, with
restart=no set on the offender. Do NOT restart it until the ssl_client zombie
leak in those container images is fixed — it re-breaks the Pi (threads pinned,
all forks fail) within hours.
