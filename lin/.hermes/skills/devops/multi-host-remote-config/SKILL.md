---
name: multi-host-remote-config
description: "Configure services, config files, env vars, systemd services, and shared Hermes agent profiles on multiple machines — SSH push, NAS-based canonical profile with symlinks, and NFS transport. Covers both push-to-each and pull-from-central patterns."
version: 1.4.0
author: Hermes
tags: [ssh, remote-config, fleet, devops, multi-host, setup]
trigger: When the user asks to configure a service, tool, API key, or shared Hermes profile on multiple machines — SSH push, NAS canonical profile with symlinks, or NFS transport. Especially when machines have heterogeneous install states (different users, packages, PATH setups).
---

# Multi-Host Remote Configuration via SSH

Class of work: push configuration (config files, env vars, API keys, service restarts) to multiple remote hosts via SSH, handling per-machine edge cases.

> **Syncthing P2P** is the preferred approach for keeping ~/.hermes/ config in sync across a Tailscale mesh. It replaces NFS shared profiles entirely — no mounting, no single point of failure, no boot delays. See `references/syncthing-p2p-sync.md` for the full setup.
>
> NFS remains documented for legacy/migration scenarios.

## Pattern Overview

The fundamental pattern is three-phase:

1. **WRITE** — create a local setup script that does one machine's complete work
2. **DEPLOY** — run that script across all machines in parallel
3. **VERIFY + FIX** — check results on each machine, resolve per-host edge cases

## Phase 1: Write the Setup Script

Create a local shell script (`/tmp/<task>-setup.sh`) that performs all steps for one machine via SSH. Key design decisions:

### Config Transport — Avoid Quoting Hell

SSH quoting is the #1 pain point. Nested quotes (`ssh user@host '...' "..." $var`) break in subtle ways. Solutions:

**Base64 encoding (recommended for JSON/small configs):**
```bash
CONTENT='{"api_key":"abc123","url":"https://api.example.com"}'
B64=$(printf '%s' "$CONTENT" | base64 -w0)
ssh user@host "echo '$B64' | base64 -d > ~/.app/config.json"
```

**Immediate exec (for commands without heredoc nesting):**
```bash
ssh user@host "mkdir -p ~/.app && printf '%s' '$CONTENT' > ~/.app/config.json"
```

**Bash -s piping (for multi-line scripts):**
```bash
ssh user@host 'bash -s' << 'EOF'
mkdir -p ~/.app
cat > ~/.app/config.json << 'INNER'
{"key":"value"}
INNER
EOF
```

### Idempotency Design

Each step should be safe to re-run:
- `mkdir -p` is inherently idempotent
- Config overwrites should be intentional — check if already set
- `systemctl restart` should check if service exists first
- Don't assume `~` expands to the same path across different SSH auth methods

## Phase 2: Parallel Deployment

Run the script across all target machines simultaneously in separate `terminal()` calls:

```bash
# Run ALL at once — independent, so parallel is safe
/tmp/setup.sh user1 host1 &
/tmp/setup.sh user2 host2 &
/tmp/setup.sh user3 host3 &
wait
```

Always use `timeout=120` for SSH scripts — auth prompts, slow networks, or apt-locked systems can delay.

## Phase 3: Verification & Edge Case Resolution

After the parallel run, check each machine individually. Common edge cases:

### Machine-Specific Issues Table

| Problem | Symptom | Fix |
|---------|---------|-----|
| `hermes` CLI not on PATH | Script reports "config updated" but `hermes config set` silently failed | Manually edit config.yaml + .env via SSH, or find/install the CLI binary |
| Broken Python editable install | `PermissionError` on `hermes` CLI import | `chown -R user:group ~/.hermes/hermes-agent/` |
| Pre-existing conflicting env vars | `.env` has an old key for the same service | Overwrite with `sed -i "s|^KEY=.*|KEY=newvalue|"` |
| Config written to wrong `$HOME` | SSH `~` expansion varies (root vs user, `su -` vs `ssh`) | Target explicit paths like `/root/.honcho/` or `/home/user/.honcho/` |
| `systemctl --user` not available | Gateway won't restart | Skip, note for manual start, or try `sudo systemctl` instead |
| Script ran but config file missing | Temp dir cleanup, signal interruption, or silent SSH failure | Re-execute the relevant SSH command directly |

### Verification Checklist

