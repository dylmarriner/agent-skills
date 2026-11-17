---
name: hermes-shared-profile
description: "Share skills, plugins, and curator state across multiple Hermes instances via network storage (NAS/CIFS) with per-machine local config. Covers NAS layout, symlink wiring, cross-machine skill merging, mount persistence, and the keep-local/share boundary."
version: 1.0.0
author: Hermes
metadata:
  hermes:
    tags: [hermes, multi-device, profile, nas, cifs, sharing, skills, plugins]
    related_skills: [hermes-agent, hermes-remote-setup]
---

# Hermes Shared Profile

Run a canonical Hermes profile directory on network storage (NAS) that all machines in a fleet symlink into. Skills, plugins, curator state, hub cache, and optionally sessions live on the share. Config, cron, logs, memories, and hooks stay per-machine.

**Transport: NFSv4 is strongly preferred over CIFS/SMB.** NFSv4 is kernel-native on Linux, has ~0.01s metadata latency (vs multiple seconds for CIFS on large skill directories), and all common client OSes (Linux, macOS) support it natively.

Useful when you have a Tailscale mesh or LAN with 2+ Hermes instances that should see the same skill library.

---

## Architecture

```
NAS (.hermes-profile/)
├── skills/              ←  Symlinked from every machine (merged from all sources)
├── plugins/             ←  Symlinked from every machine
├── .curator_backups/    ←  Shared curator state
├── .hub/                ←  Shared hub cache
└── sessions/            ←  Optional — per-machine subdirs (lin/, kubuntux/, etc.)

Each machine's ~/.hermes/
├── config.yaml          ←  LOCAL — machine-specific (MCP paths, terminal backend, device names)
├── sessions →           SYMLINK to NAS/machine-name/ (e.g. sessions/kubuntux/)
├── cron/                ←  LOCAL — per-machine schedules
├── logs/                ←  LOCAL — per-machine logs
├── memories/            ←  LOCAL per-machine (Synapse/Honcho handle cross-device sync)
├── hooks/               ←  LOCAL — per-machine hook scripts
├── skills →             SYMLINK to NAS
├── plugins →            SYMLINK to NAS
├── .curator_backups →   SYMLINK to NAS
└── .hub →               SYMLINK to NAS
```

### Sessions: shared NAS with per-machine isolation

Session files (JSONL chat logs + JSON request dumps) are individual append-only files, not a shared SQLite DB — so there's no concurrency concern. Each machine gets its own subdirectory under `sessions/` on the NAS, and symlinks `~/.hermes/sessions` to it:

```
sessions/
├── lin/          ← lin's sessions
├── kubuntux/     ← kubuntux's sessions
├── rabuntu/      ← rabuntu's sessions
└── macuntu/      ← macuntu's sessions
```

This keeps all session data in one place for backup/disk accounting while preventing cross-machine corruption.

## Prerequisites

Load the `hermes-agent` skill first — this skill references Hermes paths (`~/.hermes/config.yaml`, `plugins/`, `skills/`) and the CLI reference there covers Hermes-specific commands you may need during setup.

## First-Time Setup

### 1. Create the canonical profile on the NAS

Pick the machine that hosts the share (call it the NAS host). Create the directory:

```bash
mkdir -p /path/to/nas/.hermes-profile/skills \
         /path/to/nas/.hermes-profile/plugins \
         /path/to/nas/.hermes-profile/.curator_backups \
         /path/to/nas/.hermes-profile/.hub
```

### 2. Merge skills from all machines

**CRITICAL: scan ALL skill sources, not just ~/.hermes/skills/.** Skills may live in:

| Source | Location | How to find |
|--------|----------|-------------|
| ~/.hermes/skills/ | Primary Hermes skills | `ls ~/.hermes/skills/` |
| ~/.agents/skills/ | OpenClaw agent skills | `ls ~/.agents/skills/ 2>/dev/null` |
| External symlink targets | Documents/, etc. | `find ~/.hermes/skills/ -type l -exec readlink -f {} \; 2>/dev/null` |
| ~/Documents/ repos | External git clones | `ls ~/Documents/*/skills/ 2>/dev/null` |

