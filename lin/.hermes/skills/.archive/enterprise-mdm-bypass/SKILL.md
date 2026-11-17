---
name: enterprise-mdm-bypass
description: >
  Bypass enterprise MDM (Miradore, Samsung Knox, Android Enterprise) enrollment
  via network-level DNS interception, USB protocol probing, traffic capture, and
  controlled WiFi hotspot. Multi-protocol approach combining USB/MTP access,
  modem AT commands, download mode, and network-layer blocking.
---

# Enterprise MDM Bypass — Network Interception Approach

## Strategy

MDM bypass works in layers. The most effective approaches combine multiple vectors:

1. **Network-level DNS blocking** — intercept the phone's DNS via a controlled hotspot
2. **USB/MTP access** — read MDM app logs, identify server endpoints
3. **Modem AT commands** — probe CDC ACM serial for USB mode switching
4. **Download mode** — attempt ODIN protocol for partition-level access
5. **Traffic capture and analysis** — identify all MDM-specific servers the phone contacts

## Prerequisites

- Linux machine with WiFi adapter supporting AP mode (hostapd)
- NetworkManager + nmcli
- dnsmasq (for hotspot DNS)
- tcpdump / tshark / Wireshark
- pyusb + libusb
- adb (optional, for post-bypass)
- A phone with USB cable

## Phase 1: Discovery via MTP

### 1. Connect phone in MTP mode

The phone should enumerate at `0x04E8:0x6860` (Samsung MTP). There's typically a CDC ACM serial at `/dev/ttyACM0`.

```bash
lsusb | grep 04e8
# Expected: 04e8:6860 Samsung (MTP mode)
```

### 2. Mount MTP and extract MDM logs

```bash
mkdir -p /tmp/mtp_mount
go-mtpfs /tmp/mtp_mount &
# Accept file sharing on phone when prompted
find /tmp/mtp_mount/ -name "*.log" -path "*miradore*" 2>/dev/null
```

Key files to check:
- `Android/data/com.miradore.client.v2/files/miradore.log.0` — Miradore enrollment log
- `Android/data/com.android.managedprovisioning/files/` — Android provisioning

### 3. Analyze MDM log to find server endpoints

```bash
grep -E "(server|host|domain|register|connect)" miradore.log.0 | grep -v "at\." | sort -u
```

Look for:
- **Enrollment key** (`EnrollmentKey><![CDATA[...]]>`)
- **Server URL** (`gateway.miradore.com`, `dir-apis.samsungdm.com`, etc.)
- **Registration status** (`client registration failed`, `DEVICE_ADMIN_ENABLED`)
- **Knox/Samsung DM endpoints** (`gsl.samsunggsl.com`, `samsungdm.com`)

## Phase 2: Modem AT Command Probing

The CDC ACM serial can be used to probe the phone's modem.

```python
import serial, time
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=2)
ser.write(b'AT\r\n')
time.sleep(1)
print(ser.read(1024))
```

Critical findings:
- `PACM(AP),UNREGISTED` — AP-side proxy blocking command
- `AT+SWATD=0` — triggers modem internal mode switch (DDEXE mode)
- `AT+SWATD=1` — ATD mode
- Most privileged commands are blocked by PACM(AP) proxy

## Phase 3: Controlled Hotspot with DNS Blocking

### 1. Create hotspot with NetworkManager

```bash
# Disconnect from current WiFi
nmcli device disconnect wlo1

# Create hotspot
nmcli device wifi hotspot ifname wlo1 ssid "MDM-Bypass" password "bypass1234"
# Note hotspot IP (typically 10.42.0.1)
```

### 2. Block MDM DNS

Find the dnsmasq config directory NM's hotspot uses:
```bash
# Check actual process arguments
ps aux | grep dnsmasq | grep -v grep
# Look for --conf-dir=...
# Usually /etc/NetworkManager/dnsmasq-shared.d/
```

