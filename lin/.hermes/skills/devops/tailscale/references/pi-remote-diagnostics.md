# Pi Remote Diagnostics & Optimization Session

Full walkthrough of diagnosing and optimizing a Raspberry Pi 5 over Tailscale when SSH is blocked by ACL, using Prometheus/node_exporter metrics and SMB as fallback.

## Initial Situation

- Pi 5 (pi5-deflab) running Debian 12 Bookworm, 8GB RAM
- SSH blocked by tailnet policy: `tailscale: tailnet policy does not permit you to SSH to this node`
- SMB shares accessible: `smbclient -L //100.68.0.96 -U rabuntu%admin`
- Web services: Pi-hole (80), Grafana (3000), Prometheus (9090), Node Exporter (9100), Forgejo (3001), CasaOS (81)

## Step 1: Remote Diagnostics via Metrics

Since SSH was blocked, I used Node Exporter and Prometheus to gather full system info:

```bash
# CPU: 4 cores @ 2.8GHz, governor=performance
curl -s http://100.x.x.x:9100/metrics | grep "node_cpu_scaling_governor"

# Load: 3.5/2.97/1.39 — high on 4 cores
curl -s http://100.x.x.x:9100/metrics | grep "^node_load"

# Memory: 8GB total, 3.6GB free
curl -s http://100.x.x.x:9100/metrics | grep "^node_memory_Mem"

# Disk: 220G root, 94% full (only 13.9G free!)
curl -s http://100.x.x.x:9100/metrics | grep "node_filesystem_avail_bytes" | grep "mountpoint=\"/\""

# Process top RAM consumers (via process_exporter on port 9256)
curl -s http://100.x.x.x:9256/metrics | grep 'namedprocess_namegroup_memory_bytes.*resident' | sort -t' ' -k2 -rn | head -20

# CPU hogs
curl -s http://100.x.x.x:9256/metrics | grep "namedprocess_namegroup_cpu_seconds_total.*user" | sort -t' ' -k2 -rn | head -20
```

## Step 2: SSH Access via Tailscale API

SSH was blocked because the machine is tagged `tag:infra` and the Pi had no SSH rule allowing access from infra-tagged machines. Fixed via Tailscale API:

1. Read current ACL: `GET /tailnet/-/acl`
2. Add `tag:pi` to `tagOwners`
3. Add SSH rule: `tag:infra → tag:pi`
4. Tag the Pi device: `POST /device/{id}/tags {"tags": ["tag:pi"]}`
5. SSH worked immediately after

## Step 3: System Optimization Script

Created and ran a comprehensive optimization script via SSH:

```bash
# Clean disk
apt clean && apt autoclean && apt autoremove -y --purge
journalctl --vacuum-size=50M
# Remove old kernels (keep current)
dpkg -l | awk '/^ii.*linux-image-[0-9]/ {print $2}' | grep -v "$(uname -r | sed 's/-[a-z].*//')" | xargs apt purge -y --purge
rm -rf /tmp/* /var/tmp/*

# Remove desktop environment
apt purge -y --purge xfce4 xfce4-* lightdm lxde-* lxappearance lxpanel pcmanfm openbox xorg xserver-xorg-*
# This freed ~400MB RAM and ~130MB disk

# Remove Pi-hole (prompt-based uninstall needed force)
DEBIAN_FRONTEND=noninteractive apt purge -y --purge pihole-meta
rm -rf /etc/pihole /opt/pihole /usr/local/bin/pihole /var/log/pihole*
systemctl stop pihole-FTL; systemctl disable pihole-FTL; rm -f /etc/systemd/system/pihole-FTL.service
deluser pihole

# Remove AdGuardHome
systemctl stop AdGuardHome; systemctl disable AdGuardHome
rm -rf /opt/AdGuardHome; deluser adguardhome

# Remove Ollama + LiteLLM
systemctl stop ollama; systemctl disable ollama
rm -f /usr/local/bin/ollama; rm -rf /usr/share/ollama /etc/ollama ~/.ollama
pkill -f litellm; rm -rf /home/*/.local/share/litellm-venv
```

**Results:** Disk 94% → 88% (and later 82% after eporner_batch move), RAM freed ~1.7G, load dropped from 3.5 to 1.9

### USB Drive I/O Error Recovery (Important Pattern)

During the 99G transfer, the USB drive disconnected with kernel errors:
```
Buffer I/O error on dev sdb2, logical block ...
EXT4-fs (sdb2): I/O error while writing superblock
Synchronize Cache(10) failed
```

The kernel power-cycled the USB port and re-detected the drive on a different device node:
- `sdb` → `sdc` → `sdd` (each reconnect = new device name!)
- Recovery auto-completed: `EXT4-fs (sdc2): recovery complete` → `mounted r/w`

**Critical fix**: Always use **UUID** in fstab, NOT device paths:
```
# WRONG — breaks on reconnection:
/dev/sdb2 /srv/nas/main ext4 defaults 0 2

# RIGHT — survives reconnection:
UUID=20b0cb3c-5a61-4a49-81d9-334ca7b56b58 /srv/nas/main ext4 defaults 0 2
```

