---
name: network-mounts
description: Mount, configure, and troubleshoot network filesystem mounts (CIFS/SMB, NFS). Covers credentials management, fstab entries with systemd automount, uid/gid mapping, and diagnostic workflow for unreachable/expired mounts.
metadata:
  tags: cifs, smb, nfs, fstab, mount, systemd, automount, network-storage
---

# Network Mounts (CIFS/SMB, NFS)

## When to use

- Mounting a remote SMB/CIFS share (NAS, Pi, Windows share)
- Setting up an automount that doesn't block boot when the remote is offline
- Troubleshooting mount failures, permission issues, or slow mounts
- Setting up a download pipeline that saves to a remote network share

**⚠️ If the user wants files to exist on both machines (not just remote access):** they need sync/replication, not a mount. Use `system/file-sync` (Syncthing) instead.

## Instructions

### Step 1: Install prerequisites

```bash
# CIFS/SMB
sudo apt-get install -y cifs-utils

# NFS
sudo apt-get install -y nfs-common
```

### Step 2: Create credentials file

For SMB/CIFS, create a credentials file (never put credentials directly in fstab):

```bash
cat > ~/.smbcredentials-<name> << 'EOF'
username=<smb_user>
password=<smb_password>
domain=WORKGROUP
EOF
chmod 600 ~/.smbcredentials-<name>   # critical — must be root-readable or owned by uid in mount
```

### Step 3: Mount point and test mount

```bash
sudo mkdir -p /mnt/<mount_name>
sudo chown $USER:$USER /mnt/<mount_name>

sudo mount -t cifs //<host>/<share> /mnt/<mount_name> \
  -o credentials=~/.smbcredentials-<name>,iocharset=utf8,\
     uid=$(id -u),gid=$(id -g),forceuid,forcegid,\
     file_mode=0755,dir_mode=0755,_netdev
```

Key options:
- `uid=$(id -u),gid=$(id -g)` — maps remote files to local user ownership
- `forceuid,forcegid` — overrides remote ownership regardless of server
- `_netdev` — tells systemd this is a network filesystem
- `iocharset=utf8` — proper Unicode filename handling

### Step 4: Auto-mount via fstab (systemd automount)

Rely on these mount options to start:
```
noauto,x-systemd.automount
```

**`noauto`** prevents blocking boot if the remote is unreachable.  
**`x-systemd.automount`** triggers mount-on-access — the mount happens lazily when the directory is first accessed (ls, cd, read, write).

Full fstab entry:

```
//<host>/<share> /mnt/<mount_name> cifs credentials=/home/<user>/.smbcredentials-<name>,iocharset=utf8,file_mode=0755,dir_mode=0755,uid=<uid>,gid=<gid>,forceuid,forcegid,_netdev,noauto,x-systemd.automount 0 0
```

### Step 5: Verify

```bash
# Trigger mount by accessing it
ls /mnt/<mount_name>/

# Check mount status — note: CIFS mounts don't show with 'grep smb',
# use 'grep cifs' or search by mount point name
mount | grep cifs
mount | grep <mount_name>

# Verify uid/gid mapping
ls -la /mnt/<mount_name>/ | head -5
```

### Step 6: Detect multi-drive Samba shares

A single Samba share can expose subdirectories that are **bind-mounted from different physical drives** on the remote server. Don't assume all subdirectories share the same backing storage.

```bash
# Compare per-directory available space
df -h /mnt/<mount_name>/*/
```

Look for different `Size` and `Avail` values in the output — those reveal separate physical drives. **Note:** the `Filesystem` column may still show the same `//host/share` for all of them even though they're on different drives — don't use that as evidence of a single disk.

When reporting mount status, always flag which subdirectories are on different storage so the user gets an accurate picture of free space.

To investigate further when you can't SSH into the remote (e.g. Tailscale policy blocks direct SSH), enumerate the SMB shares and check remote Samba version:

```bash
smbclient -L //<host> -U <user>%<pass> -m SMB3
```

This reveals all exported shares and their types, plus the Samba version string. Helpful when the remote is a Pi or NAS you can't log into directly.

## Steps (NFS — export from a remote Linux server)

### Step 2: Check and mount the source drive on the server

```bash
# SSH into the server
ssh user@<server>

# Find available drives
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL

# Check if the target partition is already mounted — it may be in fstab
# but not actually mounted (e.g. after boot failures)
mountpoint /srv/nas/main
df -h | grep <label_or_device>

# Mount manually if needed (assumes fstab entry exists)
sudo mount /dev/<device> /srv/nas/main

# Verify
df -h | grep <device>
```

### Step 3: Configure the NFS export on the server

```bash
# Add export entry — use the Tailscale IP of the client machine
echo '/srv/nas/main <client_tailscale_ip>(rw,sync,no_subtree_check,no_root_squash)' \
  | sudo tee -a /etc/exports

# Apply exports
sudo exportfs -ra

# Verify
sudo exportfs -v
```

Key options:
- `rw` — read-write access
- `sync` — writes are committed synchronously (safer than async)
- `no_subtree_check` — disables subtree checking for performance
- `no_root_squash` — preserves root privileges from the client (use for trusted Tailscale networks; omit for public-facing exports)
- Always restrict the export to a specific client IP. Never use `*` unless you know why.