Start with the primary machine (the one with your preferred skill set). Copy its skills resolving symlinks to actual files/dirs:

```bash
cp -rL ~/.hermes/skills/* /path/to/nas/.hermes-profile/skills/
```

Then scan for additional sources the primary machine's skills might NOT cover:

```bash
# Copy OpenClaw agent skills that weren't symlinked individually
for d in ~/.agents/skills/*/; do
  name=$(basename "$d")
  [ -d "/path/to/nas/.hermes-profile/skills/$name" ] && continue
  [ -L "$d" ] && [ ! -e "$d" ] && echo "SKIP broken symlink: $name" && continue
  cp -rL "$d" "/path/to/nas/.hermes-profile/skills/$name"
done
```

Then, for each additional machine, rsync unique skills (skip any name that already exists):

```bash
# Run ON the additional machine, targeting the shared NAS path:
rsync -a --ignore-existing ~/.hermes/skills/ /path/to/nas/.hermes-profile/skills/
```

**ALSO scan additional machines for OpenClaw/hub skills:**
```bash
ssh <machine> "rsync -a --ignore-existing ~/.agents/skills/ /path/to/nas/.hermes-profile/skills/"
```

**First-copy-wins** — when names collide, the first machine's version is kept (it was copied first, and `--ignore-existing` skips it on subsequent machines). To see which skills would collide:

```bash
# On the additional machine — find unique skills NOT yet in shared dir:
comm -23 <(ls ~/.hermes/skills/) <(ls /path/to/nas/.hermes-profile/skills/)
```

**⚠ Broken symlinks in `comm` output**: `comm` lists broken symlinks as "unique" because the symlink name exists locally but the target doesn't. These files can't be copied and produce `Input/output error` or `No such file or directory` errors. Filter them out:

```bash
for s in $(comm -23 <(ls ~/.hermes/skills/) <(ls /path/to/nas/.hermes-profile/skills/)); do
  target=$(readlink ~/.hermes/skills/"$s" 2>/dev/null || echo "$s")
  if [ -L ~/.hermes/skills/"$s" ] && [ ! -e "$target" ]; then
    echo "BROKEN: $s -> $target (nowhere)"
  else
    echo "UNIQUE: $s"
  fi
done
```

**Name collisions after merge**: if two machines had different skills with the same name, the first-copy-wins rule may hide one. Hermes detects these at runtime with an "Ambiguous skill name" error. To find and fix:

```bash
find /path/to/nas/.hermes-profile/skills/ -maxdepth 2 -name SKILL.md | \
  sed 's|.*/skills/||; s|/SKILL.md||' | sort | uniq -d
```

If colliding skills exist, rename the less-important one to a unique name.

Copy metadata files too:
```bash
cp ~/.hermes/skills/.bundled_manifest /path/to/nas/.hermes-profile/skills/ 2>/dev/null
cp ~/.hermes/skills/.curator_state /path/to/nas/.hermes-profile/skills/ 2>/dev/null
cp ~/.hermes/skills/.usage.json /path/to/nas/.hermes-profile/skills/ 2>/dev/null
```

### 3. Merge plugins (same pattern)

```bash
cp -rL ~/.hermes/plugins/* /path/to/nas/.hermes-profile/plugins/
# Then from additional machines:
rsync -a --ignore-existing ~/.hermes/plugins/ /path/to/nas/.hermes-profile/plugins/
```

### 4. Wire each machine — symlink and keep locals

**⚠ CRITICAL: use `mv`, never `rm`.** If you `rm -f sessions` you permanently delete the session directory. Always `mv <dir> <dir>.local` first — this creates a backup AND reveals any existing symlinks vs directories.

On each machine, back up the old dirs then symlink:

