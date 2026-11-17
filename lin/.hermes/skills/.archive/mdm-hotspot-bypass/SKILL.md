---
name: mdm-hotspot-bypass
description: "Bypass Samsung MDM enrollment during setup wizard using DNS-blocked WiFi hotspot + traffic capture. For Miradore/Samsung Knox Manage pre-enrollment devices stuck at setup."
version: 1.0.0
tags: [samsung, mdm, miradore, knox, dns, hotspot, enrollment, bypass]
---

# MDM Hotspot Bypass — Pre-Enrollment Samsung Bypass

**Trigger:** Samsung device at setup wizard, Miradore/Knox MDM detected (pre-enrollment or fresh factory reset). When the user needs to complete setup without MDM activating.

**Key insight:** MDM enrollment happens during setup via network calls. If you control the network, you control enrollment. A DNS-blocked WiFi hotspot lets the phone reach the internet normally but silently kills MDM server connections with 0.0.0.0 responses.

**Tested on:** SM-S921B (S24) — clean setup, no MDM activation. SM-A546E (A54) — local Device Admin activates regardless, but server enrollment blocked.

## Workflow

### Step 1 — Create DNS-Blocked Hotspot

```bash
# Disconnect from any existing WiFi
nmcli device disconnect wlan0
sleep 2

# Create hotspot
nmcli device wifi hotspot ifname wlan0 ssid "MDM-Bypass" password "bypass1234"
sleep 3

# Block MDM domains (NetworkManager hotspot uses dnsmasq-shared.d)
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
cat <<'EOF' | sudo tee /etc/NetworkManager/dnsmasq-shared.d/block-mdm.conf
# Miradore
address=/gateway.miradore.com/0.0.0.0
address=/gateway.miradore.com/::
address=/miradore.com/0.0.0.0
address=/miradore.com/::
# Samsung Device Management
address=/samsungdm.com/0.0.0.0
address=/samsungdm.com/::
address=/api.gras.samsungdm.com/0.0.0.0
address=/api.gras.samsungdm.com/::
address=/diagmon-serviceapi.samsungdm.com/0.0.0.0
address=/diagmon-serviceapi.samsungdm.com/::
address=/dir-apis.samsungdm.com/0.0.0.0
address=/dir-apis.samsungdm.com/::
# Samsung GSL (Global Service Logic)
address=/samsunggsl.com/0.0.0.0
address=/samsunggsl.com/::
address=/gsl.samsunggsl.com/0.0.0.0
address=/gsl.samsunggsl.com/::
address=/eu-gslu.samsunggsl.com/0.0.0.0
address=/eu-gslu.samsunggsl.com/::
# Samsung B2B certificate pinning
address=/secb2b.com/0.0.0.0
address=/secb2b.com/::
# Microsoft Azure (Miradore CDN/telemetry pipes)
address=/mobile.pipe.aria.microsoft.com/0.0.0.0
address=/mobile.pipe.aria.microsoft.com/::
address=/mobile.events.data.microsoft.com/0.0.0.0
address=/mobile.events.data.microsoft.com/::
EOF

# Restart to apply
sudo systemctl restart NetworkManager
sleep 3
nmcli connection up Hotspot
```

### Step 2 — Verify DNS Blocks

```bash
for domain in gateway.miradore.com api.gras.samsungdm.com dir-apis.samsungdm.com gsl.samsunggsl.com secb2b.com; do
    nslookup $domain 10.42.0.1 | grep "Address:" | tail -1
done
# All should return 0.0.0.0 or ::
# google.com should still resolve normally
```

### Step 3 — Start Traffic Capture

```bash
# Find phone IP after connection
sudo cat /var/lib/NetworkManager/dnsmasq-wlo1.leases

# Capture ONLY phone traffic (substitute IP)
sudo tcpdump -i wlan0 -nn -s0 -w /tmp/phone_setup.pcap 'host 10.42.0.XX' &
```

### Step 4 — Phone Setup Flow

