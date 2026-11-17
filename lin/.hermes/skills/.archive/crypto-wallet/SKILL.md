---
name: crypto-wallet
description: "Monero and privacy cryptocurrency wallet setup: Feather wallet, Monero CLI wallet generation, Tails OS persistent storage integration, Tor routing."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Crypto Wallet Setup

Install Feather wallet, generate Monero wallets via the official CLI, and integrate with Tor + Tails persistent storage.

## When to Use This Skill

- User wants to install/setup a crypto wallet (Feather, Monero CLI)
- User wants to generate a Monero wallet seed/keys
- User wants to configure crypto wallet for Tor/anonymity
- User wants to save wallet files to Tails persistent storage
- User mentions Haveno, Cake Wallet, Bisq2, Feather, or Monero

## Dependencies

```
# Ubuntu
sudo apt install -y proxychains4 torsocks expect
# Feather wallet: download AppImage from GitHub releases
# Monero CLI: download from https://downloads.getmonero.org/cli/linux64
```

## Installing Feather Wallet

Download the latest AppImage from GitHub releases:
```bash
wget https://github.com/feather-wallet/feather/releases/latest/download/feather-<version>.AppImage
chmod +x feather-<version>.AppImage
```

Launch with system Tor: `./feather-wallet.AppImage --use-local-tor`

Feather auto-detects Tor at 127.0.0.1:9050 on Tails and Ubuntu systems.

## Generating a Monero Wallet (Official CLI)

The Monero CLI binary's embedded wordlist may differ from GitHub source. Always use the release binary for wallet generation.

```bash
# Download Monero CLI
curl -sL "https://downloads.getmonero.org/cli/linux64" -o /tmp/monero-cli.tar.bz2
cd /tmp && tar -xjf monero-cli.tar.bz2

# Create wallet password file
echo -n 'yourpassword' > /tmp/monero_pw.txt

# Generate wallet with expect (handles interactive prompts)
expect << 'EXPECTEOF'
set timeout 30
spawn /tmp/monero-x86_64-linux-gnu-*/monero-wallet-cli \
    --generate-new-wallet=/tmp/my-wallet \
    --password-file=/tmp/monero_pw.txt \
    --log-level=0
expect "language of your choice:" { send "1\r" }
expect eof
EXPECTEOF
```

The expect script handles the language selection prompt. The seed phrase is printed to stdout. The wallet files are created at the specified path with `.keys` suffix.

## Wallet File Locations

- Feather stores wallets at: `~/.feather/wallets/`
- Monero CLI creates: `<wallet-name>`, `<wallet-name>.keys`, `<wallet-name>.address`
- Tails persistent: `/home/amnesia/Persistent/`

## Saving to Tails USB

```bash
# Mount Tails persistent storage
printf 'passphrase' | sudo cryptsetup luksOpen /dev/sdX2 tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data
# Copy files to /mnt/tails_data/Persistent/
sudo cp feather-wallet.AppImage /mnt/tails_data/Persistent/
# Unmount and lock
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
```

## Troubleshooting

- **"Electrum-style word list failed verification"**: The seed phrase was generated with a wordlist that doesn't match the Monero CLI binary. Regenerate using the binary's own wallet creation (not a custom Python script).
- **Feather GUI doesn't respond to xdotool clicks**: KDE Plasma compositor may block xdotool. Launch Feather and let the user click manually through the welcome screens.
- **Wallet file format**: Monero CLI generates standard `.keys` files readable by Feather. No format conversion needed.

## References

- `references/monero-wallet-generation.md` — Detailed expect scripts and wallet file handling
- Feather GitHub: https://github.com/feather-wallet/feather
- Monero CLI: https://downloads.getmonero.org/cli/linux64
