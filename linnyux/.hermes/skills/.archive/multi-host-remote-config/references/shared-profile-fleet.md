# Shared Hermes Profile Fleet Deployment

Reference deployment: 4-machine Hermes mesh sharing skills/plugins/sessions via NAS canonical profile with NFSv4 transport.

**Last updated:** 2026-07-15 — Migrated from CIFS to NFSv4, added shared sessions with per-machine isolation.

## Machine Inventory

| Host | Role | Hermes User | Profile Path | NAS Access |
|------|------|-------------|--------------|------------|
| lin (HP Pavilion) | Primary dev | lin | /home/lin/.hermes/ | /mnt/hermes-profile-nfs (NFSv4) |
| kubuntux | NAS host, dev | kubuntux | /home/kubuntux/.hermes/ | /media/kubuntux/DEVELOPMENT1/ (local) |
| rabuntu (Pi5) | NAS mount client | root | /root/.hermes/ | /mnt/hermes-profile-nfs (NFSv4) |
| macuntu | NAS mount client | macuntu | /home/macuntu/.hermes/ | /mnt/hermes-profile-nfs (NFSv4) |

## Canonical Profile Location

```
NAS path:    /media/kubuntux/DEVELOPMENT1/.hermes-profile/
NFS export:  /media/kubuntux/DEVELOPMENT1/.hermes-profile  (fsid=0)
NFS client:  <server>:/  /mnt/hermes-profile-nfs  (nfs4, sync, noatime, vers=4.2)
Server IP:   100.93.75.87 (Tailscale)
```

## Contents

- **Skills:** 1324 directories, 1205 Hermes-discoverable (depth-2 SKILL.md), 3044 total SKILL.md at all depths
- **Plugins:** 21 from merged lin + macuntu sources
- **Sources merged:** lin (102 skills), kubuntux (921 unique), macuntu (40 unique), .agents/skills/ (252 unique from OpenClaw), cybersecurity-skills (769 sub-skills)
- **Size:** ~2.6G

## Transport: NFSv4

All clients mount NFSv4 via Tailscale. CIFS was the initial transport but NFS was significantly faster.

### Performance Comparison

| Operation | CIFS | NFSv4 |
|-----------|------|-------|
| `ls skills/` (1324 entries) | ~0.8-1.5s | ~0.013-0.056s |
| SKILL.md first load | noticeable lag | instant |

NFSv4 eliminates SMB protocol overhead for metadata operations, which is the primary path for skill discovery.

### Server Setup (kubuntux)

```bash
sudo apt-get install nfs-kernel-server

# /etc/exports:
/media/kubuntux/DEVELOPMENT1/.hermes-profile 100.0.0.0/8(rw,sync,no_subtree_check,no_root_squash,fsid=0)

sudo exportfs -ra
sudo systemctl restart nfs-server
```

Key: `fsid=0` makes this the NFSv4 pseudo-filesystem root, so clients mount `server:/` not `server:/path/to/.hermes-profile`.

### Client Setup (lin, rabuntu, macuntu)

```bash
sudo apt-get install nfs-common      # Linux
sudo mkdir -p /mnt/hermes-profile-nfs
sudo mount -t nfs4 100.93.75.87:/ /mnt/hermes-profile-nfs -o sync,noatime,vers=4.2
```

Use the Tailscale IP (100.x.x.x) not the hostname — NFS RPC resolution can fail on `kubuntux` hostname if the NFS server doesn't have reverse DNS.

#### fstab Entry

```
100.93.75.87:/  /mnt/hermes-profile-nfs  nfs4  sync,noatime,vers=4.2,noauto  0 0
```

`noauto` — network filesystem should not block boot if the NAS is down. Mount manually or add a systemd mount unit `mnt-hermes\x2dprofile\x2dnfs.mount` with `After=network-online.target`.

### Hostname Resolution Fix

If `rpcinfo -p kubuntux` gives "RPC: Unknown host", the Tailscale hostname isn't resolvable via NFS. Fix: add to `/etc/hosts` on each client:

```
100.93.75.87  kubuntux
```

Or use the IP directly in mount commands (shown above).

## Merge Technique

### 1. Seed from Primary Machine