**Post-recovery steps:**
1. Check if the device reconnected with a new name: `ls /dev/sd*`
2. Mount via UUID: `sudo mount UUID=xxx /mount/point`
3. Schedule fsck on next boot: `sudo tune2fs -c 1 /dev/sdX`
4. Test writes: `touch /mount/point/test_write`
5. Resume any interrupted operations (filesystem should be clean after recovery)

**Root cause pattern**: This specific Seagate Expansion Portable (0bc2:231a) has a known USB bridge quirk where sustained write loads cause the bridge to lock up. The kernel driver has a quirk entry (`Quirks match for vid 0bc2 pid 231a: 800000`) that handles the reconnect but the cache sync always fails.

### SMB Share Path Discovery (via rpcclient)

Before you can fix mergerfs or understand disk layout, find the actual server-side paths:

```bash
# List all shares with their server-side paths
rpcclient -U user%password 100.x.x.x -c "netshareenumall"

# Sample output:
# netname: Main   path: C:\srv\nas\main\shared
# netname: shared path: C:\mnt\shared
# netname: rabuntu path: C:\home\rabuntu  (Home Directories)
# netname: Backup  path: C:\media\devmon\backup-dev-ext4
```

This reveals the real filesystem paths vs. what SMB exposes. Compare with `df -h` and `mount` output to understand what's on which physical drive.

### Understanding the Share Mapping

The `shared` SMB share at `/mnt/shared` and `Main` at `/srv/nas/main/shared` may be DIFFERENT paths despite the name similarity. Always verify:

```bash
# On the target machine
readlink -f /mnt/shared /srv/nas/main/shared
# Check if they're bind mounts or separate dirs
mount | grep -E 'shared|nas|main'
```

### Mergerfs Pool Diagnosis

Check the current mergerfs config:

```bash
# From fstab
grep mergerfs /etc/fstab

# From running process
mount | grep mergerfs

# What's in the pool (branch paths)
cat /proc/mounts | grep mergerfs
```

The mergerfs pool format is `branch1:branch2:branch3 mountpoint fuse.mergerfs options`.
Branches are separated by colons. The first branch is the primary, and `category.create=epmfs` picks the branch with the most free space for new files.

### Fixing a Broken Mergerfs Pool

If the pool is missing a drive or has wrong branches:

1. **Update fstab** — replace the wrong branch path with the correct one:
```bash
sudo sed -i 's|/old/wrong/path|/correct/path|' /etc/fstab
```

2. **Move data** to the correct drive:
```bash
# Cross-filesystem move (copy + delete)
sudo rsync -a /source/path/ /destination/path/
sudo rm -rf /source/path
```
Note: `mv` across filesystems copies then deletes. For large datasets, `rsync` gives progress.

3. **Remount** the mergerfs:
```bash
sudo umount /mnt/shared/videos
sudo mount /mnt/shared/videos
```

4. **Verify**:
```bash
# Check pool size and free space
df -h /mnt/shared/videos
# Check file count visible
ls /mnt/shared/videos/ | wc -l
```

## Step 4: Mergerfs Pool Fix

The `/mnt/shared/videos` mergerfs pool had incorrect branches — it was merging two empty directories on root fs instead of including the 1.3TB external drive.

### Discovery
```bash
# Get share paths
rpcclient -U user%pass 100.x.x.x -c "netshareenumall"
# Shows: Main → C:\srv\nas\main\shared, shared → C:\mnt\shared
# Check fstab for mergerfs config
cat /etc/fstab | grep mergerfs
# Found: /mnt/shared/external-dev2/videos:/mnt/shared/videos-original
```

### Root Cause
- `/mnt/shared/external-dev2` was a bind mount to `/mnt/dev2` which is on the root filesystem (not the 1.3TB drive)
- The actual 1.3TB drive at `/srv/nas/main/videos` was empty and NOT in the mergerfs pool
- All 99G of videos sat in `videos-original` on root fs

### Fix
1. Update fstab:
```bash
# Replace the stale external-dev2 branch with the 1.3TB drive directory
sudo sed -i 's|/mnt/shared/external-dev2/videos:/mnt/shared/videos-original|/srv/nas/main/videos:/mnt/shared/videos-original|' /etc/fstab
```

2. Move files:
```bash
sudo mv /mnt/shared/videos-original/* /srv/nas/main/videos/
```

3. Remount mergerfs:
```bash
sudo umount /mnt/shared/videos
sudo mount /mnt/shared/videos
```

### USB Drive I/O Errors During Move
During the 99G transfer, the USB drive disconnected with "Buffer I/O error on sdb2" errors. The kernel power-cycled the USB port and the drive reconnected as a different device:
- `/dev/sdb` → `/dev/sdc`
- Fstab was already using UUID so it remounted fine
- Recovery log: "EXT4-fs (sdc2): recovery complete" → "mounted filesystem r/w"
- Scheduled fsck on next boot: `sudo tune2fs -c 1 /dev/sdc2`

### Final Fstab Entry
```
# Use UUID to survive device reconnection
UUID=20b0cb3c-5a61-4a49-81d9-334ca7b56b58 /srv/nas/main ext4 defaults,noatime,nofail,x-systemd.device-timeout=10 0 2
```
