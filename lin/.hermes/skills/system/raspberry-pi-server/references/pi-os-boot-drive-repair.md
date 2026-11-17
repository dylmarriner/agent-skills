# Pi OS Boot Drive Repair

Diagnosing and fixing a Raspberry Pi OS external boot drive that won't boot properly, has filesystem corruption, or suffers from boot delays.

## Quick Diagnostic Flow

```bash
# 1. Find the drive partitions
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL,MODEL

# 2. Identify Pi OS partitions (labelled bootfs + rootfs)
blkid /dev/sdX1 /dev/sdX2
# sdd1: LABEL="bootfs" TYPE="vfat"
# sdd2: LABEL="rootfs" TYPE="ext4"

# 3. Filesystem check (unmounted)
fsck -n /dev/sdX1    # vfat boot partition (read-only check)
fsck -n /dev/sdX2    # ext4 root partition
```

## Common Issues & Fixes

### 1. Boot partition dirty bit

**Symptom:** `fsck -n /dev/sdX1` shows "Dirty bit is set. Fs was not properly unmounted."

**Fix:**
```bash
fsck -a /dev/sdX1    # Auto-fix: clears dirty bit, writes changes
```

The dirty bit means the Pi was powered off uncleanly (power loss, kernel hang from exFAT I/O freeze, etc.). This is the most common Pi OS issue.

### 2. Boot sector/backup mismatch

**Symptom:** `fsck` reports "There are differences between boot sector and its backup. This is mostly harmless. Differences: (offset:original/backup) 65:01/00"

**Assessment:** Harmless on Raspberry Pi — the `65:01/00` difference is a known quirk of the RPi firmware writing a non-standard byte at offset 0x65. fsck.fat flags it but cannot auto-fix it. No action needed.

### 3. Boot delay from missing fstab UUIDs

**Symptom:** Pi takes 60-90 seconds longer to boot. `journalctl -b 0 --priority=err` shows:
```
Timed out waiting for device dev-disk-by\x2duuid-<UUID>.device
```

**Diagnosis:**
```bash
# Mount the Pi rootfs
mkdir -p /mnt/pi_root /mnt/pi_boot
mount /dev/sdX2 /mnt/pi_root
mount /dev/sdX1 /mnt/pi_boot

# Check fstab for missing UUIDs
cat /mnt/pi_root/etc/fstab
# Look for entries referencing drives not currently connected
# e.g. UUID=79FD-9DBB (exfat portable drive)
# e.g. UUID=20b0cb3c ... (NAS drive)
```

**Fix — add timeout to each missing drive entry:**
```bash
sed -i 's|UUID=<UUID> /path/<type> defaults,nofail|UUID=<UUID> /path/<type> defaults,nofail,x-systemd.device-timeout=10|' /mnt/pi_root/etc/fstab
```

Critical: every external USB drive entry MUST have `nofail` AND `x-systemd.device-timeout=<seconds>`. Without `nofail`, a missing drive prevents boot entirely. Without the timeout, systemd waits the default 90s for each missing device.

**Target UUIDs to check:**
- Any `UUID=` entry not matching a currently attached drive
- Exfat portable drives (common Pi accessory drives)
- USB backup drives that get rotated

### 4. Udev rule errors on Pi 5

**Symptom:** `journalctl -b 0 --priority=err` shows dozens of:
```
(udev-worker)[NNN]: sdXX /etc/udev/rules.d/60-iosched.rules:2 Failed to write ATTR{.../queue/scheduler}, ignoring: No such file or directory
```

**Cause:** The rule tries to set I/O scheduler via `ATTR{queue/scheduler}="none"` but on Pi 5 the kernel uses different sysfs paths for the block scheduler.

**Fix — add a path-existence test:**
```bash
# Original (spams errors):
# ACTION=="add|change", KERNEL=="sd*", ATTR{queue/scheduler}="none"

# Fixed (only writes when scheduler attribute exists):
ACTION=="add|change", KERNEL=="sd*", ATTR{queue/scheduler}=="?*", ATTR{queue/scheduler}="none"
```

The `ATTR{queue/scheduler}=="?*"` test checks if the attribute exists before attempting to write it. On Pi 5 where the path is different, the test fails silently and the write is skipped — no error.