1. Connect phone to hotspot "MDM-Bypass" with password "bypass1234"
2. Proceed through setup wizard
3. If stuck at "Couldn't update" — temporarily remove DNS blocks, let update pass, re-block before MDM enrollment step
4. Setup completes, MDM enrollment silently fails

### Step 5 — Analyze & Extend

```bash
# DNS queries for new MDM domains
sudo tshark -r /tmp/phone_setup.pcap -Y "dns.flags.response==0" \
  -T fields -e dns.qry.name | sort -u | grep -iE "miradore|samsungdm|samsunggsl|secb2b|mdm|knox"

# TLS SNI for unblocked MDM traffic  
sudo tshark -r /tmp/phone_setup.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort -u | grep -iE "miradore|samsungdm|samsunggsl|mdm"

# Add any new domains to blocklist, restart hotspot, have phone forget/reconnect
```

## Pre-Enrollment Detection

### Via MTP (after authorizing file access on phone)

```bash
# Check for MDM agent apps
ls /tmp/mtp_phone/Internal\ Storage/Android/data/ | grep -iE "miradore|knox|mdm|managed"

# Read Miradore log
cat /tmp/mtp_phone/Internal\ Storage/Android/data/com.miradore.client.v2/files/miradore.log.0
```

**Log indicators:**
- `Client not yet registered` → Pre-enrollment, DNS block WILL work
- `enrollmentKey=<uuid>` → Enrollment attempted, key is visible
- `DEVICE_ADMIN_ENABLED` → Local admin activated, may survive DNS block  
- `Failed sessions: N` → Our blocks working, counting failures
- `Succesfull sessions: 0` → No server enrollment succeeded

### Via USB Mode Detection

| PID | Mode | What's available |
|-----|------|-----------------|
| 0x685d | Download mode | Odin/heimdall protocol (broken on new Exynos) |
| 0x6860 | MTP | File access via go-mtpfs + CDC ACM serial |
| 0x6862 | RNDIS+DM+ACM | USB Ethernet + CDC ACM serial |
| 0x9008 | EDL (Qualcomm only) | Firehose protocol |

## Common Pitfalls

1. **NetworkManager dnsmasq directory:** Hotspot uses `dnsmasq-shared.d` NOT `dnsmasq.d`. Blocklist in wrong directory → no effect.
2. **IPv6 bypass:** Always block BOTH `0.0.0.0` (IPv4) AND `::` (IPv6). dnsmasq `address=/domain/0.0.0.0` only blocks A records; add separate `address=/domain/::` for AAAA.
3. **Stale DNS on phone:** After updating blocklist, phone must forget/reconnect to flush DNS cache.
4. **Stale `ipv4.dns-options` on NM connection:** `nmcli connection modify Hotspot ipv4.dns-options ""` to clear.
5. **Update check roadblock:** The "checking for updates" step in Samsung setup wizard sometimes blocks progress when DNS is filtered. Temporarily remove ALL blocks, let it pass, then re-block before MDM enrollment step.
6. **Local Device Admin survives:** Some Samsung firmware pre-provisions MDM as system app that activates Device Admin during setup BEFORE any network check. DNS can't prevent local activation. S24 SM-S921B confirmed clean; A54 SM-A546E confirmed local activation regardless.

## OneUI 6.x Service Code Dead Ends

These were tested on SM-A546E and SM-S921B, OneUI 6.1, Android 14 — NONE enable ADB:

| Code | Function | Result |
|------|----------|--------|
| `*#0808#` | USB settings | Only MTP or RNDIS+DM+ACM, no ADB option |
| `*#0011#` Q-sequence | ADB backdoor | **PATCHED** on OneUI 5.1.1+ |
| `*#9900#` | SysDump | Debug Level HIGH + reboot, ADB stays off |
| `*#*#4636#*#*` | Phone info | **BLOCKED** by OneUI 6.x |
| `*#9090#` | Service mode | **BLOCKED** |