For each machine, verify:
1. **Config file** — `cat ~/.app/config.json` — correct content?
2. **Env vars** — `grep KEY ~/.hermes/.env` — correct value?
3. **Config integration** — `grep -A3 "^section:" ~/.hermes/config.yaml` or Python yaml parser — correct setting?
   - **Pitfall:** `grep -A3` only shows 3 lines after match. The `provider` line may be farther in. Use `grep -A10` or a Python yaml parser.
4. **Service status** — `systemctl --user is-active service-name`
5. **Live connectivity** — `curl` or `python3 -c "import module; print('OK')"` if applicable

### Python YAML Verification (more reliable than grep)

```bash
ssh user@host 'python3 -c "
import yaml
with open(\"~/.hermes/config.yaml\") as f:
    cfg = yaml.safe_load(f)
print(cfg.get(\"section\", {}).get(\"key\", \"NOT SET\"))
"'
```

## Shared Filesystem Profile Pattern (Legacy — Use Syncthing P2P Instead)

When all machines mount a shared NAS volume, the cleanest approach is a **canonical profile store + per-machine symlinks**. This avoids SSH quoting hell and gives every machine instant access to the same skills/plugins without per-machine sync scripts.

### Architecture

```
/mnt/nas/.hermes-profile/         # CANONICAL — one copy on NAS
  skills/                         #  merged from all machines
  plugins/                        #  merged from all machines
  .curator_backups/
  .hub/

Machine A: ~/.hermes/
  config.yaml    ← LOCAL (terminal backend, MCP server paths, device-specific)
  sessions/      ← LOCAL
  cron/          ← LOCAL
  logs/          ← LOCAL
  memories/      ← LOCAL (or use Synapse Memory for cross-device sync)
  skills →       /mnt/nas/.hermes-profile/skills   ← SYMLINKED
  plugins →      /mnt/nas/.hermes-profile/plugins  ← SYMLINKED
```

Each machine keeps its own `config.yaml` (machine-specific terminal backend, MCP server paths, device names) and its own `cron/`, `logs/`, `memories/`. Only `skills/` and `plugins/` are always symlinked to the NAS. `sessions/` can optionally be shared via per-machine subdirs (see `references/shared-profile-fleet.md` for the pattern).

### Step-by-Step Setup

#### 1. Create the canonical profile on the NAS

Pick a NAS path accessible by all machines. Then:

```bash
mkdir -p /mnt/nas/.hermes-profile/skills \
         /mnt/nas/.hermes-profile/plugins \
         /mnt/nas/.hermes-profile/.curator_backups \
         /mnt/nas/.hermes-profile/.hub
```

#### 2. Seed with the best-installed machine

From the machine with the most complete Hermes setup (typically your primary dev machine):

```bash
# Resolve symlinks so they work on all machines
cp -rL ~/.hermes/skills/* /mnt/nas/.hermes-profile/skills/
```

**Key pitfall:** Many Hermes skills are symlinks to OpenClaw hub skills (`../../.agents/skills/<name>`) or external repos. `cp -rL` resolves these to actual files. Without `-L`, the symlinks break on other machines.

#### 3. Merge skills from other machines

```bash
# On each additional machine
rsync -a --ignore-existing ~/.hermes/skills/ /mnt/nas/.hermes-profile/skills/
```

