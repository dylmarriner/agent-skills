# Worked Example: NFS over Tailscale — Rabuntu → Kubuntux

## Topology

| Machine  | Tailscale IP   | Role     |
|----------|----------------|----------|
| Kubuntux | 100.93.75.87   | Client   |
| Rabuntu  | 100.68.0.96    | Server   |

## Source Drive (Rabuntu side)

```
lsblk output:
sdb      1.8T
├─sdb1 495.8G exfat  → /media/devmon/exfat-dev  (label: exfat-dev)
└─sdb2   1.3T ext4   → /srv/nas/main             (label: backup-dev-ext4)
```

sdb2 was in `/etc/fstab` on rabuntu but was **not mounted** at the time of setup:

```
/dev/sdb2 /srv/nas/main ext4 defaults,noatime,nofail,x-systemd.device-timeout=10 0 2
```

Manually mounted: `sudo mount /dev/sdb2 /srv/nas/main`

This drive is also listed in a second fstab entry as `/mnt/storage_big` (same device, different mount point).

## Server-side NFS Export

Added to `/etc/exports`:

```
/srv/nas/main 100.93.75.87(rw,sync,no_subtree_check,no_root_squash)
```

Applied with: `sudo exportfs -ra`

Options chosen:
- `rw` — read-write
- `sync` — safe writes
- `no_subtree_check` — disable subtree checking on an already-large export
- `no_root_squash` — trusted Tailscale network, client needs root access preserved

## Client-side Mount (Kubuntux)

1. Installed `nfs-common`
2. Created mount point: `/media/kubuntux/DEVELOPMENT1/rabuntu-1.3tb/`
3. Test mount: `sudo mount -t nfs 100.68.0.96:/srv/nas/main /media/kubuntux/DEVELOPMENT1/rabuntu-1.3tb`
4. Verified: 1.4T, 327G used, 951G free — read/write OK

## fstab Entry (Kubuntux)

```
100.68.0.96:/srv/nas/main /media/kubuntux/DEVELOPMENT1/rabuntu-1.3tb nfs defaults,nofail,x-systemd.automount,noatime,vers=4.2 0 0
```

- `nofail` — boot doesn't block on unreachable server
- `x-systemd.automount` — lazy mount-on-access
- `vers=4.2` — NFSv4.2, only needs port 2049

## Notes

- Both machines use UID 1000 for their primary user. NFS passes raw UIDs, so files written from either side show as owned by the local user without any mapping.
- The existing Samba/CIFS mounts in kubuntux's fstab (pointing to Macuntu IP 100.75.23.127) mount the same rabuntu drives via a different protocol. The NFS mount is a direct connection to rabuntu's Tailscale IP — faster and simpler.