### Step 4: Install client prerequisites and test mount

```bash
# On the client machine
sudo apt-get install -y nfs-common

# Create mount point
sudo mkdir -p /mnt/<mount_name>

# Test mount (specify NFSv4.2 for best performance)
sudo mount -t nfs -o vers=4.2 <server_tailscale_ip>:/export/path /mnt/<mount_name>

# Verify
df -h /mnt/<mount_name>
ls /mnt/<mount_name>/ | head -10

# Test write access
touch /mnt/<mount_name>/.test_write && rm /mnt/<mount_name>/.test_write
```

### Step 5: Auto-mount via fstab (systemd automount)

```bash
# Add to /etc/fstab:
# <server_ip>:<export_path> <mount_point> nfs defaults,nofail,x-systemd.automount,noatime,vers=4.2 0 0

echo '<server_tailscale_ip>:/srv/nas/main /mnt/<mount_name> nfs defaults,nofail,x-systemd.automount,noatime,vers=4.2 0 0' \
  | sudo tee -a /etc/fstab
```

Key options:
- `nofail` — don't block boot if the server is unreachable
- `x-systemd.automount` — lazy mount-on-access (won't block on directory access either)
- `vers=4.2` — NFSv4.2 (modern, better performance, uses a single port)
- `noatime` — skip access time updates for performance

## Pitfalls

### CIFS

- **Credentials file permissions**: If fstab is read as root but the credentials file is user-only, the mount will fail. Either make the creds file `chmod 600` owned by root, or reference the full path with the correct UID set in the mount options.
- **Slow mounts over Tailscale relay**: If the remote is behind a DERP relay (no direct Tailscale connection), operations like `ls` can time out. Use `tailscale ping` to check if direct connection is available.
- **Duplicate options in fstab**: When editing fstab, avoid duplicate uid/gid entries (e.g. both `uid=1000,gid=1000,forceuid,forcegid` appearing twice). Clean up with `sudo sed -i`.
- **Mount point already in use**: Run `sudo umount /mnt/<mount_name>` before remounting with different options.
- **No guest access**: Most private SMB shares require auth. Test with `smbclient -L //<host> -U <user>%<pass>` first.
- **PID file overhead**: If you have many CIFS mounts, monitor mount counts and stale connections.
- **Share visible but not accessible**: If a client can see a share in the browse list but gets access denied when opening it, the share likely lacks `guest ok = yes` while the client connects as guest. Diagnose with `sudo smbstatus` (check Username column for `nobody`) and `smbclient //host/share -N`. See `references/local-samba-server-troubleshooting.md` Step 8.

### NFS

- **No export defined → mount hangs**: If the server has no matching export entry, `mount -t nfs` will hang for ~90s then fail with "mount.nfs: Connection timed out". Always confirm with `showmount -e <server_ip>` or `exportfs -v` on the server first.
- **Drive not mounted on server → export path missing**: The NFS export path must exist and have a mounted filesystem behind it. If the drive isn't mounted, the export will be an empty directory. Use `df -h | grep <mount_point>` to verify.
- **root_squash by default**: Without `no_root_squash`, root on the client gets mapped to `nobody:nogroup`. For trusted Tailscale networks where you manage both ends, add `no_root_squash` to the export options.
- **Firewall ports**: NFSv3 requires `portmap` (111), `nfs` (2049), and `rpc.mountd` (various). NFSv4.x only needs port 2049 — much simpler for firewalls. Always prefer `vers=4` or `vers=4.2`.
- **UID/GID mapping**: NFS passes raw numeric UIDs/GIDs. Files created on the server as `rabuntu:rabuntu (1000:1000)` show as `kubuntux:kubuntux (1000:1000)` on the client if both use UID 1000 for their user. Mismatched UIDs cause permission issues — check with `id` on both machines if files show as owned by unexpected users.
- **Tailscale vs LAN IP**: Always use the Tailscale IP (100.x.x.x) for the mount address when both machines are on Tailscale. The Tailscale interface handles NAT traversal and encryption. Using LAN IPs may fail if the machines are on different subnets.

## Client access from Android

Android devices can access Samba shares through file manager apps. The easiest is **CX File Explorer** (free, Play Store). For the exact connection flow (no separate share name field — shares appear after auth), see:

- `references/android-smb-cx-file-explorer.md` — CX File Explorer vs SMB server: step-by-step connection, UI pitfalls, and port info

## Related reference documents

- `references/nfs-tailscale-setup-worked-example.md` — complete worked example: NFS export from a Linux server over Tailscale, client mount, fstab persistence (dev/sdb2 → rabuntu → kubuntux)

- `references/tube-site-video-extraction.md` — technique for downloading videos from sites with session-tokenized CDN URLs (custom Flowplayer/JWPlayer sites that yt-dlp can't parse)
- `references/local-samba-server-troubleshooting.md` — diagnosing and fixing the local Samba server when clients can't connect (dead services, missing /run/samba, NetBIOS name length > 15 killing nmbd, firewall, user DB)
