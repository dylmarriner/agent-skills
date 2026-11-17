# exFAT Partition Hang Recovery

## Symptom

- `ls /mnt/dev/` or `ls /mnt/shared/external-dev/` hangs indefinitely
- `sudo umount /mnt/dev` hangs — even `sudo umount -l`
- SSH to the Pi eventually times out
- Ping also fails
- All mounts under `/mnt/shared/` become inaccessible (including healthy ext4 partitions) because the directory traversal stalls on the broken exfat entry

## Root cause

Linux exfat driver can enter an unrecoverable I/O wait state if the partition has latent filesystem corruption, a bad sector, or a hot-unplug event. The kernel thread enters D-state (uninterruptible sleep) and cannot be killed. No SSH login or network service will respond because the I/O path is locked.

## Recovery

**The only recovery is a hard power cycle.**

1. Unplug the Pi's power cable (or press the physical reset button if available)
2. Plug back in and wait for boot
3. SSH in and run fsck on the exfat partition before remounting:

```bash
# Unmount if it auto-mounted during boot
sudo umount /dev/sdb1 2>/dev/null

# Check and repair
sudo fsck.exfat /dev/sdb1
```

4. Remount manually and verify:

```bash
sudo mount /dev/sdb1 /mnt/dev
ls /mnt/dev/
```

## Prevention

- Add `nofail,x-systemd.device-timeout=30` to the exfat fstab entry so a future hang at boot is recoverable (systemd will time out instead of blocking the entire boot sequence).
- Consider migrating important data off exfat onto ext4, which has more robust error handling.