Always resolve symlinks so files are real on the NAS (not machine-specific relative paths):

```bash
cp -rL /home/lin/.hermes/skills/* /mnt/nas/.hermes-profile/skills/
```

`-L` (follow symlinks) is critical — many skills are symlinks to OpenClaw hub skills at `../../.agents/skills/<name>` or external git repos.

### 2. Merge from Secondary Machines

```bash
ssh kubuntux 'rsync -a --ignore-existing ~/.hermes/skills/ \
  /media/kubuntux/DEVELOPMENT1/.hermes-profile/skills/'
```

`--ignore-existing` — on name collision, keep the first version (typically from the primary machine).

### 3. Merge OpenClaw Agent Skills

After seeding from `~/.hermes/skills/`, also check `~/.agents/skills/` — this contains skills installed by OpenClaw that may not have symlinks in the Hermes skills dir:

```bash
rsync -a --ignore-existing ~/.agents/skills/ /mnt/nas/.hermes-profile/skills/
```

### 4. Check for External Skill Sources

Dylan's lesson: when told "you have 1500+ skills" but your count shows ~1000, you missed sources. Check:

- `~/.agents/skills/` (OpenClaw hub skills)
- `~/Documents/` (git-cloned skill repos)
- `~/.understand-anything/` (plugin-provided skills)
- Any `cybersecurity-skills` or similarly named collections
- Any skill dirs OTHER machines might have (kubuntux had 2.6G of hub-installed skills)

### 5. Handle Broken Symlinks

Secondary machines often have symlinks pointing to local paths that don't exist on the primary (e.g. `~/.agents/skills/<name>` without `.agents/` installed). Detect and skip:

```bash
for s in /source/.hermes/skills/*; do
  name=$(basename "$s")
  [ -L "$s" ] && target=$(readlink -f "$s" 2>/dev/null) || continue  # skip broken
  [ -d "$target" ] && cp -rL "$target" "/mnt/nas/.hermes-profile/skills/$name/"
done
```

Broken symlinks show up in `ls` counts but have zero content. They cannot be copied and are effectively lost — check if the target exists on any machine first.

## Per-Machine Wiring

### Lin (primary)

```bash
cd ~/.hermes
mv skills skills.local && mv plugins plugins.local
rm -f .curator_backups .hub
ln -s /mnt/hermes-profile-nfs/skills skills
ln -s /mnt/hermes-profile-nfs/plugins plugins
ln -s /mnt/hermes-profile-nfs/.curator_backups .curator_backups
ln -s /mnt/hermes-profile-nfs/.hub .hub
```

### Kubuntux (NAS host — local filesystem)

```bash
cd ~/.hermes
mv skills skills.local && mv plugins plugins.local
ln -s /media/kubuntux/DEVELOPMENT1/.hermes-profile/skills skills
ln -s /media/kubuntux/DEVELOPMENT1/.hermes-profile/plugins plugins
```

### Rabuntu & Macuntu (NFS clients)

Same as lin but unmount CIFS first if switching:

```bash
# Cleanup old CIFS mount (if any)
sudo umount /mnt/kubuntux-nas 2>/dev/null
# NFS already mounted at /mnt/hermes-profile-nfs

cd ~/.hermes
rm -rf skills plugins .curator_backups .hub 2>/dev/null
ln -s /mnt/hermes-profile-nfs/skills skills
ln -s /mnt/hermes-profile-nfs/plugins plugins
ln -s /mnt/hermes-profile-nfs/.curator_backups .curator_backups
ln -s /mnt/hermes-profile-nfs/.hub .hub
```

## Shared Sessions

In addition to skills/plugins, sessions can be consolidated onto the NAS using **per-machine subdirectories**.

### Architecture

Shared session storage is NOT a single shared SQLite DB — each machine creates individual JSON/JSONL session files. Storing them in a shared NFS directory with per-machine subdirs is safe because:

- Each file is written by only one machine (the one that owns the session)
- Files are append-only JSONL or single-write JSON request dumps
- No concurrent write to the same file across machines

```
/mnt/hermes-profile-nfs/sessions/
  lin/        ← 693 files
  kubuntux/   ← 819 files
  rabuntu/    ← 1 file
  macuntu/    ← 1 file
```

