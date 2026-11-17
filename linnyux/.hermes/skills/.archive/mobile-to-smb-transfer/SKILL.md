---
name: mobile-to-smb-transfer
description: Transfer files (videos, photos, media) from Android phones to SMB/CIFS network shares. Covers USB MTP, ADB, and direct SMB-from-phone methods. Includes Samba auth troubleshooting.
trigger: user wants to copy files from phone to a network share, mount phone storage, or fix SMB login failures
---

# Mobile to SMB File Transfer

Transferring media from Android phones to Samba/CIFS shares on the local network.

## Phone Connection Methods

### 1. Direct SMB from phone (easiest — no computer needed)

Install an SMB-capable file manager on the phone and connect straight to the share over WiFi/Tailscale:

| App | Notes |
|-----|-------|
| **X-plore** | Best SMB support, free, handles credentials well |
| **Solid Explorer** | Polished, SMBv2/3 support |
| **CX File Explorer** | Clean UI, good SMB |
| **MiXplorer** | Free, lightweight, powerful |

Connection details to enter in the app:
```
Protocol: SMB / SMBv2 / SMBv3
Server:   <tailscale-ip> or <hostname>  (e.g. 100.93.75.87 or kubuntux)
Share:    <share-name>                  (e.g. videos)
User:     <samba-user>                  (e.g. kubuntux)
Pass:     <samba-pass>
```

### 2. USB MTP mount (phone → Linux → SMB)

Connect phone via USB, select "File Transfer / MTP" on the phone notification.

```bash
# Install MTP tools
sudo apt install jmtpfs go-mtpfs

# Mount phone storage
mkdir -p /tmp/phone
jmtpfs /tmp/phone

# Browse files
ls /tmp/phone/Phone/DCIM/Camera/

# Mount SMB target
sudo mkdir -p /mnt/smb_videos
sudo mount -t cifs //100.93.75.87/videos /mnt/smb_videos \
  -o username=kubuntux,password=kubuntux,vers=3.0,uid=$(id -u)

# Copy files
cp /tmp/phone/Phone/DCIM/Camera/*.mp4 /mnt/smb_videos/

# Cleanup
fusermount -u /tmp/phone
sudo umount /mnt/smb_videos
```

### 3. ADB over WiFi (if Developer Options + USB debugging accessible)

```bash
# Connect phone via USB first, enable TCP mode
adb tcpip 5555
# Disconnect USB, find phone IP
adb connect <phone-ip>:5555
# Pull files
adb pull /sdcard/DCIM/Camera/ /tmp/phone_vids/
# Pipe into SMB
```

### 4. ADB over USB (developer phones only)

```bash
adb devices                          # verify connection
adb shell ls /sdcard/DCIM/Camera/   # find videos
adb pull /sdcard/DCIM/Camera/ /tmp/phone_vids/
```

## SMB Auth Troubleshooting

### Symptoms & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `NT_STATUS_LOGON_FAILURE` | Wrong samba password or user doesn't exist in samba DB | Reset with `smbpasswd -a <user>` on the SMB server |
| `NT_STATUS_ACCESS_DENIED` | Share has `guest ok = no` and no credentials provided | Use `-U user%pass` or mount with `username=...,password=...` |
| `NT_STATUS_NOT_FOUND` | Hostname resolution failed | Use Tailscale IP instead of hostname, or check `/etc/hosts` |
| `NT_STATUS_CONNECTION_REFUSED` | Samba service not running | `systemctl start smbd && systemctl enable smbd` |
| Timeout / slow | SMB version mismatch | Add `vers=3.0` to mount options |

### Samba password reset (SSH to SMB server)

```bash
# Check existing samba users
sudo pdbedit -L

# Reset password for user
sudo smbpasswd <username>
# or re-create
sudo pdbedit -a -u <username> -t
sudo smbpasswd -a <username>
```

### Mount SMB share permanently

Add to `/etc/fstab`:
```
//100.93.75.87/sharename /mnt/mountpoint cifs username=user,password=pass,vers=3.0,uid=1000,gid=1000,noatime,soft,_netdev 0 0
```

### Test SMB access from CLI

```bash
# List files (interactive password prompt)
smbclient //server/share -U user

# Single command
smbclient //server/share -U user%pass -c "ls"

# Copy a file to the share
smbclient //server/share -U user%pass -c "put /path/to/local/file.mp4"

# Copy from share
smbclient //server/share -U user%pass -c "get file.mp4"
```

## After Transfer — Verify

- Check file size matches original
- Can SSH into kubuntux and run `ls -lh /mnt/storage/videos/`
- Or `smbclient //kubuntux/videos -U kubuntux -c "ls"`

## Samba Server Admin

For server-side SMB share fixes (missing share paths, NT_STATUS errors, config reload), see `references/samba-server-admin.md`.

## Pitfalls

- **Locked phones (MDM/FRP)**: If Developer Options and USB debugging are disabled on the phone, MTP and ADB methods won't work. Use method 1 (SMB file manager app) as the fallback.
- **Tailscale required for hostname resolution**: `kubuntux` only resolves on machines on the same Tailscale network. Use raw IP (`100.93.75.87`) as fallback.
- **Samba passwd != system passwd**: Changing the Linux login password does NOT update the Samba password. Always use `smbpasswd` (not `passwd`) for SMB auth changes.
- **MTP mounts are read-write but flaky**: Large file transfers (>1GB) over MTP can hang. Use SMB-from-phone for big files.
- **SMB version negotiation**: Old phones may only support SMBv1. Set `client min protocol = NT1` on the server or `vers=1.0` in mount options if the phone app doesn't work.
