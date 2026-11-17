# Session Example: Merged 4-Machine Fleet (lin/kubuntux/rabuntu/macuntu)

This reference records the exact implementation from the session that built this shared profile.

## Fleet Layout

| Machine | OS | Hermes user | Skills before | Plugins before | Transport |
|---------|----|-------------|---------------|----------------|----------|
| lin | Kubuntu | lin | 108 (41 symlinks to OpenClaw `.agents/skills/`) | 11 plugins | NFSv4 via Tailscale |
| kubuntux | Kubuntu | kubuntux | 966 (2.6G — from OpenClaw hubs, Claude Code, etc.) | 0 plugins/enabled | Local (NAS host) |
| rabuntu | Raspberry Pi OS | root | empty | empty | NFSv4 via Tailscale |
| macuntu | Ubuntu | macuntu | 935 (126M) | 11 plugins | NFSv4 via Tailscale |

## Merged Result

- **Skills:** 1324 dirs, 1205 top-level SKILL.md, 3044 total SKILL.md at all depths (~3GB)
- **Plugins:** 21 (merged from lin + macuntu)
- **Sessions:** shared on NAS with per-machine subdirs

## NAS Location

The canonical profile lives on kubuntux (`100.93.75.87`) at `/media/kubuntux/DEVELOPMENT1/.hermes-profile/`. All clients mount via NFSv4 at `/mnt/hermes-profile-nfs/`.

## Key Commands Used

### Merge skills — scan ALL sources

```bash
# Step 1: Copy primary machine's skills (resolve symlinks)
cp -rL ~/.hermes/skills/* /path/to/nas/.hermes-profile/skills/

# Step 2: Also copy OpenClaw `.agents/skills/` (not all are symlinked)
rsync -a --ignore-existing ~/.agents/skills/ /path/to/nas/.hermes-profile/skills/

# Step 3: Merge from each additional machine
ssh <machine> "rsync -a --ignore-existing ~/.hermes/skills/ /path/to/nas/.hermes-profile/skills/"
ssh <machine> "rsync -a --ignore-existing ~/.agents/skills/ /path/to/nas/.hermes-profile/skills/"

# Step 4: Copy symlink targets from external paths (Documents/, etc.)
find ~/.hermes/skills/ -type l -exec sh -c '
  t=$(readlink -f "$1")
  n=$(basename "$1")
  [ -d "$t" ] && [ ! -d "/path/to/nas/.hermes-profile/skills/$n" ] && cp -rL "$t" "/path/to/nas/.hermes-profile/skills/$n"
' _ {} \;
```

### Merge plugins

```bash
cp -rL ~/.hermes/plugins/* /path/to/nas/.hermes-profile/plugins/
ssh <machine> "rsync -a --ignore-existing ~/.hermes/plugins/ /path/to/nas/.hermes-profile/plugins/"
```

### Set up shared sessions with per-machine subdirs

```bash
# Create per-machine subdirs
mkdir -p /path/to/nas/.hermes-profile/sessions/{lin,kubuntux,rabuntu,macuntu}

# Copy each machine's sessions to its subdir
cp ~/.hermes/sessions/* /path/to/nas/.hermes-profile/sessions/lin/

# Then symlink ALWAYS using mv (never rm):
mv ~/.hermes/sessions ~/.hermes/sessions.local
ln -s /path/to/nas/.hermes-profile/sessions/lin ~/.hermes/sessions
```

**⚠ CRITICAL: use `mv`, not `rm`.** On macuntu, `rm -f sessions` in the wiring script permanently deleted 46 session files. There is no recovery. Always `mv <dir> <dir>.local`.

### Symlink wiring (run on each machine)

```bash
cd ~/.hermes
mv skills skills.local && ln -s /path/to/nas/.hermes-profile/skills skills
mv plugins plugins.local && ln -s /path/to/nas/.hermes-profile/plugins plugins
mv sessions sessions.local && ln -s /path/to/nas/.hermes-profile/sessions/<machine> sessions
mv .curator_backups .curator_backups.local 2>/dev/null; ln -s /path/to/nas/.hermes-profile/.curator_backups .curator_backups
mv .hub .hub.local 2>/dev/null; ln -s /path/to/nas/.hermes-profile/.hub .hub
```

## NFS Setup

### Server (kubuntux — NAS host)

```bash
sudo apt-get install -y nfs-kernel-server
echo "/media/kubuntux/DEVELOPMENT1/.hermes-profile 100.0.0.0/8(rw,sync,no_subtree_check,no_root_squash,fsid=0)" \
  | sudo tee /etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-server
```

### Client (lin, rabuntu, macuntu)

```bash
sudo apt-get install -y nfs-common
sudo mkdir -p /mnt/hermes-profile-nfs
sudo mount -t nfs4 100.93.75.87:/ /mnt/hermes-profile-nfs -o sync,noatime,vers=4.2
```

fstab entry:
```
100.93.75.87:/ /mnt/hermes-profile-nfs nfs4 sync,noatime,vers=4.2,noauto 0 0
```

### Performance comparison

| Operation | CIFS | NFSv4 |
|-----------|------|-------|
| `ls skills/` (1324 entries) | 2-5 seconds | 0.01-0.05 seconds |
| `find -name SKILL.md` (3000+ files) | 10-30 seconds | 0.1-0.5 seconds |

## Name Collisions

After merging all 4 machines, `skill-creator` collided between:
- OpenClaw `~/.agents/skills/skill-creator/`
- A Hermes skill installed from another source

Detect collisions:
```bash
find /path/to/nas/.hermes-profile/skills/ -maxdepth 2 -name SKILL.md | \
  sed 's|.*/skills/||; s|/SKILL.md||' | sort | uniq -d
```

## What's Kept Local Per Machine

| Path | Reason |
|------|--------|
| `config.yaml` | MCP paths, terminal backend, device names, provider configs |
| `cron/` | Machine-specific schedules |
| `logs/` | Per-machine logs |
| `memories/` | Local file memories (Synapse/Honcho handle cross-device sync) |
| `hooks/` | Per-machine hook scripts |
| `audio_cache/`, `image_cache/` | Local caches |

## Original CIFS Setup (for reference)

Before the NFSv4 migration, shares were mounted via CIFS:

```bash
# SMB mount
sudo mount -t cifs //100.93.75.87/DEVELOPMENT1 /mnt/development1 \
  -o sec=none,uid=1000,gid=1000,file_mode=0775,dir_mode=0775
```

fstab:
```
//100.93.75.87/DEVELOPMENT1  /mnt/development1  cifs  sec=none,uid=1000,gid=1000,file_mode=0775,dir_mode=0775,noauto,soft,nounix 0 0
```

Rabuntu (root user) CIFS:
```
//100.93.75.87/DEVELOPMENT1  /mnt/kubuntux-nas  cifs  sec=none,uid=0,gid=0,file_mode=0775,dir_mode=0775,noauto,soft,nounix 0 0
```
