---
name: fstab-fuse-mounts
description: Correct fstab syntax for FUSE-based filesystem mounts. Avoids boot hangs from invalid fstype or missing nofail.
---

# FUSE Fstab Syntax

When adding FUSE-based filesystem mounts to /etc/fstab, follow these rules:

## fstype
Use the plain filesystem name (e.g. `exfat`), NOT `exfat-fuse` or `fuse.exfat`.

## Mount helper
Ensure `/sbin/mount.<fstype>` exists. For exfat-fuse:
```
ln -sf mount.exfat-fuse /sbin/mount.exfat
```

## nofail
External/non-essential drives MUST include `nofail,x-systemd.device-timeout=10` in the options column. Without nofail, systemd blocks boot waiting for the mount to succeed — if the drive isn't connected or the fstype is wrong, the system hangs indefinitely.

## Example
```
/dev/sdb1 /mnt/storage_media exfat defaults,noatime,uid=1000,gid=1000,fmask=0000,dmask=0000,nofail,x-systemd.device-timeout=10 0 0
```

## Why not `exfat-fuse` as fstype?
`mount` resolves fstype by looking for `/sbin/mount.<fstype>`. So `exfat-fuse` would look for `/sbin/mount.exfat-fuse`. While that binary exists, systemd's fstab parser may not handle non-standard fstypes correctly. Using `exfat` (the standard type) with the mount.exfat symlink is safer and more portable.
