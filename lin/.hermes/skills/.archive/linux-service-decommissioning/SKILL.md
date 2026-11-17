---
name: linux-service-decommissioning
description: "Remove a Linux service permanently and prove it is gone."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags:
      - linux
      - systemd
      - services
      - teardown
      - apt
      - resource-reclamation
    related_skills:
      - system-cleanup
      - linux-laptop-performance-tuning
---

# Linux Service Decommissioning

## When to Use

- User says "permanently remove X", "uninstall X and make sure it doesn't come back", "stop X for good".
- User asks to reclaim the CPU/RAM a background service or daemon is consuming.
- A service was killed already but reappeared after login or reboot.
- You need to prove a removal is complete rather than assert it.

Not for: tuning a service you intend to keep (see `linux-laptop-performance-tuning`), or reclaiming disk space (see `system-cleanup`).

## Why this is not just `kill`

Removing a service is a teardown, not a `kill`. Stopping the process is the first of seven steps; the rest are what stop it coming back on next login or reboot. Always finish with an absence proof — "I killed it" is not the same as "it is gone".

## Procedure

### 1. Identify before you kill

A process that looks like stray junk is often a live dependency, and a systemd-managed one just respawns. Run this gate on every candidate first.

```bash
# Managed or orphan? ppid 1 = orphan (safe to reap); ppid = systemd = stop the UNIT instead.
ps -o pid,ppid,args -p <PID>
systemctl --user status <name> 2>/dev/null
systemctl status <name> 2>/dev/null
systemctl --user list-units --all 2>/dev/null | grep -i <name>

# Declared dependency? Names like *-mcp-server, desktop-commander, docling-mcp-server,
# mcp-server-filesystem read like stray desktop utilities but are servers the agent
# is actively using. Grep the agent's own config before touching them.
grep -rniE '<process-name>' ~/.hermes/config.yaml

# What is genuinely orphaned?
ps -eo pid,ppid,comm --no-headers | awk '$2==1 {print $1, $3}'
```

Leave it alone if the name appears in the agent's own config, or its parent is a live agent process. Only reap processes with `ppid 1` and no config reference. When in doubt, report the classification and ask — a killed dependency is a silent, confusing outage later.

### 2. Stop and disable BOTH scopes

A user-scope unit survives a system-level disable, and vice versa. Do both.

```bash
systemctl --user disable --now <name>
sudo systemctl disable --now <name>
pkill -x <name>
```

### 3. Confirm the install source, then purge

`dpkg -l` tells you nothing about a binary that was hand-dropped. Ask the file itself who owns it, or you will "purge" a service and leave it fully intact.

```bash
dpkg -l | grep <name>
snap list 2>/dev/null | grep <name>
dpkg -S "$(command -v <name>)" 2>/dev/null || echo "NOT package-owned — hand-installed"
ls -la /usr/local/bin/<name> /usr/bin/<name> 2>/dev/null
```

- Package-owned → `sudo apt-get purge -y <name> && sudo apt-get autoremove -y`.
- Hand-installed (`dpkg -S` says not owned, binary in `/usr/local/bin`) → `sudo rm -f` the binary and the unit by hand; nothing else knows it exists. A hand-written `/etc/systemd/system/<name>.service` is the tell, and `systemctl cat <name>` prints the `ExecStart=` path that names the exact binary to delete.
- Either way, if the service was never *running*, `apt purge` alone is not a completed removal — the unit, the account, and the data dirs all survive it.

### 4. Wipe config AND state

A package purge leaves both behind, and stale state can resurrect behaviour if anything reinstalls the package.

```bash
rm -rf ~/.config/<name> ~/.local/state/<name>
```

### 5. Remove leftover unit files, reload, clear failures

```bash
sudo rm -f /etc/systemd/system/<name>*.service \
           /lib/systemd/system/<name>*.service \
           /usr/lib/systemd/system/<name>*.service
sudo systemctl daemon-reload
sudo systemctl reset-failed; systemctl --user reset-failed
```

### 6. Remove the service account and the data dirs it owns

Daemons that keep models, indexes, or caches under their own UID leave two copies — one in the user's home, one under `/usr/share/<name>` owned by the system account. Neither is removed by `apt purge` when the install was not a package.

```bash
find ~/.<name> /usr/share/<name> -type f 2>/dev/null | head   # confirm what is actually there first
sudo userdel <name>
sudo groupdel <name>          # run separately — userdel often skips it, see pitfalls
rm -rf ~/.<name>
sudo rm -rf /usr/share/<name>
```

Check the data dir's *size* before deleting, not after: a few tens of KB with no blobs means the service was installed but never populated, which is worth saying in the report ("never actually deployed") — it is a different claim from "removed a working install".

### 7. Deregister it from the consumer configs

A stopped-and-deleted service is still advertised as an endpoint by whatever references it. Step 1's grep is for *protection*; repeat it now for *erasure* and remove every hit, or the next session reads a config that points at a port nothing listens on.

Hermes' own `~/.hermes/config.yaml` is guarded: the file-write tools refuse it outright (`Refusing to write to Hermes config file … Agent cannot modify security-sensitive configuration`). Use the CLI instead, which validates as it writes:

```bash
hermes config unset providers.<name>     # remove a whole provider block
hermes config set <dotted.path> <value>
hermes config get <dotted.path>
hermes config check                      # confirm the file still parses after the edit
```

Do not hand-edit that file or route around the guard with an in-place editor — `hermes config check` at the end is what proves the YAML still loads.

## Verification: an absence proof, not a glance

Every line must read gone/0. Run it and report the result rather than asserting success.

```bash
for c in "binary:$(command -v <name> || echo none)" \
         "dpkg:$(dpkg -l 2>/dev/null | grep -c <name>)" \
         "sysunits:$(systemctl list-unit-files 2>/dev/null | grep -ci <name>)" \
         "userunits:$(systemctl --user list-unit-files 2>/dev/null | grep -ci <name>)" \
         "procs:$(pgrep -xc <name> 2>/dev/null || echo 0)" \
         "cfg:$([ -e ~/.config/<name> ] && echo PRESENT || echo gone)" \
         "state:$([ -e ~/.local/state/<name> ] && echo PRESENT || echo gone)" \
         "homedata:$([ -e ~/.<name> ] && echo PRESENT || echo gone)" \
         "share:$([ -e /usr/share/<name> ] && echo PRESENT || echo gone)" \
         "user:$(getent passwd <name> || echo gone)" \
         "group:$(getent group <name> || echo gone)" \
         "listen:$(ss -ltnp 2>/dev/null | grep -c ':<port>')"; do echo "  $c"; done
```

`listen` is the one that catches a half-removal: a live listener on the service's port means something else respawned it or a second copy is installed under a different name. `getent passwd`/`group` catch the account left by step 6 when `userdel` declined to remove the group.

Then confirm the resource actually came back, with two `/proc` samples rather than one `ps` reading:

```bash
# resolve it from the skills tree rather than hardcoding $HOME
python3 "$(find ~/.hermes/skills -name cpu-snapshot.py -print -quit)"
```

`ps %CPU` is a lifetime average, so it reports a just-removed hog at full tilt and reports a currently-pegging one as idle right after a restart. Compare `free -h` and `swapon --show` before and after for the RAM/swap delta.

## Reclaiming resources without uninstalling

When the user wants the load gone but may still want the tool ("not using anything except X right now"), stop and disable rather than purge — reversible with one `enable --now`:

```bash
systemctl --user stop <unit>; systemctl --user disable <unit>
```

Say explicitly in the report which services were stopped-but-not-removed and the exact command to bring each back.

Desktop daemons parked in zram are the cheapest win: a notification daemon holding 500M+ of swap frees it on `pkill -x <name>`, and `~/.config/autostart/<name>.desktop` with `Hidden=true` stops it returning at login.

## Pitfalls

- **`pkill -f` is a footgun; use `pkill -x`.** `-f` matches the pattern anywhere on ANY command line, including the shell running your own command — `pkill -f plasma-discover` terminates your own session mid-script. The tool reports this as a bare SIGTERM (exit -15) with no output, which reads like a mystery failure. `-x` matches the exact `comm` name only. Inspect with `pgrep -a -x <name>`.
- **Names over 15 characters cannot be matched by `-x` or `ps -C`.** The kernel truncates `comm` (e.g. `docling-mcp-server` → `docling-mcp-ser`), so exact matching silently finds nothing. Match on `args` (`ps -eo pid,args | grep <name>`) or kill by PID for those.
- **A source checkout in `$HOME` sharing the service name is not part of the package.** `~/<name>` survives every step above. Delete it only when the tool is gone for good, and name it in the report so the user knows a repo was deleted, not just a service.
- **Removing a sync/peer daemon is a one-sided change.** Remote machines keep listing this node as a peer forever. Tell the user which hosts still have stale entries so they can clean those too.
- **`userdel` will not remove a group that has other members.** It prints `group <name> not removed because it has other members` and exits **0**, so a `&&`-chained script reports success with the group still present. Service accounts added to `video`/`render` for GPU access always hit this. Always run `groupdel <name>` as a separate command and verify with `getent group <name>`.
- **"Installed" and "deployed" are different claims — check for a listener, not a directory.** A binary plus a systemd unit plus a models dir looks deployed, but `systemctl status` reading `inactive (dead)` and `du -sh` on the data dir reading tens of KB means nothing ever ran and nothing was ever pulled. Report that distinction explicitly; the user asking for a removal wants to know whether anything was actually live.
- **A service can be handed to you already inactive.** `disable --now` on a dead unit succeeds silently, so it proves nothing about your teardown — the unit file, the account, and `/usr/share/<name>` are the parts still there.
- The agent's own config is a removal target, not just a protection gate. See step 7.
- **A stopped-but-enabled unit returns at next login.** `stop` alone is not a fix; `disable` is what makes it stick. Verify with `systemctl --user is-enabled <unit>`.
- **Purging can leave `--failed` entries for the removed unit**, which looks like the removal half-failed. `reset-failed` on both scopes clears it.

## Related

Depth for the surrounding work lives in two separate skills — this one owns teardown and verification only:

- `system-cleanup` — disk reclamation tiers, docker/snap/cache cleanup, ext4 reserved-block trap.
- `linux-laptop-performance-tuning` — CPU governors, thermals, sysctl tuning, boot-latency analysis, memory-pressure diagnosis, background-load audit.