```bash
cd ~/.hermes

# Back up and symlink skills
mv skills skills.local
ln -s /path/to/nas/.hermes-profile/skills skills

# Back up and symlink plugins
mv plugins plugins.local
ln -s /path/to/nas/.hermes-profile/plugins plugins

# Back up and symlink curator state
mv .curator_backups .curator_backups.local 2>/dev/null
ln -s /path/to/nas/.hermes-profile/.curator_backups .curator_backups 2>/dev/null

# Back up and symlink hub cache
mv .hub .hub.local 2>/dev/null
ln -s /path/to/nas/.hermes-profile/.hub .hub 2>/dev/null

# Optionally share sessions on NAS with per-machine subdir
# First create the machine's subdir on the NAS:
#   mkdir -p /path/to/nas/.hermes-profile/sessions/<machine-name>
#   cp ~/.hermes/sessions/* /path/to/nas/.hermes-profile/sessions/<machine-name>/
# Then:
#   mv sessions sessions.local
#   ln -s /path/to/nas/.hermes-profile/sessions/<machine-name> sessions
```

Keep local on each machine (do NOT symlink these):
- `config.yaml` — machine-specific paths, terminal backend, MCP server definitions, device-specific env
- `cron/` — per-machine scheduled jobs
- `logs/` — per-machine log files
- `memories/` — local memory files (cross-device sync handled by Honcho/Synapse)
- `hooks/` — per-machine hook scripts
- `audio_cache/`, `image_cache/` — local caches

### 5. Mount persistence

**Recommended: NFSv4** (significantly faster metadata performance than CIFS for skill directories with 1000+ entries).

Set up the NFS server on the NAS host machine:

```bash
# On the NAS host:
sudo apt-get install -y nfs-kernel-server
echo "/path/to/nas/.hermes-profile 100.0.0.0/8(rw,sync,no_subtree_check,no_root_squash,fsid=0)" \
  | sudo tee /etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-server
```

On each client machine, add the NFS mount to fstab:

```bash
# On client machines with NFSv4:
echo "nas-host-ip:/ /mnt/hermes-profile-nfs nfs4 sync,noatime,vers=4.2,noauto 0 0" \
  | sudo tee -a /etc/fstab
sudo mkdir -p /mnt/hermes-profile-nfs
sudo mount -t nfs4 nas-host-ip:/ /mnt/hermes-profile-nfs -o sync,noatime,vers=4.2
```

Alternatively, **CIFS/SMB** (works when NFS isn't available, e.g. NAS is a Windows share):

```bash
# On machine <host>
echo "//nas-host/share  /mnt/shared-hermes  cifs  sec=none,uid=<uid>,gid=<gid>,file_mode=0775,dir_mode=0775,noauto,soft,nounix 0 0" \
  | sudo tee -a /etc/fstab
```

Use `noauto` for network filesystems — they shouldn't block boot if the NAS is down. Mount manually or add a systemd mount unit for automatic startup after the network is up.

On the NAS host itself, the path is local (no mount needed).

## Adding a New Machine Later

1. Mount the NAS share (CIFS/fstab as above)
2. Do NOT copy local skills — just symlink
3. The shared dir already has everything merged
4. Preserve the machine's existing config.yaml, sessions, cron, memories

## What to Watch For

| Concern | Handling |
|---------|----------|
| Concurrent curator runs | Shared `.curator_backups` handles this; only one runs at a time |
| Symlink resolution on network FS | Hermes follows symlinks transparently on both NFS and CIFS |
| NFS metadata latency | ~0.01s for 1300-entry `ls` — negligible. CIFS is ~1-5s for the same operation |
| NAS host is down | Skills/plugins/sessions become empty dirs. Local config/cron/memories still work. Use `noauto` in fstab so boot isn't blocked |
| Skill hub installs | When installing from hub, the skill lands in the shared dir — available everywhere instantly |
| Name collisions after merge | Two machines may have different skills with the same name. First-copy-wins hides one. Detect with `find ... -name SKILL.md | sort | uniq -d`. Rename the less-important skill to un-collide |
| `rm` instead of `mv` destroys data | Always `mv <dir> <dir>.local`. A `rm -rf sessions` deletes the entire session database permanently |

## Verification

After wiring, verify on each machine:

```bash
# Skills accessible
ls ~/.hermes/skills/ | head -5

# Plugins accessible
ls ~/.hermes/plugins/ | head -5

# A known skill loads
skill_view(name='<any-skill>')

# Local paths intact
head -3 ~/.hermes/config.yaml
ls ~/.hermes/sessions/ 2>/dev/null
```
