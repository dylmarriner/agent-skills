---
name: mtp-android-backup
description: Back up an Android phone via MTP (USB) from Linux. Covers jmtpfs mounting, file copy, phone screen unlock requirement, and common FUSE cleanup issues.
version: 1.0.0
---

# MTP Android Backup

Back up files from an Android phone to a Linux machine over USB MTP. Covers the common pitfalls: locked screen blocks MTP access, stale FUSE mounts, and which MTP tools actually work.

## Trigger Conditions

- User says "backup my phone" or "copy files off my phone"
- Android phone connected via USB (Samsung, Pixel, OnePlus, etc.)
- Phone shows in `lsusb` with vendor ID like `04e8:` (Samsung), `18d1:` (Google/Pixel), etc.
- Goal: copy photos, videos, documents, downloads, music from internal storage

## Prerequisites

Install MTP tools:

```bash
sudo apt install -y mtp-tools jmtpfs
```

Check the phone is detected:

```bash
lsusb | grep -iE 'samsung|android|google|oneplus|xiaomi'
```

Verify MTP mode. On Samsung, the USB device ID tells you the mode:
- `04e8:6860` — MTP mode (file transfer)
- `04e8:6862` — RNDIS + DM + ACM (dev mode, NOT MTP)

## Workflow

### Step 1: Unlock the phone screen

**This is mandatory.** Samsung One UI, Google Pixel, and most Android phones block MTP storage access when the screen is locked. Unlock with PIN/password/pattern first. The phone also needs to have "File Transfer" selected in the USB notification (not "Charging only" or "Photo Transfer").

### Step 2: Mount via jmtpfs

```bash
mkdir -p /tmp/phone-backup
jmtpfs /tmp/phone-backup
```

jmtpfs runs in the foreground (FUSE). If using `background=true` in a terminal session, the FUSE mount stays resident and subsequent `ls` commands work.

If mount fails with "Permission denied" on the mount point, check for a stale mount from a previous attempt:

```bash
# Check for stale FUSE mounts
mount | grep jmtpfs
# Force unmount
fusermount -u /tmp/phone-backup
# Remove and recreate
rmdir /tmp/phone-backup && mkdir -p /tmp/phone-backup
```

### Step 3: Browse and estimate

```bash
ls /tmp/phone-backup/
# List top-level directories — expect "Internal storage" or similar
ls /tmp/phone-backup/Internal\ storage/
```

Typical backup targets:
- DCIM/ — photos and videos
- Pictures/ — screenshots, saved images
- Documents/ — PDFs, docs
- Download/ — downloaded files
- Recordings/ — voice recordings
- Music/ — music files
- Movies/ — video files

### Step 4: Copy files

```bash
mkdir -p ~/phone-backup
cp -r /tmp/phone-backup/Internal\ storage/DCIM/ ~/phone-backup/
cp -r /tmp/phone-backup/Internal\ storage/Pictures/ ~/phone-backup/
cp -r /tmp/phone-backup/Internal\ storage/Documents/ ~/phone-backup/
cp -r /tmp/phone-backup/Internal\ storage/Download/ ~/phone-backup/
```

`du -sh ~/phone-backup/` to verify size.

### Step 5: Unmount

```bash
fusermount -u /tmp/phone-backup
rmdir /tmp/phone-backup
```

If `fusermount` says "target is busy", kill the jmtpfs process first:

```bash
pkill jmtpfs
# or
kill $(pgrep jmtpfs)
```

## Pitfalls

1. **Phone screen must be unlocked** — MTP is blocked at the kernel level on Android when the device is locked. `mtp-files` will show "Get Storage information failed" or jmtpfs will mount an empty/IO-error directory.

2. **Stale FUSE mounts from prior attempts block new ones** — If `jmtpfs` fails with "Transport endpoint is not connected" or "Input/output error" on the mount point, the previous session left a broken FUSE mount. Unmount with `fusermount -u` first.

3. **MTP over FUSE is slow for many small files** — Each file open goes through USB framing. For large photo libraries (5000+ files), MTP copies are slower than adb pull (when ADB is available).

4. **`du -sh` returns zero for mounted directories** — FUSE MTP doesn't expose accurate file sizes to `du`. The files are real — `ls -la` individual files shows correct sizes.

5. **Some phones need the "File Transfer" USB mode selected** — After plugging in, pull down the notification shade and tap the USB notification. Select "File Transfer" or "MTP". Default is often "Charging only".

6. **go-mtpfs vs jmtpfs** — jmtpfs is more reliable on modern Ubuntu/Kubuntu. go-mtpfs may fail with Permission denied for the non-root FUSE mount. Use jmtpfs.

