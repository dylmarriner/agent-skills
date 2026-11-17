---
name: linux-process-exhaustion
description: "Use when 'Failed to fork' or hosts have runaway processes."
---

# Linux Process/Thread Exhaustion (fork bombs, zombie leaks)

Systematic methodology for when a Linux host runs out of process/thread slots.
Classic symptom: the box is up (SSH works) but every new process fails with
`FATAL -> Failed to fork`, `fork: retry: Resource temporarily unavailable`, or
`Resource temporarily unavailable`. apt, sudo, and even pipes die. This is NOT
apt corruption, NOT a repo problem, NOT network — it is the kernel refusing new
tasks.

## Trigger conditions

Use this skill when:
- `apt update` / `apt upgrade` fails with `FATAL -> Failed to fork`
- Any command fails with `fork: retry: Resource temporarily unavailable`
- A host is reachable but "nothing can start" — even simple commands die
- Process count is in the tens of thousands (healthy Linux: a few hundred to low thousands)
- Zombie count (`ps -o stat= | grep -c Z`) is in the thousands or tens of thousands

## Diagnostic pipeline

### 1) Confirm thread exhaustion — THE key check

```bash
cat /proc/sys/kernel/threads-max        # kernel cap (e.g. 63812)
ps -eLf --no-headers | wc -l            # current threads
```

If current ≈ max (e.g. 63811/63812), every fork fails. This is the root cause.
Also check memory (OOM can coexist but fork failure is the thread cap):
```bash
free -h
uptime
```

### 2) Find the swarm — what process and whose

```bash
# By process name — the bomb is usually ONE comm dominating
ps -e --no-headers -o comm= | sort | uniq -c | sort -rn | head -10

# By user — who owns the swarm
ps -e --no-headers -o user= | sort | uniq -c | sort -rn | head -10

# Zombies vs live, per user
ps -u <user> -o stat= | sort | uniq -c    # Z = zombie
```

### 3) Identify the spawner, not the zombies

Sample one victim and read its parent:
```bash
P=$(pgrep -u <user> <comm> | head -1)
cat /proc/$P/status | head -8          # State: Z (zombie)? PPid?
ps -p <PPid> -o pid,ppid,user,etime,comm,args
```

KEY INSIGHT: **zombies cannot be killed** — SIGKILL is a no-op on Z state.
Each zombie holds a task slot until its parent calls wait(). So you must kill the
PARENT (or the container/unit owning it); init then reaps the orphans. If the
spawner is short-lived, its children reparent to init but a live subreaper
(containerd-shim, s6, systemd unit) may hold them — check the histogram of
zombie PPids:
```bash
for z in $(pgrep -u <user> <comm> | head -200); do
  awk '/^PPid/{print $2}' /proc/$z/status 2>/dev/null
done | sort | uniq -c | sort -rn | head -5
```

### 4) Check for container / restart-policy traps

If a zombie's parent chain leads to a `containerd-shim` or the process runs
inside a container, the container's restart policy (`unless-stopped` / `always`)
will RESPAWN the spawner seconds after you kill it — the count climbs right back.

```bash
docker ps -a --format '{{.ID}} {{.Names}} {{.Status}}' | grep <container>
docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}'
```

## Remediation

### Kill the spawner (with sudo — other users' processes need root)

```bash
sudo kill -9 <spawner-pid>
# or by name across a user:
sudo pkill -9 -u <user> <comm>
```

`pkill` WITHOUT sudo on another user's processes fails per-PID with
"Operation not permitted" — and across 60K PIDs that is ~3.5 MB of error spam.
ALWAYS append `>/dev/null 2>&1` to swarm-wide pkill/kill.

### If the spawner is containerized — disable restart policy FIRST

```bash
docker update --restart=no <container>   # FIRST
docker stop <container>                  # THEN
```

For a whole compose project:
```bash
docker compose -p <project> stop
# Then verify nothing came back:
docker ps --filter label=com.docker.compose.project=<project> --format '{{.Names}} {{.Status}}'
# Any container still Up has a restart policy — disable and stop it again.
```

### Verify reaping

```bash
sleep 30
pgrep -u <user> <comm> | wc -l           # should trend to 0
ps -eLf --no-headers | wc -l             # should drop from cap to normal
ps -u <user> -o stat= | sort | uniq -c   # Z count → ~0
```

If zombies persist after killing the spawner, a live parent is still holding
them — repeat step 3/4 and kill that parent too.

### Then run the original command

apt / installs / anything that was failing will now work. Memory often recovers
too (swap drains, available RAM climbs) once the swarm is gone.

## Pitfalls

- **"Failed to fork" is thread exhaustion, not apt corruption** — do not touch
  apt lists/sources until you've checked `threads-max` vs current thread count.
- **Zombies can't be killed** — SIGKILL on Z state is a no-op. Kill the parent;
  init reaps the orphans. Zombie count not dropping = a live parent holds them.
- **`docker stop` alone is undone by restart policies** — `docker update
  --restart=no` FIRST, then stop. Always re-list containers after a compose stop.
- **Swarm-wide pkill without sudo spams "Operation not permitted" per PID** —
  use sudo, and always `>/dev/null 2>&1`.
- **Under severe exhaustion, pipes and subshells also fail** — even
  `ps | wc -l` gets "fork: retry". Keep remote commands to a single simple
  command per SSH call until threads free up.
- **`which <bin>` returning empty + `ls -la $(which <bin>)`** — the failed
  substitution makes `ls` list the whole home directory (can dump 100+ KB of
  junk into the session). Use `command -v` and guard/quote substitution.
- **SSH drop mid-upgrade is not failure** — a kernel upgrade can restart sshd;
  reconnect and check `pgrep -x apt`; apt finishes in the background.
- **Messagebus uid 100 is a common disguise** — a container running as uid 100
  shows up as `messagebus` in `ps -o user=`; the swarm's real owner is the
  container, not dbus. Check the container process tree before blaming dbus.

## References

- `references/fork-bomb-thread-exhaustion.md` — full worked case: Pi 5
  (rabuntu), 61K ssl_client zombies from a 21-container compose stack, exact
  commands and timing.
