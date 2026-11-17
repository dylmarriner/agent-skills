# Tails Persistent Storage Operations

Tails uses LUKS-encrypted persistent storage on a separate partition from the system.

## Identifying the Drive

```bash
lsblk -o NAME,SIZE,TYPE,LABEL,FSTYPE
```

Look for:
- Partition labelled "TAILS" (vfat, ~8GB) — the Tails system
- Partition labelled "TailsData" (crypto_LUKS, remaining space) — persistent storage

## Opening and Mounting

```bash
# Write password to temp file (necessary for piping to cryptsetup)
printf 'your_passphrase_here' > /tmp/tails_key

# Open LUKS
sudo cryptsetup luksOpen /dev/sdX2 tails_data --key-file=/tmp/tails_key

# Wipe key file from disk
sudo shred -u /tmp/tails_key

# Mount
sudo mkdir -p /mnt/tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data
```

## File Operations

Files go to `/mnt/tails_data/Persistent/`. This directory maps to `~/Persistent/` within the Tails session.

```bash
# Copy files
sudo cp /path/to/file /mnt/tails_data/Persistent/

# Fix ownership
sudo chown lin:lin /mnt/tails_data/Persistent/filename

# Verify
sudo ls -la /mnt/tails_data/Persistent/
```

## Closing

```bash
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
sudo rm -rf /mnt/tails_data
```

## Pitfalls

- **Passphrase piping**: `cryptsetup luksOpen` doesn't read from stdin by default. Use `--key-file=/dev/stdin` or `--key-file=/tmp/keyfile` with a temp file, then shred the file
- **The mount point must exist**: Create with `sudo mkdir -p` if it was deleted
- **Don't write passwords to shell history**: Use `printf` with a temp file, not inline `echo`
- **Ownership matters**: Files owned by `root` won't be writable from Tails (user is `amnesia`). Set owner to the regular user (`lin` on your host)
