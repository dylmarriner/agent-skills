---
name: crypto-anonymity-stack
description: Hardened Tor/proxychains/DNS anonymity stack for Linux workstations. Install, configure, and verify Tor with proxychains and DNS privacy.
version: 1.0.0
author: Hermes Agent + user
platforms: [linux]
---

# Crypto Anonymity Stack

Set up a hardened Tor + proxychains + DNS privacy stack for anonymous network access. Supports iptables killswitch with Hermes API exceptions.

## When to Use

- User asks to "hide my network identity", "make me anonymous", "set up Tor"
- User wants to route apps/cli through Tor
- User mentions proxychains, torsocks, Tor Browser
- User wants DNS privacy or leak prevention

## Check Prerequisites

```bash
# Check if Tor is installed and running
systemctl is-active tor@default
ss -tlnp | grep 9050   # Tor SOCKS port
```

## Install Components

```bash
sudo apt install -y proxychains4 torsocks nyx
```

Tor is typically pre-installed on Ubuntu. Verify with `systemctl status tor@default`.

## Configure

### Tor (hardened config at /etc/tor/torrc)

Essential settings — this requires sudo, so write to /tmp first and instruct user:
```
SocksPort 9050
SocksPort 127.0.0.1:9050 IsolateDestAddr IsolateDestPort IsolateClientProtocol IsolateSOCKSAuth
SocksPolicy accept 127.0.0.0/8
SocksPolicy reject *
DNSPort 5353
TransPort 9040
ControlPort 9051
CookieAuthentication 1
ExitRelay 0
BridgeRelay 0
SafeLogging 1
DisableDebuggerAttachment 1
```

### Proxychains (~/.proxychains4.conf)

Use dynamic_chain, proxy DNS, exclude local subnets including Tailscale (100.0.0.0/8):

```ini
dynamic_chain
proxy_dns
localnet 127.0.0.0/255.0.0.0
localnet 10.0.0.0/255.0.0.0
localnet 172.16.0.0/255.240.0.0
localnet 192.168.0.0/255.255.0.0
localnet 100.0.0.0/255.0.0.0   # Tailscale
[ProxyList]
socks5 127.0.0.1 9050
```

### Torsocks (~/.torsocks.conf)

```ini
TOR_SOCKS_IP=127.0.0.1
TOR_SOCKS_PORT=9050
TOR_DNS_IP=127.0.0.1
TOR_DNS_PORT=5353
```

## Verify

```bash
# Direct SOCKS5 test
curl -s --socks5-hostname 127.0.0.1:9050 https://check.torproject.org | grep -i congratulations

# Proxychains test
proxychains4 -q curl -s https://check.torproject.org | grep -i congratulations
```

## Hermes Compatibility

Proxychains is **opt-in** (prefix commands with `proxychains4`). Hermes runs normally without it.

The **iptables killswitch** blocks ALL non-Tor traffic and WILL BREAK Hermes API calls. If applied, add exceptions:

```bash
sudo iptables -A OUTPUT -d api.deepseek.com -j ACCEPT
sudo iptables -A OUTPUT -d openrouter.ai -j ACCEPT
# Add any other API endpoints Hermes uses
```

## Tails USB Operations

Tails persistent storage uses LUKS encryption:

```bash
# Identify the Tails USB
lsblk -o NAME,SIZE,TYPE,LABEL,FSTYPE
# TailsData partition will be labeled "TailsData" with type crypto_LUKS

# Open LUKS
sudo cryptsetup luksOpen /dev/sdX2 tails_data --key-file=/tmp/keyfile

# Mount
sudo mkdir -p /mnt/tails_data
sudo mount /dev/mapper/tails_data /mnt/tails_data

# Files go to /mnt/tails_data/Persistent/

# Clean up
sudo umount /mnt/tails_data
sudo cryptsetup luksClose tails_data
```

## Pitfalls

- **iptables killswitch breaks Hermes**: Always warn the user and leave commented-out ACCEPT rules for their API endpoints in the setup script
- **Tailscale IPs excluded**: Add `localnet 100.0.0.0/255.0.0.0` to proxychains so local cluster traffic bypasses Tor
- **User password needed for sudo**: Tor config and proxychains system installs need sudo. Write configs to home dir and provide a setup script
- **Tails persistent storage is LUKS**: The password trick works with `printf` + `--key-file=/dev/stdin` or a temp file + shred
