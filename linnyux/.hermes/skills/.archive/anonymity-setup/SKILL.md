---
name: anonymity-setup
description: "Tor hardening, proxychains, DNS privacy, and iptables killswitch for network anonymity on Linux."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tor, proxychains, anonymity, dns-privacy, privacy, security]
    related_skills: [haveno-setup, crypto-wallet-setup]
---

# Anonymity Setup

Configure Tor, proxychains, torsocks, and optional iptables killswitch for network anonymity. Designed for workstation/desktop use where Hermes and other tools still need API access.

## When to Use This Skill

Trigger when the user:
- Wants to "hide my IP", "go anonymous", "use Tor for everything"
- Asks about proxychains, torsocks, or routing apps through Tor
- Wants a firewall killswitch to prevent non-Tor traffic
- Wants DNS privacy (DNS over Tor)
- Mentions Tails, Whonix, or other anonymity OSes

## Components Installed

| Component | Package | Purpose |
|-----------|---------|---------|
| Tor | `tor` | SOCKS5 proxy on 127.0.0.1:9050 |
| Proxychains | `proxychains4` | Route any app through Tor |
| Torsocks | `torsocks` | Alternative Tor wrapper |
| Nyx | `nyx` | Real-time Tor monitor |
| iptables | system | Optional killswitch |

## Step 1: Install Packages

```bash
sudo apt install -y tor proxychains4 torsocks nyx
```

## Step 2: Verify Tor is Running

```bash
systemctl is-active tor@default
# Should print: active

ss -tlnp | grep 9050
# Should show: LISTEN 127.0.0.1:9050
```

## Step 3: Configure Proxychains

Write `~/.proxychains4.conf` (user-local, no sudo needed):

```
dynamic_chain
proxy_dns
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000

# Exclude local networks from proxying
localnet 127.0.0.0/255.0.0.0
localnet 10.0.0.0/255.0.0.0
localnet 172.16.0.0/255.240.0.0
localnet 192.168.0.0/255.255.0.0
localnet 100.0.0.0/255.0.0.0   # Tailscale

[ProxyList]
socks5 127.0.0.1 9050
```

**Key points:**
- Use `dynamic_chain` (skips dead proxies) not `strict_chain`
- Add `100.0.0.0/8` for Tailscale — otherwise Tailscale IPs route through Tor and fail
- Use `socks5` not `socks4` for DNS proxy support

## Step 4: Configure Torsocks

Write `~/.torsocks.conf`:

```
TOR_SOCKS_IP=127.0.0.1
TOR_SOCKS_PORT=9050
TOR_DNS_IP=127.0.0.1
TOR_DNS_PORT=5353
TOR_ALLOW_INBOUND=1
TOR_SKIP_NETWORKS=127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.0.0.0/8
```

## Step 5: Verify

```bash
# Direct SOCKS5 test
curl -s --socks5-hostname 127.0.0.1:9050 https://check.torproject.org | grep -o "Congratulations[^<]*"

# Proxychains test
proxychains4 -q curl -s https://check.torproject.org | grep -o "Congratulations[^<]*"

# IP check
proxychains4 -q curl -s https://api.ipify.org && echo
```

Both should show "Congratulations" and a Tor exit IP.

## Step 6: New Tor Circuit

```bash
echo -e "AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT" | nc -w2 127.0.0.1 9051
```

Requires `ControlPort 9051` in torrc (not enabled by default on Ubuntu).

## Step 7 (Optional): Hardened Tor Config

The default Ubuntu torrc at `/etc/tor/torrc` is minimal. A hardened config adds:
- `IsolateDestAddr IsolateDestPort` on the SOCKS port
- `DNSPort 5353` for DNS over Tor
- `TransPort 9040` for transparent torification
- `ExitRelay 0` (not a relay)
- `Sandbox 1` for kernel-level sandboxing

Apply with:
```bash
sudo cp /path/to/hardened-torrc /etc/tor/torrc
sudo chown root:root /etc/tor/torrc
sudo systemctl restart tor@default
```

## Pitfalls

- **Proxychains is opt-in** — Only commands prefixed with `proxychains4` route through Tor. Hermes and other tools run normally without it. Proxychains does NOT affect system-wide traffic.
- **iptables killswitch breaks Hermes** — If you apply the killswitch (block all non-Tor outbound), Hermes API calls to DeepSeek/OpenRouter/etc. will fail. Only use on a dedicated anonymity machine, or add specific ACCEPT rules for your API endpoints.
- **Tailscale breaks through Tor** — Tailscale IPs (100.x.x.x) are not routable over Tor. Always add `100.0.0.0/8` to proxychains localnet exclusions.
- **Synapse/remote services** — If Hermes connects to a remote proxy (Synapse, LiteLLM on another machine), that IP must also be in localnet exclusions if it's on a private network.
- **Tor circuits are slow** — First connection through a new circuit is slow (~3-5s handshake). Subsequent connections reuse the circuit. Use `tornewid` sparingly.
- **GUI apps and proxychains** — Not all GUI apps work with proxychains. Feather wallet, Tor Browser, and other Tor-aware apps handle Tor internally.
- **Torsocks vs proxychains** — `torsocks <cmd>` wraps the app in a LD_PRELOAD library. `proxychains4 <cmd>` uses ptrace. Torsocks is more compatible with complex apps; proxychains is more universal.
