# Example Pi SMB Share Layout

This is a reference layout from a Raspberry Pi 5 running Samba (smbd) with USB external storage bind-mounted into the share, plus mergerfs pooling.

## Pi Details

- Hostname: pi5-deflab
- Tailscale IP: 100.68.0.96
- User: rabuntu (also the SMB user)
- SMB share name: `[shared]`
- SMB share path: `/mnt/shared/`

## SMB Config (`/etc/samba/smb.conf`)

```ini
[shared]
   path = /mnt/shared
   browseable = yes
   read only = no
   guest ok = no
   valid users = rabuntu
```

## `/mnt/shared/` Directory Layout

```
/mnt/shared/
├── videos/             ← mergerfs pool (see below)
├── music -> /mnt/massive_storage/music   ← symlink to mass storage
├── external-dev/       ← bind mount of external drive partition 1 (exfat)
└── external-dev2/      ← bind mount of external drive partition 2 (ext4)
```

## External USB Drive (1.8TB, /dev/sdb)

| Device  | Size   | Filesystem | Direct Mount | SMB Bind Mount | Notes |
|---------|--------|------------|-------------|----------------|-------|
| sdb1    | 496G   | exfat      | /mnt/dev     | /mnt/shared/external-dev | Can cause kernel hangs on I/O issues |
| sdb2    | 1.3T   | ext4       | /mnt/dev2    | /mnt/shared/external-dev2 | Healthy, use /mnt/dev2/ for direct access |

## Mergerfs Pool: `/mnt/shared/videos`

The `videos/` directory is a mergerfs pool combining two branch directories:

| Branch | Path | Purpose | Free Space |
|--------|------|---------|-----------|
| ext4 partition | `/mnt/dev2/videos/` | New videos land here (epmfs policy) | ~934G |
| Original | `/mnt/shared/videos-original/` | Existing videos from before mergerfs | ~19G |

**New files go to ext4** due to `category.create=epmfs` (existing path, most free space).

### fstab entry for mergerfs

```fstab
/mnt/dev2/videos:/mnt/shared/videos-original /mnt/shared/videos fuse.mergerfs defaults,allow_other,category.create=epmfs,minfreespace=1G 0 0
```

**IMPORTANT**: Use `/mnt/dev2/videos` (raw partition path), NOT `/mnt/shared/external-dev2/videos` (bind mount path). If the exfat partition at `/mnt/shared/external-dev` goes down, the entire `/mnt/shared/` directory becomes un-traversable, which would prevent accessing the bind-mount path for the mergerfs pool.

### Creation steps (recovery)

If the pool needs to be recreated:

```bash
sudo mkdir -p /mnt/dev2/videos          # target dir on big partition
sudo mergerfs -o defaults,allow_other,category.create=epmfs,minfreespace=1G \
  /mnt/dev2/videos:/mnt/shared/videos-original /mnt/shared/videos
```

## Bind Mounts in /etc/fstab

```fstab
# External 1.8TB drive bind mounts
/mnt/dev  /mnt/shared/external-dev  none  bind  0  0
/mnt/dev2 /mnt/shared/external-dev2 none  bind  0  0
```

**Warning**: The exfat bind mount (`/mnt/dev → /mnt/shared/external-dev`) can make the entire `/mnt/shared/` directory un-traversable if the exfat filesystem enters a bad state. Access ext4 content directly via `/mnt/dev2/` in that case.

## Client-side Mount

On the client machine, the SMB share is mounted at `/mnt/pivideos/`:

```
//100.68.0.96/shared /mnt/pivideos cifs credentials=~/.smbcredentials-pi,... 0 0
```

So external drive content is accessible locally at:
- `/mnt/pivideos/external-dev/` (exfat, may be unreliable)
- `/mnt/pivideos/external-dev2/` (ext4, reliable)
- `/mnt/pivideos/videos/` (mergerfs pool via ext4 + original)

## Known Issues

- **exfat I/O hang = Pi freeze**: If the exfat partition locks up (unmount hangs, `ls` on mount point hangs), the Pi kernel can completely freeze — SSH and ping both fail. Only recovery is a hard power cycle. Afterwards, run `sudo fsck /dev/sdb1` before remounting.
- **Bind mount chain fragility**: If the exfat partition fails, its bind mount also fails. This can cascade to make `/mnt/shared/` untraversable, breaking SMB access to ALL subdirectories including the healthy ext4 partition and mergerfs pool.
