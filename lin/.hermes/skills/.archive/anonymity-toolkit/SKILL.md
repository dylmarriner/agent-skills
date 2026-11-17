---
name: anonymity-toolkit
description: "Install and configure Tor, proxychains, torsocks, and anonymous crypto exchanges (Haveno) on Linux. Covers Hermes compatibility with anonymity stacks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tor, proxychains, haveno, anonymity, privacy, crypto-exchange, firefox, tails]
    related_skills: [red-teaming/godmode, secure-linux-web-hosting]
---

# Anonymity Toolkit

Install and configure an anonymity stack on Linux: hardened Tor, proxychains for app-level routing, and anonymous crypto exchanges (Haveno). Includes Hermes compatibility notes.

## When to Use This Skill

Trigger when the user asks to:
- "Hide my network identity"
- "Set up Tor routing for all traffic"
- "Install Haveno / Bisq / decentralized exchange from source"
- "Route apps through Tor transparently"
- "Install and set up anonymous tools"
- "Configure my system for privacy"

## Core Components

| Component | Purpose | Installation |
|-----------|---------|-------------|
| **Tor** | Anonymous network layer (SOCKS5 on :9050) | `apt install tor` — runs as systemd service |
| **Proxychains4** | Route any CLI app through Tor transparently | `apt install proxychains4` — config at `/etc/proxychains4.conf` or `~/.proxychains4.conf` |
| **Torsocks** | Alternative Tor routing wrapper | `apt install torsocks` — config at `~/.torsocks.conf` |
| **Nyx** | Real-time Tor circuit monitor | `apt install nyx` — run `nyx -i 127.0.0.1:9051` |
| **Haveno** | Anonymous P2P crypto exchange (Monero) | Build from source with Java 21 + JavaFX (see below) |
| **Feather Wallet** | Decentralized Monero wallet with native Tor | AppImage from GitHub releases |
| **setup-anonymity.sh** | One-shot script: hardened torrc + proxychains + optional iptables killswitch | Place at `~/setup-anonymity.sh` — see Step 5 |

## Step 1: Verify and Harden Tor

```bash
# Check if Tor is running
systemctl status tor@default
ss -tlnp | grep 9050  # should show listener

# Verify Tor works
curl -s --socks5-hostname 127.0.0.1:9050 https://check.torproject.org | grep -i "congratulations"
```

Hardened torrc goes in `/etc/tor/torrc`. Key settings:
- `SocksPort 9050` — standard SOCKS5
- `DNSPort 5353` — DNS through Tor
- `ExitRelay 0` — never an exit node
- `DisableDebuggerAttachment 1` — security hardening
- `Sandbox 1` — kernel-level isolation

## Step 2: Configure Proxychains

### User-local config (`~/.proxychains4.conf`):
```
dynamic_chain
proxy_dns
localnet 127.0.0.0/255.0.0.0
localnet 10.0.0.0/255.0.0.0
localnet 172.16.0.0/255.240.0.0
localnet 192.168.0.0/255.255.0.0
localnet 100.0.0.0/255.0.0.0   # Tailscale — don't route tailnet traffic through Tor
[ProxyList]
socks5 127.0.0.1 9050
```

### CRITICAL: Tailscale subnet exclusion
The `100.0.0.0/8` range (Tailscale) MUST be in localnet exclusions. Without this, Tailscale traffic (Synapse, cluster services) gets routed through Tor and breaks.

## Step 3: Hermes Compatibility

**Proxychains is opt-in — it does NOT affect Hermes.** Only commands explicitly prefixed with `proxychains4` route through Tor. Hermes runs as a normal process and makes direct API calls.

**The iptables killswitch WILL break Hermes.** If you apply firewall rules blocking all non-Tor outbound traffic, Hermes API calls to DeepSeek/OpenRouter will fail. Add explicit ACCEPT rules:
```bash
sudo iptables -A OUTPUT -d api.deepseek.com -j ACCEPT
sudo iptables -A OUTPUT -d openrouter.ai -j ACCEPT
sudo iptables -A OUTPUT -d 100.68.0.96 -j ACCEPT  # Synapse proxy if used
```

## Step 4: Install Haveno from Source

### Prerequisites
```bash
# Install SDKMan (Java version manager)
curl -s "https://get.sdkman.io" | bash
source ~/.sdkman/bin/sdkman-init.sh

# Install Java 21 with JavaFX (Liberica FX build)
sdk install java 21.0.2.fx-librca
sdk default java 21.0.2.fx-librca
```

### Build
```bash
git clone --depth 1 --branch master https://github.com/haveno-dex/haveno.git ~/Documents/haveno
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh
make skip-tests  # skip tests = faster build
```

### Launch
Haveno bundles its own Tor internally — no proxychains needed for Haveno itself.
```bash
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh
java -jar desktop/build/libs/desktop-*-all.jar \
  --baseCurrencyNetwork=XMR_MAINNET \
  --useLocalhostForP2P=false \
  --useDevPrivilegeKeys=false \
  --nodePort=9999 \
  --appName=Haveno \
  --apiPassword=apitest
```

