---
name: decentralized-exchange
description: Install, build, configure, and troubleshoot decentralized P2P exchanges (Haveno). Covers source builds, JavaFX fixes, seed node management, and wallet setup.
version: 1.0.0
author: Hermes Agent + user
platforms: [linux]
---

# Decentralized Exchange Setup

Install and configure decentralized P2P exchanges built on Monero + Tor (Haveno). Covers building from source, JavaFX module fixes, seed node configuration, and wallet initialization.

## When to Use

- User asks to "install Haveno", "set up Haveno", "build Haveno"
- User wants a decentralized Monero exchange
- User encounters JavaFX module access errors with JFoenix
- User sees "no seed nodes available" or "filter object" warnings
- User needs to run seed nodes for their own Haveno network

## Build from Source

### Dependencies

- Java JDK 21 with JavaFX (Liberica FX): `sdk install java 21.0.2.fx-librca` via SDKMan
- Git, make, wget

### Clone and Build

```bash
git clone https://github.com/haveno-dex/haveno.git ~/Documents/haveno
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh
make skip-tests
```

### Launch Script

Use a script that includes JFoenix JavaFX module access fixes:

```bash
#!/bin/bash
HAVENO_DIR="$HOME/Documents/haveno"
JAVA_HOME="$HOME/.sdkman/candidates/java/21.0.2.fx-librca"
export JAVA_HOME PATH="$JAVA_HOME/bin:$PATH"
cd "$HAVENO_DIR"

exec "$JAVA_HOME/bin/java" \
    --add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED \
    --add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED \
    --add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED \
    --add-exports javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED \
    --add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED \
    -jar "$HAVENO_DIR/desktop/build/libs/desktop-1.6.0-SNAPSHOT-all.jar" \
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

## Seed Node Configuration

The official Haveno repo ships with `placeholder.onion:8000` as a stub. To actually use Haveno:

### Option A: Run a Local Seed Node

```bash
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh
make seednode  # Port 1002
make seednode2  # Port 3003 (second for redundancy)
```

### Option B: Join a Third-Party Network

Find a community Haveno network and configure their seed node address.

### Configuring Seed Nodes

Update the `xmr_mainnet.seednodes` resource file in both source and build output:

```
# nodeaddress.onion:port [(@owner,@backup)]
<your_seed_node_onion>:1002 (@local)
```

Update these files:
- `core/src/main/resources/xmr_mainnet.seednodes`
- `core/build/resources/main/xmr_mainnet.seednodes`

Then rebuild or update the JAR:
```bash
# Rebuild
make skip-tests
# OR directly patch the fat JAR
cd /tmp
echo '<your_seed>:1002 (@local)' > xmr_mainnet.seednodes
zip -f ~/Documents/haveno/desktop/build/libs/desktop-1.6.0-SNAPSHOT-all.jar xmr_mainnet.seednodes
```

## Troubleshooting

### JavaFX JFoenix Errors

If you see `IllegalAccessError: class com.jfoenix.skins.JFX... cannot access class com.sun.javafx...`, add the relevant `--add-exports`/`--add-opens` flags to the Java command.

Known required flags:
```
--add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED
--add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED
--add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED
--add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED
--add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED
--add-exports javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED
--add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED
```

### Wallet Lock Errors

`"haveno_XMR.keys" is opened by another wallet program` — a monero-wallet-rpc from a previous run is still alive. The process may be orphaned if the Haveno process was killed without clean shutdown. Fix:

```bash
# Kill ALL monero and haveno processes
pkill -9 -f monero-wallet-rpc
pkill -9 -f "desktop-1.6.0-SNAPSHOT"
sleep 3
# Remove stale wallet data so the new run creates fresh
rm -rf ~/.local/share/Haveno/xmr_mainnet/wallet/
# Then restart
```

Always check with `ps aux | grep monero` before restarting — stale RPC processes can persist across multiple restarts.

### "Placeholder.onion" Seed Node

Expected. The placeholder is a stub. Configure a real seed node (see above).

### Monero Node Sync Timeouts

Haveno retries multiple public Monero nodes. It will eventually connect. Common nodes:
- `node.monerodevs.org:18089`
- `rucknium.me:18081`
- `node2.monerodevs.org:18089`

## Pitfalls

- **Java version matters**: Ubuntu's default JDK 21 lacks JavaFX. Use Liberica FX via SDKMan
- **Placeholder seed node is not real**: You MUST configure seed nodes. Run `make seednode` or join a community network
- **Rebuild needed for seednode changes**: Source file changes aren't picked up until `make` or JAR patching
- **Multiple monero-wallet-rpc builds up**: Each restart spawns a new RPC process on a different port. The old ones hold wallet locks
