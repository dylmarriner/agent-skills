---
name: crypto-wallet-setup
description: "Install and configure decentralized cryptocurrency wallets (Feather, Monero CLI) with Tor. Generate Monero wallet seeds and integrate with Tails persistent storage."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [crypto, wallet, monero, feather, tails, decentralized]
    related_skills: [haveno-setup, anonymity-setup, godmode]
---

# Crypto Wallet Setup

Install and configure decentralized cryptocurrency wallets — primarily Feather (Monero) with Tor integration. Generate wallet seed phrases using the official Monero wordlist. Deploy to Tails OS persistent storage.

## When to Use This Skill

Trigger when the user:
- Asks for a "crypto wallet", "Monero wallet", "decentralised wallet"
- Wants a wallet that works on Tails OS
- Wants to "generate a wallet seed" or "create a Monero wallet"
- Mentions Feather, Monero, XMR
- Wants to set up anonymity-focused crypto tools (pairs with Haveno)

## Feather Wallet (Monero)

**Best decentralized wallet for Tails:** Native Tor support, no blockchain download, lightweight, fully open source.

### Install

```bash
# Find latest version
curl -sL https://api.github.com/repos/feather-wallet/feather/releases/latest | grep tag_name

# Download (adjust version)
cd ~/Downloads
wget https://github.com/feather-wallet/feather/releases/download/2.8.1/feather-2.8.1.AppImage
chmod +x feather-2.8.1.AppImage

# Run with system Tor
./feather-wallet.AppImage --use-local-tor
```

### Key Options

| Flag | Purpose |
|------|---------|
| `--use-local-tor` | Use system Tor (127.0.0.1:9050) instead of bundled Tor |
| `--stagenet` | Connect to Monero stagenet (testing) |
| `--testnet` | Connect to Monero testnet |

### Wallet Creation Workflow

1. Launch Feather → "Create new wallet"
2. Set wallet name and password
3. **WRITE DOWN the 25-word seed phrase on paper** — this is the ONLY backup
4. Feather connects to remote Monero nodes via Tor automatically
5. Wallet file is stored at `~/.feather/wallets/<name>.keys`

### Tails OS Integration

On Tails, the Feather AppImage and wallet files should live in the Persistent folder:

```
/home/amnesia/Persistent/
  feather-wallet.AppImage
```

Run: `./feather-wallet.AppImage --use-local-tor`

Tails routes all traffic through Tor system-wide, so Feather's Tor integration works automatically.

## Monero Seed Phrase Generation

### ⚠ CRITICAL: Wordlist Mismatch Between Source and Binary

The GitHub source code wordlist (`english.h` from the Monero repo) may differ from the wordlist embedded in the official Monero CLI release binary. If you generate a seed using the GitHub wordlist and then try to restore it with `monero-wallet-cli`, you will get **"Electrum-style word list failed verification"** for words that exist in the GH list but not the binary's embedded list (e.g. "either", "tail", "locker" were in the source but not in v0.18.5.0's binary).

**USE THE MONERO CLI BINARY FOR WALLET GENERATION**, not a Python script with a source-extracted wordlist, unless you verify every word against the actual binary.

### Offline Wallet Creation with monero-wallet-cli + expect

This is the ONLY reliable method for generating a wallet that Feather and other Monero wallets can restore:

```bash
# 1. Download the official CLI tools
curl -sL "https://downloads.getmonero.org/cli/linux64" -o /tmp/monero-cli.tar.bz2
cd /tmp && tar -xjf monero-cli.tar.bz2

# 2. Create a password file
echo -n 'your-wallet-passphrase' > /tmp/monero_pw.txt

# 3. Generate wallet (offline — no daemon needed)
expect << 'EXPECTEOF'
set timeout 30
spawn /tmp/monero-x86_64-linux-gnu-v*/monero-wallet-cli \
    --generate-new-wallet=/tmp/my-wallet \
    --password-file=/tmp/monero_pw.txt \
    --log-level=0

expect "language of your choice:" { send "1\r" }
expect -re "(seed|mnemonic|words)" {
    exp_settle_time 2
    puts "---SEED PHRASE GENERATED---"
}
expect eof
EXPECTEOF

# 4. Copy wallet files to Feather's expected location
mkdir -p ~/.feather/wallets
cp /tmp/my-wallet* ~/.feather/wallets/
```