## Conventions

- Tor config goes in `/etc/tor/torrc` (needs sudo)
- Proxychains config goes in `~/.proxychains4.conf` (user-local, no sudo)
- Haveno data dir: `~/.local/share/Haveno/`
- Always verify Tor works after config changes: `curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org`

## Step 5: One-Shot Setup Script

Create `~/setup-anonymity.sh` for bulk application (useful when setting up a new machine):

```bash
#!/bin/bash
# [1/6] Hardened torrc        → sudo cp /tmp/hardened-torrc /etc/tor/torrc
# [2/6] Proxychains config    → cp ~/.proxychains4.conf + sudo to /etc/
# [3/6] Verify Tor            → check.torproject.org curl test
# [4/6] Firewall killswitch   → iptables (OPTIONAL, breaks Hermes — see Step 3)
# [5/6] DNS privacy           → point to Tor's DNSPort
# [6/6] Load aliases          → source ~/.anonymity-aliases
```

The script asks confirmation before applying the killswitch and includes commented-out Hermes API exception rules.

## Step 6: Feather Wallet for Tails OS

Feather (https://featherwallet.org) is the best decentralized Monero wallet for Tails. It's lightweight (no blockchain download), Tor-native, and fully P2P.

### Install on this machine (for transfer to Tails USB):
```bash
wget https://github.com/feather-wallet/feather/releases/download/2.8.1/feather-2.8.1.AppImage
chmod +x feather-2.8.1.AppImage
# Verify: ./feather-2.8.1.AppImage --help
```

### Install on Tails persistent storage:
```bash
# 1. Identify Tails USB — usually sda with two partitions:
#    sda1 = TAILS (FAT32, ~8GB system)
#    sda2 = TailsData (LUKS, ~rest of space — persistent storage)

# 2. Unlock the LUKS container:
sudo cryptsetup luksOpen /dev/sda2 tails_data --key-file=/tmp/tails_key
sudo mkdir -p /mnt/tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data

# 3. Copy files:
sudo cp feather-wallet.AppImage /mnt/tails_data/Persistent/
sudo chown amnesia:amnesia /mnt/tails_data/Persistent/feather-wallet.AppImage
sudo chmod +x /mnt/tails_data/Persistent/feather-wallet.AppImage

# 4. Clean up:
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
sudo shred -u /tmp/tails_key
```

### On Tails:
```bash
cd ~/Persistent && ./feather-wallet.AppImage --use-local-tor
```
The `--use-local-tor` flag tells Feather to use Tails' system Tor at 127.0.0.1:9050 instead of its bundled Tor. Create a new wallet and save the seed phrase on paper.

## Pitfalls

See also `references/haveno-build.md` for detailed Haveno build commands and `references/tails-setup.md` for Tails persistent storage mounting/setup.

1. **No sudo access for torrc changes** — Write the config to /tmp and let the user run `sudo cp /tmp/hardened-torrc /etc/tor/torrc && sudo systemctl restart tor@default`
2. **Tailscale breaks through proxychains** — Always add `100.0.0.0/8` to localnet exclusions or Tailscale connections (Synapse MCP, SSH to other machines) will fail silently
3. **Firewall killswitch breaks Hermes** — The iptables-based killswitch blocking all non-Tor traffic will prevent Hermes from making API calls. Always add ACCEPT rules for API endpoints or don't run killswitch on the Hermes machine
4. **SDKMan sourcing across shells** — SDKMan needs to be sourced in each new shell: `source ~/.sdkman/bin/sdkman-init.sh`. The `make` command won't find the right Java version without it
5. **Haveno has no pre-built binaries** — Must be built from source. No official mainnet is operated — user needs a third-party network or seed node
6. **JavaFX requirement** — Haveno needs a JDK with JavaFX bundled. Ubuntu's packaged OpenJFX is version 11 which conflicts with JDK 21. Use Liberica FX build from SDKMan
7. **Haveno build artifacts** — The fat jar is at `desktop/build/libs/desktop-*-all.jar` (~186MB). The smaller jar at `desktop/build/libs/desktop-*.jar` (~4MB) needs classpath setup
8. **Tor checks fail inside Sandbox** — When running `execute_code` tests, the sandbox doesn't inherit shell env vars. Load dotenv explicitly or pass values directly
9. **Tails persistent storage is LUKS-encrypted** — Must use `cryptsetup luksOpen` before mounting. The key file approach (`--key-file=/tmp/key`) works when piping passwords doesn't. Always `shred -u` the key file after use
10. **Feather wallet `--use-local-tor` flag** — On Tails or any system with a running Tor daemon, use this flag to avoid conflicts with Feather's bundled Tor binary. Without it, Feather starts its own Tor which may fail on locked-down systems
11. **Tails persistent ownership is `amnesia:amnesia`** — Files copied to TailsData from another machine must have ownership changed to `amnesia` or they won't be writable on Tails
