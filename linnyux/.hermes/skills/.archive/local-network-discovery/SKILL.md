---
name: local-network-discovery
description: Discover and identify devices on a local subnet — MAC-based vendor lookup, port probing, and fallback when router UIs show empty device lists.
---

# Local Network Discovery

Discover devices on a local subnet, identify them by MAC OUI, and probe for services. Use when the user asks "find devices on my network", "what's connected", or "find a specific device (Sony/Samsung/etc)".

## Prerequisites

- `arp-scan` installed (`sudo apt install arp-scan -y`)
- `nmap` installed
- Root/sudo for arp-scan (needs raw sockets)

## Workflow

### 1. Quick subnet scan (arp-scan — primary method)

Most reliable way to discover all devices. Returns IP, MAC, and vendor name in one shot.

```bash
sudo arp-scan --local --ignoredups
```

Or specify subnet explicitly:
```bash
sudo arp-scan 192.168.1.0/24
```

Notes:
- Faster than nmap -sn (1-2 seconds vs 10-30s)
- Shows every device that has an active ARP cache entry
- Uses `/usr/share/arp-scan/ieee-oui.txt` for vendor names
- If vendors show as "(Unknown)", the OUI database may need updating or the MAC isn't in it

### 2. Ping sweep fallback (nmap)

When arp-scan misses hosts (e.g. firewalled devices):

```bash
nmap -sn 192.168.1.0/24
```

Shows DNS hostnames if available. Slower but catches devices arp-scan might miss.

### 3. MAC OUI vendor lookup

If vendor comes back as "(Unknown)" or you need confirmation:

```bash
grep -i "5C843C" /usr/share/arp-scan/ieee-oui.txt
```

OUI format: `LINE_NUM:HEX_OUI\tVendor Name` (no colons, e.g. `5C843C` for `5c:84:3c`)

### 4. Port probing (when nmap is slow/timing out)

Some devices (PlayStations, IoT) don't respond to SYN scan. Use netcat for quick checks:

```bash
nc -zv -w 1 <ip> <port>
```

Known device ports:
- **9295** — Sony PlayStation Remote Play (PS4/PS5)
- **80/443** — Web interfaces
- **22** — SSH

### 5. Service version scan (for devices that respond)

```bash
sudo nmap -sV -T4 --top-ports 50 <ip>
```

## Pitfalls

- **Router web UI device lists are unreliable.** ISP routers (Spark, etc.) often show empty Connected Devices tables even with active clients. Don't trust the web UI — always verify with arp-scan.
- **SYN scan (-sS, nmap default) times out on some devices** (Sony PlayStation, some IoT). Use `-sT` (TCP connect) or fall back to `nc -zv` for those.
- **arp-scan needs sudo** — without it you get no results. The user needs passwordless sudo for arp-scan or a sudoers entry.
- **Some devices share MACs** (Sonos speakers, WiFi extenders with wired/wireless interfaces). Same MAC on different IPs = same physical device.
- **locally-administered MACs** (2nd octet bit 1 set, like `86:c8:52:xx:xx:xx`) are randomized/private addresses — vendor lookup won't work.

## Verification

Run `sudo arp-scan --local` and confirm the output lists the expected devices with correct vendors. Cross-reference IPs against the router's lease list if accessible.