Create block config **with both IPv4 and IPv6**:
```bash
echo "address=/target-domain.com/0.0.0.0
address=/target-domain.com/::" | sudo tee /etc/NetworkManager/dnsmasq-shared.d/block-mdm.conf
```

Critical: ALWAYS add `::` for IPv6 — phones will fall back to IPv6 otherwise.

### 3. Apply and verify

```bash
sudo systemctl restart NetworkManager
sleep 3
nmcli connection up Hotspot
sleep 2

# Verify
nslookup gateway.miradore.com 10.42.0.1
# Expected: Address: 0.0.0.0 and Address: ::
nslookup google.com 10.42.0.1
# Expected: Address: <real IP>
```

### 4. Clean up stale configs

If reconfiguring, remove ALL stale dnsmasq config files from both directories:
```bash
sudo rm /etc/NetworkManager/dnsmasq.d/block-*.conf
sudo rm /etc/NetworkManager/dnsmasq-shared.d/block-*.conf
nmcli connection modify Hotspot ipv4.dns-options ""
nmcli connection modify Hotspot ipv6.dns-options ""
```

## Phase 4: Traffic Capture and MDM Server Discovery

### 1. Find phone IP

```bash
# Scan hotspot subnet
nmap -sn 10.42.0.0/24
```

### 2. Capture all phone traffic

```bash
sudo tcpdump -i wlo1 -nn -s0 -w /tmp/phone_traffic.pcap 'host 10.42.0.X'
```

### 3. Analyze for MDM endpoints

```bash
# TLS Server Name Indication
tshark -r phone_traffic.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn

# DNS queries
tshark -r phone_traffic.pcap -Y "dns.flags.response == 0" \
  -T fields -e dns.qry.name | sort | uniq -c | sort -rn

# Destination IPs (filter out Google CDN)
tshark -r phone_traffic.pcap -T fields -e ip.dst | \
  grep -v "^10\.42\." | grep -v "^142\.250\|^172\.217" | \
  sort | uniq -c | sort -rn
```

### Known MDM server domains to watch for:
- `gateway.miradore.com` — Miradore cloud gateway (Azure Front Door backed)
- `dir-apis.samsungdm.com` — Samsung Device Management API
- `gsl.samsunggsl.com` / `eu-gslu.samsunggsl.com` — Samsung Global Service Logic
- `pinning-02.secb2b.com` — Certificate pinning
- `samsungdm.com` — Samsung DM
- `auditrecording-pa.googleapis.com` — Android Management API audit
- `gmscompliance-pa.googleapis.com` — Google Play compliance

## Phase 5: Iterative Blocking Strategy

1. **Clean pass first** — remove all DNS blocks, let phone connect freely
2. **Let setup progress** through update checks (these need Google/Samsung CDN)
3. **Capture the MDM enrollment attempt** — watch TLS SNI for MDM domains
4. **Block discovered domains** — add only MDM-specific domains to dnsmasq config
5. **Keep samsung.com and general CDN accessible** — the phone needs these for normal operation

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Couldn't update" in setup | Blocking samsung.com or Google CDN | Remove blocks, let update proceed |
| Still enrolls after block | Phone used cellular data | Turn on airplane mode, use hotspot only |
| Device admin active without server | Pre-installed system app | Need ADB or recovery wipe |
| No traffic in pcap | Phone on different network | Check phone WiFi connection |
| DNS block only works for IPv4 | IPv6 not blocked | Add `address=/domain/::` entries |
| NM hotspot drops on restart | NM reconnects to known WiFi | `nmcli device disconnect wlo1` first |

## Pitfalls

- Miradore/Samsung DM can be pre-installed as a system app — survives factory reset
- DNS cache on phone persists — disconnect/reconnect WiFi to clear
- The phone may fall back to cellular data if hotspot isn't the only connection
- Setup wizard update check contacts different servers than MDM enrollment
- Some domains serve dual purpose (update + MDM check) — requires iterative approach

## References

See `references/samsung-a54-mdm-bypass.md` for the session-specific domain list, AT command findings, and server endpoints discovered during real testing.
