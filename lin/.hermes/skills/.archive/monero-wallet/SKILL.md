---
name: monero-wallet
description: Install and configure Monero wallets (Feather Wallet, monero-wallet-cli). Covers AppImage setup, wallet generation from seed, non-interactive CLI operations with expect, and Feather wallet GUI setup.
version: 1.0.0
author: Hermes Agent + user
platforms: [linux]
---

# Monero Wallet Setup

Install and configure Monero wallets — Feather Wallet (GUI, Tor-native) and monero-wallet-cli (official CLI). Covers wallet creation, seed generation, and restoration.

## When to Use

- User asks to "install a crypto wallet", "set up Monero wallet", "install Feather wallet"
- User wants a decentralized wallet for Tails
- User needs to create/restore a Monero wallet non-interactively
- User asks about Monero seed phrases, wallet files

## Install Feather Wallet

Feather is a lightweight, Tor-native Monero wallet. Download the AppImage:

```bash
# Get latest version
curl -sL https://api.github.com/repos/feather-wallet/feather/releases/latest | python3 -c "
import sys,json; d=json.load(sys.stdin)
for a in d.get('assets',[]):
    n=a['name']
    if 'AppImage' in n and 'arm' not in n:
        print(a['browser_download_url'])
" | xargs -r wget -O ~/Downloads/feather-wallet.AppImage

chmod +x ~/Downloads/feather-wallet.AppImage
```

### Run for first time

```bash
~/Downloads/feather-wallet.AppImage --help  # Verify
~/Downloads/feather-wallet.AppImage --use-local-tor  # Use system Tor
```

On Tails: `./feather-wallet.AppImage --use-local-tor` (auto-detects Tor at 127.0.0.1:9050)

## Generate Wallet via Monero CLI

For non-interactive wallet generation (e.g., from a script), download the official Monero CLI tools and use `expect`:

```bash
# Download
curl -L "https://downloads.getmonero.org/cli/linux64" -o /tmp/monero-cli.tar.bz2
cd /tmp && tar -xjf monero-cli.tar.bz2
```

### Prefer `--password-file` over Expect

The `--password-file` flag is more reliable than piping or Expect, especially when the CLI is slow to start Tor. Create the file first:
```bash
echo -n 'mywalletpass' > /tmp/monero_pw.txt
```

### Offline Wallet Creation (Recommended)

No daemon connection needed for wallet creation — omit `--daemon-address` entirely:

```bash
expect << 'EXPECTEOF'
set timeout 30
spawn monero-wallet-cli \
    --generate-new-wallet=/tmp/wallet \
    --password-file=/tmp/monero_pw.txt \
    --log-level=0

expect "language of your choice:" { send "1\r" }
expect eof
EXPECTEOF
```

Output files:
- `/tmp/wallet` — wallet data (~410KB)
- `/tmp/wallet.keys` — encrypted keys (~1.7KB)  
- `/tmp/wallet.address` — public Monero address (single line)

The seed phrase is printed to stdout after generation. Extract with:
```bash
grep -A2 "can be used to recover" wallet_creation.log
```

### Non-Interactive Wallet Restoration from Seed

```expect
set timeout 30
spawn monero-wallet-cli \
    --restore-deterministic-wallet \
    --generate-new-wallet=/tmp/restored-wallet \
    --password-file=/tmp/password.txt \
    --log-level=0

expect "language of your choice:" { send "1\r" }
expect "seed" { sleep 0.5; send "your 25 word seed phrase here\r" }
expect "password" { sleep 0.5; send "walletpass\r" }
expect eof
```

## Seed Phrase

Monero uses a 25-word seed with a 1626-word English wordlist. Generate with:

```bash
# Via monero-wallet-cli (recommended — official wordlist verified by binary)
monero-wallet-cli --generate-new-wallet=/tmp/wallet --password-file=/tmp/pw.txt
```

The seed is printed at wallet creation. Extract from output with: `grep -A2 "can be used to recover"`.

## Tails Integration

Copy Feather AppImage to Tails persistent storage:

```bash
# Mount Tails LUKS
sudo cryptsetup luksOpen /dev/sdX2 tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data

# Copy wallet
cp ~/Downloads/feather-wallet.AppImage /mnt/tails_data/Persistent/

# Clean up
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
```

## Pitfalls

- **GUI automation is unreliable**: Feather uses Qt which doesn't respond to xdotool reliably under KDE. For wallet creation, use the Monero CLI and then open the wallet file in Feather
- **Wordlist mismatch**: The GitHub source code wordlist may differ from the release binary's wordlist. Always verify seed phrases against the official Monero CLI binary
- **`--password-file` for CLI**: Use this flag to skip interactive password prompts. Create the file with `echo -n 'password' > /tmp/pw.txt`
- **Seed checksum**: Monero validates the seed. A random Python-generated seed may fail "Electrum-style word list failed verification". Always use the official CLI to generate seeds
- **Expect pattern matching**: Use `expect "language of your choice:"` (exact string) not regex. The CLI takes time to start Tor, so set a generous timeout
- **Wallet files location**: Feather stores in `~/.feather/wallets/`. Haveno stores in `~/.local/share/Haveno/xmr_mainnet/wallet/`