### Setup

```bash
# Create per-machine subdirs once (from any machine)
mkdir -p /mnt/nas/.hermes-profile/sessions/{lin,kubuntux,rabuntu,macuntu}

# On each machine, copy existing sessions and symlink
cp ~/.hermes/sessions/* /mnt/nas/.hermes-profile/sessions/$(hostname)/
mv ~/.hermes/sessions ~/.hermes/sessions.local
ln -s /mnt/nas/.hermes-profile/sessions/$(hostname) ~/.hermes/sessions
```

### Pitfalls

- **Symlink creation failure with `rm -f` on directories.** `rm -f` does NOT remove directories. Use `rm -rf` (carefully) or `mv` to rename first, then create the symlink. A failed symlink creates a file/directory INSIDE the original sessions dir rather than replacing it — e.g. `sessions/macuntu -> /nas/sessions/macuntu` with session files alongside it, instead of `sessions -> /nas/sessions/macuntu`.
- **Backup first.** If `mv sessions sessions.local` fails (e.g. read-only NFS, permissions), the `ln -s` creates a dangling symlink and the original files are at risk. Sequence: `cp` to NAS → `mv` local aside → `ln -s` to NAS.
- **macuntu sessions were lost** in this deployment because `rm -rf sessions` was run before the cp completed (sessions.local was empty). Always verify the copy first.

## Verification Checklist

After wiring each machine:

```bash
# Skills count matches NAS
ls ~/.hermes/skills/ | wc -l        # Should match: NFS count (1324)

# Plugins count
ls ~/.hermes/plugins/ | wc -l       # Should match: 21

# Session isolation
ls ~/.hermes/sessions/              # Only THIS machine's files

# Local config intact
head -3 ~/.hermes/config.yaml       # Machine-specific

# Symlink check
readlink -f ~/.hermes/skills        # Should point to NFS path

# NFS mount
mount | grep hermes-profile          # Should show nfs4
```

## What Stays Local Per Machine

| Item | Why Local |
|------|-----------|
| `config.yaml` | Terminal backend, MCP server paths, per-machine device names, provider credentials |
| `cron/` | Machine-specific scheduled jobs |
| `logs/` | Hermes gateway logs — per-machine |
| `memories/` | Local MEMORY.md/USER.md — Synapse Memory syncs these cross-device |
| `.env` | API keys — machine-specific credential files |
| `hooks/` | Machine-specific webhook triggers |
| `pairing/` | Device pairing state |
| `scripts/` | Machine-specific automation scripts |

## Fallback / Rollback

Each machine has a local backup of the pre-shared state. To revert:

```bash
cd ~/.hermes
rm skills plugins .curator_backups .hub
mv skills.local skills
mv plugins.local plugins
```

## Merge Pitfalls

- **Broken symlinks masquerade as skills.** `ls` shows them but `readlink -f` returns nothing. Filter with `[ -d "$(readlink -f "$s" 2>/dev/null)" ]` before copying.
- **Symlink resolution on CIFS.** CIFS mounts can't create symlinks (`Operation not supported`). Use `cp -rL` from the source machine, not on the NAS mount itself.
- **Count != usable skills.** `ls skills/ | wc -l` counts dotfiles, broken symlinks, archive dirs. Hermes-discoverable count is `find skills/ -maxdepth 2 -name 'SKILL.md' | wc -l`.
- **Name collisions.** `--ignore-existing` keeps the first version. Decide which machine is authoritative before merging.
- **External path dependencies.** Skills referencing external files (understand-anything plugin skills) break on machines without those repos. Copy the dep alongside or document which external deps are needed.
- **Sub-skills at depth 3+.** Skills inside category dirs (e.g. `skills/cybersecurity/analyze-memory/SKILL.md`) aren't individually Hermes-discoverable. Flatten to top-level if individual discovery matters.
- **Broken symlinks on secondary machines.** Macuntu had 15 dangling symlinks to `~/.agents/skills/` — a directory that existed on the primary (lin) but not on macuntu. These cannot be resolved and represent permanently lost skills unless the source machine's `.agents/skills/` is also copied to the merge target.