### Restore from Seed with monero-wallet-cli

```bash
expect << 'EXPECTEOF'
set timeout 30
spawn /tmp/monero-x86_64-linux-gnu-v*/monero-wallet-cli \
    --restore-deterministic-wallet \
    --generate-new-wallet=/tmp/restored-wallet \
    --password-file=/tmp/monero_pw.txt \
    --log-level=0

expect "language of your choice:" { send "1\r" }
expect "seed" { sleep 0.5; send "YOUR 25 WORD SEED PHRASE HERE\r" }
expect eof
EXPECTEOF
```

### Alternative: Python Script (for quick prototyping — verify against binary)

```python
import re, subprocess, secrets, hashlib

entropy = secrets.randbits(256)
words = []
remaining = entropy
word_count = len(wordlist)

for i in range(24):
    idx = remaining % word_count
    words.append(wordlist[idx])
    remaining //= word_count

# Checksum word (simple hash-based)
entropy_bytes = entropy.to_bytes(32, 'big')
h = hashlib.sha256(entropy_bytes).digest()
checksum_idx = h[0] % word_count
words.append(wordlist[checksum_idx])

seed_phrase = ' '.join(words)
```

### Security

- Generate with `secrets.randbits()` (CSPRNG), NOT `random`
- Write seed on PAPER only — never store digitally
- Verify each word against the official wordlist
- The checksum word is derived from SHA-256 of the entropy bytes modulo 1626
- A 25-word Monero seed provides 256 bits of entropy + 4 bits of checksum

## Tails Persistent Storage USB

### Partition Layout

| Partition | Label | Filesystem | Size | Content |
|-----------|-------|------------|------|---------|
| sda1 | TAILS | FAT32 | ~8GB | Tails OS system |
| sda2 | TailsData | LUKS (crypto_LUKS) | ~49GB | Persistent storage |

### Mounting from Linux

```bash
# Open LUKS container
echo -n "$PASSPHRASE" > /tmp/key
sudo cryptsetup luksOpen /dev/sda2 tails_data --key-file=/tmp/key
sudo shred -u /tmp/key

# Mount
sudo mkdir -p /mnt/tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data

# Copy files (preserve ownership to lin user)
sudo cp /path/to/file /mnt/tails_data/Persistent/
sudo chown lin:lin /mnt/tails_data/Persistent/file

# Clean up
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
```

### Persistent Storage Features

- Enabled during Tails first boot setup
- Stores wallet files, configs, keys between reboots
- LUKS-encrypted (passphrase required)
- Contains: Persistent/ (main user folder), dotfiles/ (configs), gnupg/, etc.
- All files disappear if passphrase is lost

### Script: generate-monero-seed.py

A standalone Python script that generates a Monero seed using the GitHub-sourced wordlist. See `references/monero-wordlist-mismatch.md` for important caveats about wordlist discrepancies between GitHub source and release binaries.

```bash
python3 ~/.hermes/skills/crypto-wallet-setup/scripts/generate-monero-seed.py
```

No dependencies beyond Python stdlib + curl. Verifies all 25 words against the official wordlist automatically.

## Haveno Decentralized Exchange

Haveno is a P2P exchange using Monero + Tor. Must be built from source on Ubuntu.

### Build

```bash
# Prerequisites: Java JDK 21+ with JavaFX (Liberica)
sdk install java 21.0.2.fx-librca   # via SDKMan

# Build
git clone https://github.com/haveno-dex/haveno.git ~/Documents/haveno
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh
make skip-tests   # 81 tasks, ~4 min build
```

