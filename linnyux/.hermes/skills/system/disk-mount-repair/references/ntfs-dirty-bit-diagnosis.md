# NTFS Dirty Bit Diagnosis — Session Reference

## Original Problem

Drive `/dev/sda` (WDC WD1001FALS, 1TB) visible in `lsblk` but not mounted. Two partitions:
- `sda1` — 465.5G, no filesystem type, part of Windows Dynamic Disk (LDM, type=42 SFS)
- `sda2` — 465.6G, NTFS, label "Stuff", not mounted

## Key Diagnostic Output

```
# lsblk showed drive but no mount point
sda    931.5G
├─sda1 465.5G
└─sda2 465.6G ntfs         Stuff

# dmesg revealed the true issue
ntfs3: sda2: volume is dirty and "force" flag is not set!
ntfs3: sda2: It is recommened to use chkdsk.
```

## Commands Used

```bash
# Initial investigation
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL
sudo blkid /dev/sda*
sudo fdisk -l /dev/sda
sudo dmesg | grep -iE 'sda|ntfs|mount'

# ntfsfix ran successfully but DID NOT clear the flag for ntfs3
sudo ntfsfix /dev/sda2
# Output: "NTFS volume version is 3.1. NTFS partition /dev/sda2 was processed successfully."

# After ntfsfix, mount without force still failed
sudo mount -t ntfs3 /dev/sda2 /mnt/development
# Error: wrong fs type, bad option... volume is dirty

# Force mount succeeded
sudo mount -t ntfs3 -o force /dev/sda2 /mnt/development

# fstab entry for persistent auto-mount
UUID=7066CC1066CBD54E /mnt/development ntfs3 uid=1000,gid=1000,force,iocharset=utf8,noatime 0 2
```

## Key Lesson

`ntfsfix` reports success but the kernel `ntfs3` driver may still see the volume as dirty. Always use `-o force` in fstab for NTFS drives that dual-boot or have been accessed by Windows. This is expected behavior, not a bug.
