# Samsung One UI 6.x — Bypass Catalog

Session: 2026-07-13 | Devices: SM-A546E, SM-S921B, Moto g34 5G, Vivo fastboot

---

## Samsung Service Code Reference (One UI 6.x)

| Code | Menu | Status | Notes |
|------|------|--------|-------|
| `*#0808#` | USB Settings | WORKS | Only MTP or RNDIS+DM+ACM on OneUI 6.x — no standalone ADB option. PID 0x6862=RNDIS+ACM, 0x6860=MTP |
| `*#9900#` | SysDump | WORKS | Debug Level HIGH requires reboot. "Run dumpstate/logcat" available |
| `*#0011#` then Menu→Back→Back→Menu→Q | ADB backdoor | PATCHED | Dead on OneUI 6.x. Samsung removed the Q key input backdoor |
| `*#*#4636#*#*` | Phone Info | BLOCKED | No response on A54/S24 OneUI 6.x |
| `*#0*#` | Hardware Test | WORKS | LCD/ sensor/ touch test menu |

## MDM DNS Blocking — Full Domain List

Discovered via tcpdump+tsshark during S24 setup (firmware S921BXXSFDZE1):

**Miradore (Azure Front Door):**
- `gateway.miradore.com`
- `*.miradore.com`

**Samsung Device Management:**
- `dir-apis.samsungdm.com`
- `api.gras.samsungdm.com` ← caught in S24 traffic, critical
- `diagmon-serviceapi.samsungdm.com`
- `*.samsungdm.com`

**Samsung Global Service Logic:**
- `gsl.samsunggsl.com`
- `eu-gslu.samsunggsl.com`
- `*.samsunggsl.com`

**Azure CDN (Miradore backend):**
- `mobile.pipe.aria.microsoft.com`
- `mobile.events.data.microsoft.com`

**Certificate Pinning:**
- `pinning-02.secb2b.com`
- `*.secb2b.com`

### dnsmasq Block Config

```bash
# /etc/NetworkManager/dnsmasq-shared.d/block-mdm.conf
# CRITICAL: include :: for IPv6 — phones fallback to v6 otherwise
address=/gateway.miradore.com/0.0.0.0
address=/gateway.miradore.com/::
address=/miradore.com/0.0.0.0
address=/miradore.com/::
address=/samsungdm.com/0.0.0.0
address=/samsungdm.com/::
address=/samsunggsl.com/0.0.0.0
address=/samsunggsl.com/::
address=/mobile.pipe.aria.microsoft.com/0.0.0.0
address=/mobile.pipe.aria.microsoft.com/::
address=/secb2b.com/0.0.0.0
address=/secb2b.com/::
```

**Clean stale configs** — NM reads from both dirs:
```bash
sudo rm /etc/NetworkManager/dnsmasq.d/block-*.conf
sudo rm /etc/NetworkManager/dnsmasq-shared.d/block-*.conf
nmcli connection modify Hotspot ipv4.dns-options ""
nmcli connection modify Hotspot ipv6.dns-options ""
```

## Permanent Mobile-Safe Block: NextDNS

Works on ANY network — WiFi, mobile data, roaming. TLS-encrypted.

1. `my.nextdns.io` → sign up → Denylist tab → paste domain list above
2. Disable ALL default blocklists (ads/trackers break normal internet)
3. On phone: Settings → Private DNS → `XXXX.dns.nextdns.io`

## UFW Hotspot Killer

Laptop crash/NM restart re-enables ufw. FORWARD policy DROP silently kills hotspot NAT.

**Diagnosis:** `sudo ufw status` shows active, `sudo iptables -L FORWARD -n` shows policy DROP
**Fix:** `sudo ufw disable`

## Date/Time TLS Sabotage

Setting wrong date to break MDM certs ALSO breaks: Google connectivity check, NextDNS/Private DNS, all HTTPS, Play Store. The "no internet" on hotspot was wrong date, not broken hotspot.

---

## Motorola moto g34 5G (fogos) — Fastboot

```
Product: fogos | Bootloader: MBM-3.0-uefi | oem_locked
PID: normal=22b8:2e82, fastboot=22b8:2e80
Firmware: U1UGS34.23-82-2-7-cf0e9a
```

Standard `getvar` works. OEM commands limited with locked bootloader.

## Vivo Fastboot

```
PID: 18d1:d00d (Google fastboot — same as Xiaomi)
getvar: BLOCKED | reboot: TIMEOUT
```

Vivo locked bootloaders aggressively block fastboot. Minimal commands: `devices`, `reboot-bootloader`. Physical key combo needed to exit: Power+VolUp+VolDown ~15s.

---

## Traffic Capture Minimum

```bash
# Find phone IP
sudo cat /var/lib/NetworkManager/dnsmasq-wlo1.leases
# Capture
sudo tcpdump -i wlo1 -nn -s0 -w /tmp/phone.pcap 'host 10.42.0.X'
# Analyze
tshark -r /tmp/phone.pcap -Y "tls.handshake.extensions_server_name" -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn
tshark -r /tmp/phone.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name | sort | uniq -c | sort -rn
```

## Iterative MDM Block Strategy

1. Full clean pass — remove ALL blocks, let setup proceed
2. Let update check pass (Samsung/Google CDN accessible)
3. Capture FIRST MDM enrollment attempt (TLS SNI)
4. Block ONLY discovered MDM domains
5. Reconnect phone to flush DNS cache
6. If still enrolling, repeat capture — always more domains
7. Never block `samsung.com` or `googleapis.com` wholesale
