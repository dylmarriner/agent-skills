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

## NTFS: use the kernel `ntfs3` driver, not ntfs-3g
ntfs3 (kernel) is much faster than the ntfs-3g FUSE driver and accepts the same ownership options:
```
UUID=B8BC56F2BC56AAA0 /media/user/volume ntfs3 uid=1000,gid=1000,umask=022,noatime,windows_names,nofail,x-systemd.device-timeout=10 0 0
```
`umask=` is accepted by ntfs3 (it expands to dmask/fmask). `windows_names` only blocks *creating* files whose names are invalid on Windows. Without `nofail`, an NTFS volume on a drive that is absent or dirty will hang boot.

### Dirty NTFS volume blocks rw mounts
The single most common reason a Windows data drive refuses to mount rw:
`ntfs3: volume is dirty and "force" flag is not set!` (ntfs-3g: "Please run chkdsk").
That flag survives an unclean Windows shutdown / fast startup. Linux cannot run chkdsk, so clear the flag before the mount:
```
sudo ntfsfix -d /dev/disk/by-uuid/<UUID>
```
To make automount survive this automatically, add a oneshot unit ordered before the generated mount unit and pull it in with an fstab option:
```
# /etc/fstab
... ntfs3 ...,nofail,x-systemd.requires=ntfs-clear-dirty.service 0 0
```
```ini
# /etc/systemd/system/ntfs-clear-dirty.service
[Unit]
Description=Clear NTFS dirty flag before automount
ConditionPathExists=/dev/disk/by-uuid/<UUID>
After=dev-disk-by\x2duuid-<UUID>.device
Before=<escaped-mountpoint>.mount
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/ntfsfix -d /dev/disk/by-uuid/<UUID>
Nice=19
IOSchedulingClass=idle
[Install]
WantedBy=local-fs.target
```
`x-systemd.requires=` makes systemd-fstab-generator emit `Requires=`/`After=` on the mount unit. `ConditionPathExists` makes it a no-op when the drive is absent. Verify the generated unit with `systemctl cat <mountpoint>.mount` and check for ordering cycles with `systemd-analyze verify`.

### Other gotchas
- `findmnt --verify` prints a cosmetic `[W] ntfs3 does not match with on-disk ntfs` warning; it compares the fstype against blkid's `ntfs` and can be ignored.
- Boot-time pulls only exist for units the generator symlinks into a target: check `/run/systemd/generator/{local-fs,remote-fs}.target.wants/`. `_netdev` + `x-systemd.automount` puts a CIFS automount under `remote-fs.target.wants`, so it still starts at boot without blocking it.
- Reuse an existing mountpoint path even if it looks wrong: symlinks and hard-coded paths *inside* the filesystem (and other people's services) pin the mountpoint. Find one with `readlink` on symlinks found while inspecting the volume read-only.

## Why not `exfat-fuse` as fstype?
`mount` resolves fstype by looking for `/sbin/mount.<fstype>`. So `exfat-fuse` would look for `/sbin/mount.exfat-fuse`. While that binary exists, systemd's fstab parser may not handle non-standard fstypes correctly. Using `exfat` (the standard type) with the mount.exfat symlink is safer and more portable.