### 5. Duplicated NFS exports

**Symptom:** `journalctl` shows `exportfs[NNN]: duplicated export entries:` followed by a path like `/media/devmon/backup-dev-ext4/cluster-storage` that doesn't exist.

**Fix:**
```bash
# Comment out or remove the broken export lines
sed -i 's|/media/devmon/backup-dev-ext4|#/media/devmon/backup-dev-ext4|' /mnt/pi_root/etc/exports
```

NFS exports referencing paths that don't exist are harmless (only add noise to logs), but cleaning them up reduces boot log spam.

### 6. Multiple boot cycles with wrong timestamps

**Symptom:** `journalctl --list-boots` shows many entries with timestamps from a date in the past (e.g. 2025-06-27 when the actual date is 2026-06-13).

**Cause:** The Pi's RTC battery is dead or missing. Without a hardware clock, the Pi uses the build timestamp of the kernel/initramfs as the boot time until NTP syncs. Multiple rapid reboots without NTP reaching a server (no network at boot, or brief power cycles) create many log entries with the same fake timestamp.

**Assessment:** Harmless. The Pi will sync time once it has a network connection and NTP reaches a pool server. To fix permanently, install an RTC battery or use `timedatectl set-ntp true`.

## Full Repair Procedure

```bash
# 1. Identify the Pi OS drive
DRIVE=/dev/sdd    # Update to your drive

# 2. Unmount if mounted
umount ${DRIVE}1 ${DRIVE}2 2>/dev/null

# 3. Check and repair both filesystems
fsck -a ${DRIVE}1      # vfat boot — auto-fix dirty bit
e2fsck -f -p ${DRIVE}2 # ext4 root — force+auto

# 4. Mount to inspect
mkdir -p /mnt/pi_boot /mnt/pi_root
mount ${DRIVE}2 /mnt/pi_root
mount ${DRIVE}1 /mnt/pi_boot

# 5. Fix fstab timeouts
# Check for entries without x-systemd.device-timeout
grep 'nofail' /mnt/pi_root/etc/fstab | grep -v 'x-systemd.device-timeout'

# Fix each missing timeout
sed -i 's|nofail,uid=|nofail,x-systemd.device-timeout=10,uid=|' /mnt/pi_root/etc/fstab

# 6. Fix udev rule if Pi 5
sed -i 's|ATTR{queue/scheduler}="none"|ATTR{queue/scheduler}=="?*", ATTR{queue/scheduler}="none"|' /mnt/pi_root/etc/udev/rules.d/60-iosched.rules 2>/dev/null

# 7. Fix NFS exports
sed -i 's|^/media/devmon|#/media/devmon|' /mnt/pi_root/etc/exports 2>/dev/null

# 8. Verify fixes
cat /mnt/pi_root/etc/fstab
cat /mnt/pi_root/etc/exports
cat /mnt/pi_root/etc/udev/rules.d/60-iosched.rules 2>/dev/null

# 9. Unmount
umount /mnt/pi_boot /mnt/pi_root
```

## Verification

After fixing, connect the drive to the Pi and power on. Check:
```bash
# Boot time should be normal (no 60-90s delays)
systemd-analyze blame | head -10

# No fstab timeout errors
journalctl -b 0 --priority=err | grep -i "timed out waiting"

# No udev noise
journalctl -b 0 --priority=err | grep -i "udev.*iosched" | wc -l
# Should be 0

# Filesystems clean
sudo fsck -n /dev/mmcblk0p2   # or the Pi's boot drive
```

## Key Principles

1. **Always add `nofail,x-systemd.device-timeout=10`** to every external USB drive entry in fstab. Missing drives cause 90s boot delays.
2. **fsck -a on vfat** (boot partition) auto-clears dirty bits. **e2fsck -f -p on ext4** (root partition) force-checks and auto-repairs.
3. **Pi 5 udev rules** need special handling for the I/O scheduler — the sysfs path changed from earlier Pi models.
4. **Unexpected unclean unmounts** on a Pi OS drive usually mean either a power loss, or an exFAT I/O freeze that locked the kernel (see `references/exfat-hang-recovery.md`).
