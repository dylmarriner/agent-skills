---
name: haveno-setup
description: "Build Haveno decentralized P2P exchange from source. Clone repo, install Java 21 with JavaFX, compile with make skip-tests, and launch on XMR_MAINNET."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [haveno, dex, monero, exchange, decentralized, java, build-from-source]
    related_skills: [crypto-wallet-setup, anonymity-setup]
---

# Haveno Setup

Build the Haveno decentralized P2P exchange from source. Haveno is a Monero-based DEX (decentralized exchange) that routes all P2P traffic through Tor internally.

## When to Use This Skill

Trigger when the user:
- Asks to "install Haveno", "build Haveno", "set up a decentralized exchange"
- Wants a P2P crypto exchange that works with Monero
- Mentions Bisq or Haveno
- Wants to trade crypto without KYC

## Install Dependencies

### Java 21 with JavaFX

Ubuntu's default JDK 21 (openjdk-21) does NOT include JavaFX. Use SDKMan to install a Liberica FX build:

```bash
# Install SDKMan
curl -s "https://get.sdkman.io" | bash
source ~/.sdkman/bin/sdkman-init.sh

# Install Java 21 with JavaFX
sdk install java 21.0.2.fx-librca
sdk default java 21.0.2.fx-librca
```

Verify:
```bash
java --version
# openjdk 21.0.2 2024-01-16 LTS
```

### System Packages

```bash
sudo apt install -y make wget git
```

## Build from Source

```bash
git clone https://github.com/haveno-dex/haveno.git
cd haveno

# Build (skip tests for speed)
source ~/.sdkman/bin/sdkman-init.sh
make skip-tests
```

Build takes ~4-5 minutes on a modern laptop (81 Gradle tasks).

### Build Artifacts

| Artifact | Path | Size |
|----------|------|------|
| Desktop fat jar | `desktop/build/libs/desktop-*-all.jar` | ~186MB |
| Desktop jar | `desktop/build/libs/desktop-*.jar` | ~4.3MB |
| Daemon jar | `daemon/build/libs/daemon.jar` | ~108KB |
| CLI jar | `cli/build/libs/cli.jar` | varies |
| Seednode | `seednode/build/libs/seednode-all.jar` | varies |

### Update

```bash
cd ~/Documents/haveno
git fetch --tags
git checkout master
source ~/.sdkman/bin/sdkman-init.sh
make clean && make skip-tests
```

## JavaFX Module Fix (Required for Java 21+)

Haveno uses JFoenix which accesses internal JavaFX APIs. Java 21+ enforces module access restrictions via the Java Platform Module System (JPMS), causing JFoenix to crash at runtime with `IllegalAccessError`.

**Without these flags**, the Haveno GUI window is created but invisible — it shows as a 10x10 pixel window on screen and the user sees only a dark desktop background.

### Symptoms & Fixes

| Error | Missing `--add-exports` |
|-------|------------------------|
| `JFXSpinnerSkin cannot access com.sun.javafx.scene.NodeHelper` | `javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED` |
| `JFXTabPaneSkin cannot access com.sun.javafx.scene.control.behavior.TabPaneBehavior` | `javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED` |

### Launch with Fixes

```bash
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh

java \
    --add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED \
    --add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED \
    --add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED \
    -jar desktop/build/libs/desktop-*-all.jar \
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

### Launcher Script

Save the full command with `--add-exports` flags to `~/Documents/haveno/launch-haveno.sh` so it's repeatable. The script must source SDKMan's Java before running.

### Via Makefile

```bash
cd ~/Documents/haveno
make haveno-desktop-mainnet
```

### Stagenet (test network)

```bash
cd ~/Documents/haveno
make user1-desktop-stagenet
# Then use stagenet faucet to get test XMR
```

## Firewall / Anonymity

- **Haveno bundles its own Tor binary** — all P2P traffic routes through Tor automatically. No proxychains or external Tor needed.
- **Mainnet requires a third-party seed node** — The official repo doesn't provide seed nodes. Find a community network and configure their seed node in Haveno's settings.
- **No KYC** — Haveno uses Monero's privacy features and Tor to keep trades anonymous.

## Pitfalls

- **No pre-built binaries** — Haveno does not provide official AppImages or .deb packages. All releases have zero assets attached. Build from source is the only way.
- **JavaFX required at runtime** — The desktop GUI needs JavaFX. Using the Liberica FX JDK from SDKMan is the most reliable approach. Ubuntu's `openjfx` package is version 11 (incompatible).
- **Build requires git checkout of master** — The `v1.6.0` tag has no assets either. Always build from master.
- **Make targets differ by network** — Run `grep -E '^[a-z].*:' Makefile | grep -iE 'mainnet|stagenet|daemon|desktop'` to see all available targets.
- **Launcher script needs SDKMan Java** — A launch script at `~/Documents/haveno/launch-haveno.sh` should export `JAVA_HOME` and `PATH` to point at the SDKMan JDK, not the system JDK.
- **Wallet file locking on restart** — Haveno's monero-wallet-rpc locks `~/.local/share/Haveno/xmr_mainnet/wallet/haveno_XMR.keys` on first run. If Haveno crashes or is force-killed, subsequent launches fail with `"is opened by another wallet program"`. Fix: kill all `monero-wallet-rpc` and `monerod` processes, then `rm -rf ~/.local/share/Haveno/xmr_mainnet/wallet/` before restarting.
- **Seed node is a placeholder** — `placeholder.onion:8000` is a stub. Haveno will warn `"No filter object from seed nodes"`. The app still starts and does peer discovery, but trading requires a real third-party network seed node.
