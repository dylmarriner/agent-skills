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

### Step 5b — Drive Still Present But ADVERTISING A DIFFERENT IDENTITY = controller in ROM/failsafe mode

Symptom: an internal SATA SSD that mounted fine for months is gone after an unclean shutdown / power cut. The device node still exists (e.g. `/dev/sdc`) but:

- `lsblk` shows a tiny capacity (~1 GB) and no FSTYPE
- `fdisk -l` reports no disklabel
- `blkid` finds nothing (`rc=2`), `/dev/disk/by-uuid/<old-uuid>` is missing
- `smartctl -i` says **SMART support is: Unavailable - device lacks SMART capability**
- the kernel log for the *same* ata port previously named the real drive and now names a controller part number; link speed often drops (6.0 → 3.0 Gbps, UDMA/133 → /100)

Prove it is the same drive on the same port (not a swapped cable):

```bash
journalctl -b -1 -k | grep -E "ata[0-9]+\.00: ATA-|SATA link up"   # previous boot: real model/serial
journalctl -b 0  -k | grep -E "ata[0-9]+\.00: ATA-|SATA link up"   # now: controller model
readlink -f /sys/class/scsi_device/<h>:0:0:0/device                        # PCI path, identical across boots
sudo dd if=/dev/sdX bs=512 count=1 | xxd | head        # ROM-mode IDENTIFY block leaks the controller name
```

A raw LBA0 dump containing a controller part number (e.g. `SM2259X`, `SM2258XT`, `SM59XT2A`) instead of an MBR/GPT is conclusive: the SSD controller is running its boot ROM, not its main firmware. Typical cause = DRAM-less SATA SSD (Silicon Motion SM2258XT/SM2259XT2, Phison S11, Realtek) losing power mid-write to its firmware/mapping metadata.

**Software CANNOT fix this — do not burn time on it.** All of these were tried on a real SM2259XT2 and re-read the ROM identity every time:

```bash
for h in /sys/class/scsi_host/host*; do echo "- - -" | sudo tee $h/scan; done   # rescan (useless)
sudo hdparm -Y /dev/sdX && sleep 5 && sudo hdparm -C /dev/sdX                  # standby/wake reset (useless)
sudo sh -c 'echo 1 > /sys/bus/pci/devices/0000:08:00.2/remove'; sleep 3; sudo sh -c 'echo 1 > /sys/bus/pci/rescan'  # full AHCI reset/COMRESET (useless)
```

Recovery ladder:

1. **True power cycle** — ACPI power-off, unplug mains, hold power 15-20 s to drain, boot. A warm `reboot` never works: the drive never loses power, so the ROM state survives. This is the only free shot.
2. **Controller firmware rebuild with the vendor MP tool** — for Silicon Motion, the SM2258XT/SM2259XT2 **MPTool** in ROM mode: read flash ID, supply the matching FDL for the onboard NAND, rebuild/ISP-download. Windows tooling; the tool must talk to the drive directly over SATA (or a supported USB-SATA bridge such as JMS578/ASM1153E). On a Linux host, give the SATA controller to a Windows VM with VFIO if its IOMMU group is clean (check `/sys/kernel/iommu_groups/*/devices` — a controller alone in its group is ideal, and keeps the host's other drives on a different controller untouched). Rebuilding usually yields a blank drive: expect to restore from backup, not to get the old file tree back.
3. **Warranty/RMA** — DRAM-less consumer SSDs are usually 3-year-warranty; firmware-level death is a valid RMA.

Note which services hardcode the mount path before declaring the outage fixed — e.g. `grep -rlI /media/<user>/<drive> ~/.config/systemd /etc/systemd` — they stay broken until the drive returns or the paths are repointed at a mirror/backup share.

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