`--ignore-existing` keeps the first version seen (prefer the primary machine's versions on name collision).

#### 4. Handle broken symlinks

Other machines often have symlinks in their skills dir pointing to local paths that don't exist (e.g. `~/.agents/skills/<name>` where `.agents/` is not installed). The initial `cp -rL` on those machines will also fail for these. Workaround:

```bash
# On the source machine, resolve symlinks before copy
for s in /source/path/.hermes/skills/*; do
  name=$(basename "$s")
  if [ -L "$s" ]; then
    target=$(readlink -f "$s" 2>/dev/null) || continue  # broken symlink
    [ -d "$target" ] && cp -rL "$target" "/mnt/nas/.hermes-profile/skills/$name/"
  fi
done
```

#### 5. Symlink each machine

On each machine:

```bash
cd ~/.hermes
# Backup originals
mv skills skills.local
mv plugins plugins.local
# Symlink to canonical store
ln -s /mnt/nas/.hermes-profile/skills skills
ln -s /mnt/nas/.hermes-profile/plugins plugins
ln -s /mnt/nas/.hermes-profile/.curator_backups .curator_backups
ln -s /mnt/nas/.hermes-profile/.hub .hub
```

#### 6. Verify

```bash
ls ~/.hermes/skills/ | wc -l          # Should match NAS count
ls ~/.hermes/plugins/ | wc -l         # Should match NAS count
ls ~/.hermes/sessions/                # Local or per-machine NAS subdir
head -3 ~/.hermes/config.yaml         # Still machine-specific
```

### Decoupling: Breaking the NFS Dependency (Making a Machine Self-Contained)

When you need to detach a machine from the shared NFS profile so Hermes works fully offline (no NAS mount needed):

**Preferred approach: Syncthing P2P (see `references/syncthing-p2p-sync.md`).** The daemon syncs config P2P across all machines, no mount needed, no SPOF.

**Fallback approach — manual copy below** for one-time migration off NFS when Syncthing isn't available:

#### What's Dependent on NFS

Under `~/.hermes/`, these 5 dirs are typically symlinked to the NFS mount:

| Directory | Typical Size | Notes |
|-----------|-------------|-------|
| `skills` | 2.7 GB | The big one — 1340+ skill dirs |
| `plugins` | 19 MB | Hermes plugins |
| `sessions` | 258 MB | Symlinked to per-machine subdir on NAS (e.g. `sessions -> /nfs/sessions/lin`) |
| `.hub` | 24 MB | Skills hub cache |
| `.curator_backups` | 73 MB | Curator rotation backups |

Everything else under `~/.hermes/` (config.yaml, cron/, logs/, memories/, scripts/, state.db, .env, etc.) is already local.

#### Step 1: Verify Current State

```bash
cd ~/.hermes
for d in skills plugins sessions .hub .curator_backups; do
  if [ -L "$d" ]; then
    echo "SYMLINK: $d -> $(readlink $d)"
  else
    echo "LOCAL: $d"
  fi
done
```

#### Step 2: Copy All NFS Data Locally

```bash
# rsync each NFS path to a .local destination
rsync -a /mnt/nfs/path/skills/ ~/.hermes/skills.local/     # 2.7GB, ~2min
rsync -a /mnt/nfs/path/plugins/ ~/.hermes/plugins.local/   # fast
rsync -a /mnt/nfs/path/sessions/<hostname>/ ~/.hermes/sessions.local/  # only this machine's sessions
rsync -a /mnt/nfs/path/.hub/ ~/.hermes/.hub.local/
rsync -a /mnt/nfs/path/.curator_backups/ ~/.hermes/.curator_backups.local/
```

**Key:** Sessions are per-machine subdirectories on the NFS (e.g. `kubuntux/`, `lin/`, `macuntu/`, `rabuntu/`). Only copy the one matching the current host.

#### Step 3: Swap Symlinks for Local Directories

```bash
cd ~/.hermes
rm skills && mv skills.local skills
rm plugins && mv plugins.local plugins
rm sessions && mv sessions.local sessions
rm .hub && mv .hub.local .hub
rm .curator_backups && mv .curator_backups.local .curator_backups
```

#### Step 4: Verify

```bash
cd ~/.hermes
for d in skills plugins sessions .hub .curator_backups; do
  if [ -L "$d" ]; then
    echo "STILL SYMLINK: $d"
  else
    echo "LOCAL: $d ($(du -sh $d 2>/dev/null | cut -f1))"
  fi
done
```

#### Pitfalls

- **Local fallback dirs may already exist.** If you previously set up `skills.local/` as a fallback or partial copy, rsync merges them correctly — it adds missing files and overwrites conflicting ones with the NFS copy.
- **Sessions is the trickiest.** It's symlinked to a per-machine subdirectory (not the root). Make sure you copy `<hostname>/`, not the whole sessions directory, or you'll flood local storage with other machines' session files.
- **2.7 GB skills copy takes ~2 minutes** over NFS at ~20MB/s. The other dirs are fast. Don't start swapping symlinks until the skills rsync finishes — a partially-copied skills dir breaks Hermes.
- **Disk space check first.** Ensure local SSD has room: `df -h ~/`. Skills is 2.7GB, plus ~375MB for the other four. ~3.1GB total.
- **The NFS can still stay mounted** for cross-machine access even after decoupling. Just change fstab from `auto` to `noauto` so it never blocks boot: `sudo sed -i 's/,auto/,noauto/' /etc/fstab` (edit the NFS line specifically).

### Performance: Config Sync Options

| Transport | Pros | Cons | Use When |
|-----------|------|------|----------|
| **Syncthing (P2P)** | No mount, no SPOF, real-time, works offline | Initial sync bandwidth, daemon overhead | **Default — always preferred** |
| **NFSv4** | Zero-copy reads, kernel-native | Server must be up, boot dependency, setup complexity | Legacy migrations only |
| **CIFS/SMB** | Works everywhere, easy setup | Slow metadata ops, protocol overhead | Non-Linux NAS |
| **rsync-to-local** (cron) | Local disk speed, offline-capable | Sync delay, no instant propagation | Laptops that go offline |

**Recommendation:** Syncthing for all machines on a Tailscale mesh. NFS/CIFS only for read-only shared data too large to replicate (e.g. model caches).

### NFSv4 Server Setup

**Server** (the NAS host):

```bash
sudo apt-get install nfs-kernel-server
echo "/path/to/.hermes-profile 100.0.0.0/8(rw,sync,no_subtree_check,no_root_squash,fsid=0)" \
  | sudo tee /etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-server
```

**Client** (each machine):

```bash
sudo apt-get install nfs-common    # Linux
sudo mkdir -p /mnt/hermes-profile
sudo mount -t nfs4 <server>:/ /mnt/hermes-profile -o sync,noatime
```

Add to `/etc/fstab`:
```
<server>:/  /mnt/hermes-profile  nfs4  sync,noatime,noauto,soft  0 0
```

Use `noauto` for network filesystems — prevents boot delays when the NAS is down.

### What Stays Local Per Machine

| Item | Why Local |
|------|-----------|
| `config.yaml` | Terminal backend, MCP server paths, per-machine device names, provider credentials |
| `sessions/` | Per-machine session files (JSONL/JSON) — CAN be shared via per-machine subdirs on NAS if desired |
| `cron/` | Machine-specific scheduled jobs |
| `logs/` | Hermes gateway logs — per-machine |
| `memories/` | Local MEMORY.md/USER.md — Synapse Memory syncs these cross-device if configured |
| `.env` | API keys — machine-specific credential files |
| `hooks/` | Machine-specific webhook triggers |
| `pairing/` | Device pairing state |
| `scripts/` | Machine-specific automation scripts |

### Merging Skills from Multiple Machines: Pitfalls

- **Broken symlinks masquerade as skills.** Both `ls` and shell globs show them but `readlink -f` returns nothing. Always filter with `[ -d "$(readlink -f "$s")" ]` before copying.
- **Symlink resolution on CIFS.** CIFS mounts often can't create symlinks (`Operation not supported`). Always use `cp -rL` or rsync from the source machine, not on the NAS mount itself.
- **Count != usable skills.** `ls skills/ | wc -l` counts all entries including dotfiles, broken symlinks, and archive dirs. The actual Hermes-discoverable count is `find skills/ -maxdepth 2 -name 'SKILL.md' | wc -l`.
- **Name collisions.** If two machines have different skills with the same name, `--ignore-existing` keeps the first one written. Decide which machine is authoritative before merging.
- **External path dependencies.** Skills that reference external files (e.g. `understand-anything` plugin skills) break on machines without those external repos. Either copy the dep alongside the skill or document which external deps are needed.
- **Sub-skills at depth 3+.** Skills nested inside category directories (e.g. `skills/cybersecurity/analyze-memory/SKILL.md`) aren't individually discoverable by Hermes. They're accessible through the category parent if it exists. Flatten them to top-level if individual discovery matters.
- **Check ALL skill sources when merging.** `~/.hermes/skills/` is not the only source. Also check: `~/.agents/skills/` (OpenClaw hub), `~/Documents/` (git-cloned collections), plugin skill dirs (e.g. `~/.understand-anything/`), and any machine-specific external repos. The user's initial count may exceed yours because they know about sources you didn't check.
- **`rm -f` does not remove directories.** When replacing a sessions directory with a symlink, `rm -f sessions` leaves the directory in place. `ln -s /nas/path sessions` then creates a symlink INSIDE the directory instead of replacing it — giving `sessions/macuntu -> /nas/sessions/macuntu` rather than `sessions -> /nas/sessions/macuntu`. Use `rm -rf` or `mv sessions sessions.local` first. Sequence: copy to NAS, mv local aside, then ln -s.

## Pitfalls

- **Always extract credentials from `/proc/<pid>/environ` before killing credential-holding processes.** If a running service was started with env vars containing API keys (especially `env:KEY_REF` style configs), those keys may not be persisted anywhere else. Before any `kill`, `systemctl stop`, or `tmux send-keys C-c`, run: `cat /proc/<pid>/environ | tr '\0' '\n' | grep -i key` to capture them. Killing first and asking later means the key dies with the process — unrecoverable. This applies doubly to tmux-session services launched from interactive shells where env vars were not saved to any profile file.
- **`grep -A5` can miss YAML keys.** YAML parsers merge duplicate keys and handle deep nesting. A `provider: honcho` that shows up in Python yaml.safe_load might not appear under `grep "^memory:" -A5` if the key was added later in the file (YAML merge semantics). Always verify with a real YAML parser for mission-critical settings.
- **`$HOME` varies per SSH auth method.** `ssh root@host "echo ~"` gives `/root`. But if the script is run via a wrapper that sources `.bashrc`, `$HOME` could differ. Use explicit absolute paths in verification.
- **`base64 -w0` is GNU coreutils-only.** On macOS (BSD base64), use `base64 -b 0` or `base64 -i - -o - | tr -d '\n'`.
- **Parallel SSH can race on shared resources.** If two machines share an NFS mount or database, serialize the mutating steps.
- **`hermes config set` writes to `.env` for secrets, not config.yaml.** Verify both files — the API key goes to `.env`, the setting stays in `config.yaml`.
- **Stale pre-existing config values can mask new ones.** Always verify the actual value, not just the presence of a key.
- **Prefer extending over rewriting existing scripts/configs.** When asked to modify a script, config, or service that is already running, make the minimal additive change. The user trusts running infrastructure — a rewrite introduces new failure modes (import paths, edge-case handling, socket/PID file conflicts) that the original already handled. The correct approach: add the new feature/endpoint/tool as an extra entry alongside the existing ones, not replace the whole file. If the user asks "wouldn't you just add some extra tools", you went too deep.

## Replicating a Full Hermes Profile to Another Host

Task shape: "copy your config / skills / memories to `<user>@<host>`". Full
recipe with commands: `references/hermes-profile-replication.md`.

Rules that apply every time:

- **Resolve the target before touching it.** `tailscale status --json` maps a
  bare `100.x.y.z` to a hostname; probe candidate users with
  `ssh -o BatchMode=yes -o ConnectTimeout=5 <user>@<ip> 'id; hostname'`. Tailscale
  SSH authenticates as the **remote local user** — a nonexistent account returns
  `tailscale: failed to look up local user "<name>"` and closes port 22, which is
  a username error, not a connectivity failure.
- **Back up the target's existing `~/.hermes` before the first write**
  (`config.yaml`, `.env`, `memories/`, `*.md`) to `~/hermes-backup-<ts>` plus a
  `hermes-backup-latest` symlink. Targets normally already have a working install.
- **`.env`: merge, never overwrite.** Union of `KEY=` lines, source wins on
  conflict, target-only keys are preserved. A blind copy onto a target `.env`
  with more keys than yours silently deletes live credentials. Compare key counts
  first and report them.
- **Measure both ends with the SAME `--exclude` set** (`node_modules`, `.git`,
  `.venv`, `__pycache__`, `.curator_backups`). Source `skills/` is ~1.3G raw vs
  ~245M clean, so an unlike-for-like `du` looks like a failed transfer when the
  copy was complete.
- **Verify by content, not `rsync exit 0`:** `md5sum` config + identity files on
  both ends, and diff the `SKILL.md` relative-path sets with `comm -23` (empty =
  nothing missing). `comm -13` output is the target's pre-existing extras that a
  merge legitimately keeps — report it as kept, not as drift.
- **A running `hermes` process does not re-read `config.yaml`** — the changes
  take effect at next start. Say so instead of implying the target is live; state
  the backup path and exactly what was skipped.

## Remote Hermes Session Query

When you need to read session data from another machine's Hermes instance (e.g. "what did we talk about on lin"), **do not try `session_search` locally** — that only searches the local database. SSH into the target machine and query its `~/.hermes/state.db` SQLite database instead.

See `references/remote-hermes-session-query.md` for the full workflow:
- Discover sessions by keyword (LIKE or FTS5 trigram)
- Read session content (title, user messages, last exchanges)
- state.db schema reference (sessions + messages tables)
- Pitfalls: timestamp format, large DB performance, JSON-file coexistence

### Quick reference

```bash
# List recent sessions
ssh user@host 'python3 -c "
import sqlite3, os
db=os.path.expanduser(\"~/.hermes/state.db\")
c=sqlite3.connect(db).cursor()
c.execute(\"SELECT id,title,started_at FROM sessions ORDER BY started_at DESC LIMIT 10\")
for r in c.fetchall(): print(f\"{r[0][:30]} | {str(r[2])[:19]} | {str(r[1])[:60]}\")
"'
```

## Remotely Diagnosing a Frozen/Unresponsive Machine

When a machine on the mesh becomes unresponsive (remote SSH still works, local screen frozen), the root cause is almost never what `top` shows first. Follow this sequence.

### Step 1: Check iowait, not just CPU

The tunnel-client processes will show high CPU no matter what — they do crypto. **The real signal is iowait:**

```
# First line of top — look for %wa (iowait)
top -b -n1 | head -3
```

- **0-5% iowait** → CPU is the real problem (find the CPU hog)
- **20-80% iowait** → disk thrashing caused by something else. The high CPU on tunnel-client is a symptom, not the cause.
- **80%+ iowait** → machine is effectively frozen. Fix the I/O source first.

### Step 2: Find what's causing the I/O

Memory-leaking processes (especially Node.js) cause swap thrashing → iowait. Look for:

```
# Processes with absurd virtual memory
ps aux --sort=-%mem | head -10
# Virtual >10GB with resident << virtual = memory leak
```

Common culprits on a Hermes/OpenClaw mesh:
- **OpenClaw gateway** (`openclaw gateway --port`): can grow to 40-65GB virtual memory over days
- **OpenClaw direct bridge** (`openclaw-direct-bridge.ts`): same pattern
- **Duplicate tsx instances** (`tsx src/main.ts`): often 6+ copies, each at 44-55GB virtual

### Step 3: Kill with prejudice

```
# Kill the memory-leaking process
sudo kill -9 <pid>

# Check if it respawns (auto-restart via systemd)
sleep 2 && pgrep -a <process-name>
```

### Step 4: Find and disable the auto-restart

If the process respawns, it's managed by systemd (user or system level):

```
# Find the service
systemctl --user list-units --state=running | grep -i <name>
systemctl list-units --type=service --state=running | grep -i <name>

# Stop AND disable (kill alone is not enough — systemd restarts it)
systemctl --user stop <service-name>
systemctl --user disable <service-name>

# Verify dead
pgrep -a <name>   # should return nothing
```

### Step 5: Restore the service (when needed)

```
systemctl --user enable <service-name>
systemctl --user start <service-name>
```

### Step 6: Verify recovery

```
# CPU should be mostly idle
top -b -n1 | head -3
# Look for: %Cpu(s): ... >80 id  (idle)
# Look for: 0.0 wa  (iowait zero)

# Memory should have dropped
free -h
```

### Key insight: tunnel-client is usually innocent

The `tunnel-client` processes (hermes-tools, openclaw-tools profiles) always show 100-150% CPU during operation because they do crypto. **This is normal.** They only cause a freeze when another process (OpenClaw gateway, duplicated tsx instances) has memory-leaked to 40+GB and triggered swap thrashing. Kill the memory leak, not the tunnels.

## Examples

### Honcho Cloud Memory on 3 Hosts

See `references/honcho-fleet-setup.md` for a complete walkthrough including the exact script, edge cases encountered, and resolution steps.

### Tunnel-Client + Hermes MCP Bridge

See `references/tunnel-client-mcp-bridge-setup.md` for setting up OpenAI's `tunnel-client` wrapping Hermes's MCP direct bridge, including credential embedding strategy, making the bridge unrestricted (omniscient mode), and restart procedures.

## Related Skills

- `remote-desktop-access` — same fleet, different class of work: installing, credential-recovering, and proving GUI remote-desktop (RustDesk) access between mesh machines
- `linux-network-performance-tuning` — has a "Fleet Deployment Strategy" section for copying sysctl configs across machines
- `cross-machine-project-sync` — synchronizing git repos between machines (different class of work, same multi-host context)
- `linux-proxy-service-management` — managing systemd services on remote hosts