### Launch (JavaFX Module Fix)

Haveno uses JFoenix which accesses `com.sun.javafx.scene.NodeHelper` and `com.sun.javafx.scene.control.behavior.TabPaneBehavior` — internal JavaFX APIs. Add these `--add-exports` flags or the GUI fails silently (invisible 10x10px window):

```bash
export JAVA_HOME="$HOME/.sdkman/candidates/java/21.0.2.fx-librca"
cd ~/Documents/haveno

exec "$JAVA_HOME/bin/java" \
    --add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED \
    --add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED \
    -jar desktop/build/libs/desktop-1.6.0-SNAPSHOT-all.jar \
    --baseCurrencyNetwork=XMR_MAINNET \
    --useLocalhostForP2P=false \
    --useDevPrivilegeKeys=false \
    --nodePort=9999 \
    --appName=Haveno \
    --apiPassword=apitest \
    --apiPort=1201 \
    --useNativeXmrWallet=false \
    --ignoreLocalXmrNode=false
```

### Clean Restart

On restart, the monero-wallet-rpc may still hold a lock:

```bash
pkill -9 -f haveno
pkill -9 -f monero-wallet-rpc
pkill -9 -f monerod
sleep 2
rm -rf ~/.local/share/Haveno/xmr_mainnet/wallet/
```

Haveno bundles its own Tor (no system Tor needed). The default seed node is a placeholder — configure a real third-party seed node in Settings to connect to a Haveno network.

## Pitfalls

- **Seed phrase portability** — A 25-word Monero seed can be restored in ANY Monero wallet (Feather, Cake Wallet, Monero CLI, etc.). The same seed works across platforms.
- **GUI automation is unreliable** — Feather is a Qt5/QML app and xdotool/click automation often fails with KWin compositor. Present the seed phrase and let the user restore manually.
- **Wordlist verification** — Always use the official Monero wordlist from the GitHub C header. Many third-party wordlists on the web are outdated or incorrect. A seed generated with a wrong wordlist will not restore.
- **AppImage dependencies** — Feather AppImage is self-contained (statically linked). No additional libraries needed on any modern Linux.
- **Tails has no Java** — Haveno needs Java 21+ with JavaFX, which Tails doesn't ship. Feather (pure C++/Qt) has no such dependency.
- **GUI automation is unreliable for Qt apps under KDE Plasma** — xdotool click events often silently fail on Qt widgets (QPushButton, QtQuick elements). `xdotool windowactivate` works for bringing windows to front but `xdotool click` on buttons inside the window may not register. The workaround is using `monero-wallet-cli + expect` for terminal-based wallet operations instead of Feather GUI automation.
- **KDE Plasma window name detection** — Under KDE Plasma, Qt windows may have empty `WM_NAME`/`_NET_WM_NAME` X11 properties even when the window is visible and focused. Use `xdotool search --pid <pid>` instead of searching by name. The window may be functional despite having no name property.
- **Screenshot pixel analysis for GUI detection** — Use PIL's `Image.getpixel()` to detect whether a GUI window is rendering on screen. The KDE Plasma desktop background base color is RGB(27,30,32). Feather wallet renders orange/warm tones (~RGB(244,167,14)). Haveno renders a dark theme (~RGB(42,46,50)). A 10x10 pixel window at (10,10) indicates a JavaFX crash (usually module access errors).
- **Seed verification** — Always verify a generated seed can be restored with `monero-wallet-cli --restore-deterministic-wallet` before telling the user it's valid. This is the only reliable verification.
- **Haveno wallet lock on restart** — After killing Haveno, `monero-wallet-rpc` may hold a file lock on `~/.local/share/Haveno/xmr_mainnet/wallet/haveno_XMR.keys`. Kill all three processes and delete the wallet directory: `pkill -9 -f monero-wallet-rpc; pkill -9 -f monerod; rm -rf ~/.local/share/Haveno/xmr_mainnet/wallet/`.
