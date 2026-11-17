---
name: disk-mount-repair
description: 'Diagnose and fix Linux disk mount failures: NTFS dirty bits, filesystem errors, fstab configuration, LDM/dynamic disks, and mount-point wiring.'
---

# Disk Mount Repair

Diagnose and fix drives that won't mount under Linux. Covers NTFS, ext4, vfat, and other common filesystems.

## Triggers

- User says "my drive won't connect", "disk not mounting", "can't access my external drive", "drive not showing up"
- `mount` command fails with filesystem type or dirty-bit errors
- Drive visible in `lsblk` but not mounted

## Workflow

### Step 1 — Gather Facts

```bash
# See all block devices, filesystems, mount points
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL

# Check partition table
sudo fdisk -l /dev/<DEVICE>

# Get UUIDs and filesystem types
sudo blkid /dev/<DEVICE>*

# Disk health
sudo smartctl -a /dev/<DEVICE>   # if smartmontools installed
```

### Step 2 — Check Kernel Messages

```bash
sudo dmesg | grep -iE '<DEVICE>|ntfs|mount|dirty|error' | tail -30
```

Key signals:
- `volume is dirty and "force" flag is not set!` — NTFS dirty bit, see Step 3
- `wrong fs type, bad option, bad superblock` — wrong fstype or corruption
- `It is recommened to use chkdsk` — filesystem needs repair

### Step 3 — NTFS Dirty Bit Resolution

The kernel `ntfs3` driver is strict about dirty flags. `ntfsfix` often **does not** fully clear the bit for `ntfs3`.

**A. Try ntfsfix anyway:**

```bash
sudo ntfsfix /dev/<PARTITION>
```

**B. Test mount without force:**

```bash
sudo mount -t ntfs3 /dev/<PARTITION> /mnt/<POINT>
```

If it fails even after `ntfsfix`, the `force` flag is required:

```bash
sudo mount -t ntfs3 -o force /dev/<PARTITION> /mnt/<POINT>
```

**C. Alternative driver (ntfs-3g FUSE):**

The older `ntfs-3g` FUSE driver is more lenient with dirty flags:

```bash
sudo mount -t ntfs-3g -o force /dev/<PARTITION> /mnt/<POINT>
```

### Step 4 — Add to fstab (Persistent Auto-Mount)

```bash
# Get UUID
sudo blkid /dev/<PARTITION>

# Append to fstab (ntfs3 with force for dual-boot safety)
echo "UUID=<UUID> /mnt/<POINT> ntfs3 uid=1000,gid=1000,force,iocharset=utf8,noatime 0 2" | sudo tee -a /etc/fstab
```

Test it:
```bash
sudo umount /mnt/<POINT>
sudo mount -a
df -h /mnt/<POINT>
```

### Step 5 — Alternative Filesystem Issues

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `wrong fs type, bad option, bad superblock` | Wrong fstype or corruption | Check fstype with `blkid`, try `-t` flag explicitly, or fsck |
| `Structure needs cleaning` | ext4 corruption | `sudo fsck.ext4 -f /dev/<PARTITION>` (umounted) |
| `Permission denied` | Wrong uid/gid in mount options | Add `uid=1000,gid=1000` to options |

### Step 6 — LDM / Dynamic Disks

If `fdisk` shows partition type `42` (SFS) or `fstype` is blank, the disk uses Windows **Dynamic Disk** (LDM). The individual partitions (e.g., sda1, sda2) may still be mountable independently as NTFS volumes — try each.

## Pitfalls

- **`ntfsfix` success ≠ clean**: The tool reports success but the kernel `ntfs3` driver may still reject the mount. Use `-o force` regardless.
- **Dual-boot Windows**: Windows fast-startup / hibernation sets the dirty bit every time. Always include `force` in fstab for dual-boot NTFS drives.
- **Dynamic Disks**: Linux cannot mount LDM spanned/striped/mirrored volumes as a single logical volume. Individual NTFS partitions within the LDM layout can still be mounted directly.
- **UUID changes**: NTFS UUIDs are stable, but if the drive was repartitioned the UUID changes — re-check with `blkid`.
- **sudo password**: Adding to fstab requires sudo. Use `tee -a` with `sudo -S` or ask the user for their password.

## Verification

```bash
# After mount
lsblk /dev/<DEVICE>
df -h /mnt/<POINT>
ls /mnt/<POINT>

# Test fstab (reboot-safe)
sudo mount -a && echo "fstab OK"

# Check for errors
sudo dmesg | tail -5
```
