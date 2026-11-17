# Storage Topology — Video Downloads

## Primary target — LOCAL SMB share (`[videos]`)

- **Path:** `/mnt/storage/videos/` (SMB share `[videos]` in `/etc/samba/smb.conf`)
- **Backend:** `/dev/sda1`, ext4, ~916G total, ~780G free
- **Permissions:** kubuntux:kubuntux (uid=1000)
- **Existing content:** Large video collection already present — `.mp4`, `.mkv` files
- **This is the SHARE served to other machines** on the LAN via Samba
- **This is where all video downloads go** — default output dir of `concurrent_downloader.py`

## Secondary target (Pi SMB share — offline-optional)

- **Mount point:** `/mnt/pivideos`
- **Backend:** `//100.68.0.96/shared` (CIFS/SMB, Pi)
- **Credentials:** `/home/kubuntux/.smbcredentials-pi` (user=rabuntu, password=admin, WORKGROUP)
- **Mount type:** systemd mount unit (`mnt-pivideos.mount`), auto-generated from /etc/fstab
- **Status indicator:** Check with `systemctl is-active mnt-pivideos.mount`
- **Known failure mode:** Error 115 (Operation now in progress) — Pi host (100.68.0.96) unreachable/offline. The automount retries continuously but fails until the Pi is back online.
- **Usage:** Rsync from local share to Pi when Pi comes back: `rsync -avP /mnt/storage/videos/ /mnt/pivideos/videos/`

## Secondary fallback (unused)

- **Path:** `/mnt/massive_storage/videos/`
- **Status:** Directory exists on disk but currently unused for video storage. Not mounted to any device.

## Multi-machine video storage

See `references/multi-machine-download.md` for other machines (macuntu, root server) and their SMB targets.

## Fallback decision tree

1. **Primary always works:** `/mnt/storage/videos/` is a local ext4 drive (always available) — this is the `[videos]` SMB share
2. **Pi check:** `ls /mnt/pivideos/` — if it returns contents, Pi is online and can be rsynced to later. If error 115, Pi is offline — skip.
3. **Rsync when Pi comes back:** `rsync -avP /mnt/storage/videos/ /mnt/pivideos/videos/`
