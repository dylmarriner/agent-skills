# Fleet Network Tuning — Session Notes

Deployed to 4 machines on 2026-07-08:

| Machine | Role | Notes |
|---------|------|-------|
| lin (100.91.55.113) | Dev laptop, CIFS client | CIFS mount of kubuntux's DEVELOPMENT1 |
| kubuntux (100.93.75.87) | Samba server + CIFS server | Exports `/media/kubuntux/DEVELOPMENT1` via Samba as `//100.93.75.87/DEVELOPMENT1` |
| macuntu (100.75.23.127) | Dev machine, CIFS client | Same CIFS mount as lin |
| rabuntu (100.68.0.96) | RPi5, standalone | No CIFS mount, already had 128MB buffers |

## What was changed

### All 4 machines

Created `/etc/sysctl.d/90-network-performance.conf` with:
- rmem_max/wmem_max: 212KB → 16MB
- tcp_fastopen=3
- tcp_slow_start_after_idle=0
- netdev_max_backlog: 16384 → 50000
- tcp_mtu_probing=1
- tcp_tw_reuse=1

### Samba server (kubuntux only)

Added to `/etc/samba/smb.conf [global]`:
- `aio read size = 16384`
- `aio write size = 16384`
- `read raw = yes`
- `write raw = yes`
- `server signing = disabled`
- `strict rename = yes`

Removed `write cache size = 262144` — unsupported on current Samba version.

### CIFS clients (lin, macuntu)

Remounted with `actimeo=60` (was 1). Added to `/etc/fstab` for persistence.

The original mount was handled by an automounter (gvfs/systemd) with no fstab entry — `actimeo=1` was the default. Installed `cifs-utils` on both machines to get the `mount.cifs` helper.

## Command reference

```bash
# Check current mount options
findmnt -n -o OPTIONS /mnt/development1

# Remount with better options
sudo mount -t cifs -o actimeo=60,vers=3.0,sec=none,uid=1000,gid=1000,\
forceuid,forcegid,file_mode=0775,dir_mode=0775,soft,nounix,\
rsize=4194304,wsize=4194304 \
//100.93.75.87/DEVELOPMENT1 /mnt/development1

# Lazy unmount if busy
sudo umount -l /mnt/development1

# Verify all sysctl values
sysctl net.core.rmem_max net.core.wmem_max net.ipv4.tcp_fastopen \
net.ipv4.tcp_congestion_control net.core.netdev_max_backlog

# Test throughput improvement
time dd if=/dev/zero bs=1M count=100 | ssh kubuntux "cat > /dev/null"
```

## Verified

All 4 machines confirmed live with `sysctl -p` no errors. The Samba `testparm` confirmed config is valid (ignored old `write cache size` param).
