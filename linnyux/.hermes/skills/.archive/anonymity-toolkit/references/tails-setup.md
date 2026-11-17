# Tails OS Crypto Wallet Setup (June 2026)

## Finding the Tails USB
```
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,LABEL,FSTYPE
# Look for:
#   sda1 -> TAILS (FAT32, ~8GB — system partition)
#   sda2 -> TailsData (LUKS — persistent storage)
```

## Mounting TailsData Persistent Storage
```bash
echo -n 'passphrase' > /tmp/tails_key
sudo cryptsetup luksOpen /dev/sda2 tails_data --key-file=/tmp/tails_key
sudo mkdir -p /mnt/tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data
sudo ls -la /mnt/tails_data/Persistent/

# Copy files:
sudo cp feather-wallet.AppImage /mnt/tails_data/Persistent/
sudo chown amnesia:amnesia /mnt/tails_data/Persistent/feather-wallet.AppImage
sudo chmod +x /mnt/tails_data/Persistent/feather-wallet.AppImage

# Clean up:
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
sudo shred -u /tmp/tails_key
sudo rm -rf /mnt/tails_data
```

## Feather on Tails
```bash
cd ~/Persistent && ./feather-wallet.AppImage --use-local-tor
```

## Ownership
Files from another machine have wrong UID. Always `chown amnesia:amnesia` after copying into TailsData.
