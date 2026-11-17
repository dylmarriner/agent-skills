---
name: samsung-knox-mdm-removal
description: "Samsung Knox Guard / MDM removal methods — Chimera Tool KG Bypass, ADB package removal, combination firmware, factory reset. Covers Knox re-enrollment behavior and Linux workarounds for Windows-only tools."
version: 1.5.0
author: agent
tags: [samsung, knox, mdm, kg, bypass, chimera, frp, unlock, tft, commercial-tools]
---

# Samsung Knox / MDM Removal

## KG / Knox MDM Removal Pipeline (Priority Order)

Samsung Knox Guard (KG) and MDM are different from FRP. Knox may re-enroll after factory reset if the warranty bit is tripped or server-side enrollment is active.

### Path 1: Chimera Tool — Samsung KG Bypass
Chimera Tool (chimeratool.com) added "Samsung KG Bypass" in March 2026 (v46.53.1220). Supports Samsung A546E (Exynos) and many other models.

**Critical limitation:** Chimera is **Windows only** (Win 10/11). Linux workaround: Windows VM with USB passthrough (Virt-Manager/VirtualBox), or Wine.

**Workflow:**
1. Get Chimera license (Basic $99.9/yr, Professional $149.9/yr) + credits
2. Phone in normal boot (PID 6860) — not download mode
3. Connect USB → Chimera detects device
4. Select Samsung KG Bypass procedure → runs via USB
5. If it works: immediately enable Developer Options → USB Debugging
6. Then run ADB Knox disable commands (below) before re-enrollment kicks in

**If user can access Settings temporarily after reset (until it locks again):**
- Chimera removes the active MDM profile during that window
- Then do ADB-level Knox disable before it re-locks

### Path 2: ADB-Level Knox Package Removal (Requires ADB access)
If ADB is available (via combo firmware, Chimera, or Developer Options window):

```bash
# Find Knox/MDM packages
adb shell pm list packages | grep -iE 'mdm|knox|enterprise|safetynet|samsung.android.knox'

# Uninstall key Knox packages (may need root)
adb shell pm uninstall -k com.sec.enterprise.knox
adb shell pm uninstall -k com.samsung.android.knox
adb shell pm uninstall -k com.samsung.android.knox.bbp
adb shell pm uninstall -k com.sec.android.app.safetynet

# Force disable Knox agent
adb shell pm disable-user --user 0 com.samsung.android.knox

# Mark device as provisioned (skip setup wizard)
adb shell settings put global device_provisioned 1
```

**Note:** Knox packages may come back after factory reset if hardware Knox is tripped.

### Path 3: Factory Reset via Settings (If accessible)
Settings → General → Reset → Factory Data Reset clears MDM if you can reach it. MDM is wiped on full factory reset. But Knox may re-enroll on next boot if server-side.

### Path 4: Combination Firmware + ADB Root
Flash combo firmware for the model, get ADB root, clear Knox data:
```bash
adb shell rm -rf /data/system/gatekeeper.*
adb shell rm -rf /data/system_de/0/spgatekeeper.db
adb shell pm list packages | grep -iE 'mdm|knox'
adb shell pm uninstall -k <mdm.package>
adb shell settings put global device_provisioned 1
```

### Path 5: Samsung Official Unlock
If Knox MDM is from an organization:
- Need original Samsung account + org admin to release device
- Samsung support can remove enrollment if you prove ownership

### Path 7: DNS-Blocked WiFi Hotspot (Pre-Enrollment MDM Bypass)

When a phone has MDM pre-installed but NOT yet enrolled (pre-enrollment state), preventing internet access to the MDM server keeps it stranded indefinitely. This works on any Miradore/Knox MDM where enrollment fails permanently without server contact. No ADB, no root, no flashing required.

### PACM Protocol (Samsung AP-Modem Gatekeeper)

The CDC ACM serial (`/dev/ttyACM0`) on Samsung Exynos devices in MTP mode routes AT commands through a **PACM** (Application Processor Control Message) proxy. The AP (Android system) intercepts every AT command before it reaches the modem.

**PACM Error Codes:**

| Error | Meaning | Common Commands |
|-------|---------|----------------|
| `PACM(AP),UNREGISTED` | Feature not registered on AP side | `AT+SWAT=1`, `AT+ADBENABLE=1`, `AT+USBADB=1`, `AT+SSW=2` |
| `PACM(AP),PROTECTED_NO_TOK` | Feature exists but needs auth token | `AT+DEBUGLVC=0,5` |
| `PACM(AP),NOT_ALLOWED_CRO` | Cross-operation restricted | `AT+CGSN`, `AT+CGMR` |

**Key insight:** `UNREGISTED` means the Android-side handler for that AT command is not compiled into the stock ROM. No serial-level trickery can enable a handler that was compiled out.

**SWATD Command** — only privileged Samsung AT command that works on stock firmware, but it only affects the modem processor's internal USB config, NOT the device's overall USB PID:

| Command | Response | Modem Effect |
|---------|----------|-------------|
| `AT+SWATD=0` | `[DR]: CHANGE TO DDEXE` / `[ATD]: CHANGE TO DDEXE` | Download/Debug EXE mode |
| `AT+SWATD=1` | `[DR]: CHANGE TO ATD` / `[ATD]: CHANGE TO ATD` | AT Data mode |
| `AT+SWATD=2` | `[DR]: ATD` + `ERROR` | Already in ATD |
| `AT+SWATD=3-5` | `ERROR` | Not supported |

SWATD takes a single integer. Sub-parameters (`=0,0` etc.) return CHANGE TO DDEXE then ERROR. The USB PID stays at 0x6860 (MTP) because the AP-side USB gadget driver controls the physical USB port — the modem cannot switch the device into a different USB mode. No known AT command enables ADB on OneUI 6.x stock firmware.

See `references/miradore-pre-enrollment-detection.md` for full AT command probe table and PACM error code testing.

### Download Mode (Exynos 1380+) — Limited Use on Linux

2024+ Samsung Exynos devices (A54, S24 Exynos 2400) use a **proprietary bootloader protocol** in download mode. It is NOT the old ODIN protocol supported by heimdall.

**USB descriptors (PID 0x685D):**
```
Interface 0 (CDC Ctrl): class=0x02, subclass=0x02, prot=0x01, int EP 0x82 IN
Interface 1 (CDC Data): class=0x0a, bulk EP 0x01 OUT, 0x81 IN
```

**Tested:** heimdall `print-pit` → `ERROR: Failed to send handshake!`. Bulk probe `b'ODIN\\0'` returned `4c 4f 4b 45` once, never reproducible after USB reset. All other probes timeout. Download mode is write-only for Linux — can flash signed firmware only.

### MDM Domain Discovery via Traffic Capture

When the phone connects to your DNS-blocked hotspot, capture traffic to discover hidden MDM server domains that aren't in any documentation.

```bash
# Capture phone traffic
sudo tcpdump -i wlo1 -nn -s0 -w /tmp/traffic.pcap 'host <phone_ip>'

# Extract TLS SNI — reveals ALL HTTPS hostnames the phone connects to
tshark -r /tmp/traffic.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn

# Extract DNS queries
tshark -r /tmp/traffic.pcap -Y "dns.flags.response == 0" \
  -T fields -e dns.qry.name | sort | uniq -c | sort -rn
```

**Known MDM domains (block ALL of these — IPv4 AND IPv6):**

```
# Samsung Device Management — primary APIs
dir-apis.samsungdm.com         # Samsung Device Management REST API
api.gras.samsungdm.com         # Samsung GRAS API (Global Remote Admin Service)
diagmon-serviceapi.samsungdm.com  # Samsung Diagnostic Monitoring API
*.samsungdm.com                # ALL Samsung DM subdomains (broad wildcard)

# Samsung Global Services
gsl.samsunggsl.com             # Samsung Global Service Logic
eu-gslu.samsunggsl.com         # EU regional GSL instance
*.samsunggsl.com               # ALL GSL subdomains

# Certificate pinning + enterprise infrastructure
pinning-02.secb2b.com          # Samsung certificate pinning service
*.secb2b.com                   # ALL secb2b subdomains

# Google Enterprise / Android MDM
auditrecording-pa.googleapis.com   # Android Enterprise audit recording
gmscompliance-pa.googleapis.com    # Google Play compliance / MDM policy sync

# Azure CDN (Miradore/Microsoft Intune backend on Azure Front Door)
mobile.pipe.aria.microsoft.com           # Azure telemetry & data pipeline
mobile.events.data.microsoft.com         # Azure event ingestion endpoint
online-production-d5cbbrbxc0dqbkcn.z01.azurefd.net  # Miradore's Azure Front Door CNAME
*.azurefd.net                            # ALL Azure Front Door (Miradore & Intune CDN)
```

The `*.samsungdm.com` and `*.samsunggsl.com` domains are critical — Miradore on Samsung devices routes enrollment through Samsung's own DM infrastructure, not directly to miradore.com. Blocking only `gateway.miradore.com` leaves the enrollment path wide open.

Additionally, `api.gras.samsungdm.com` and `diagmon-serviceapi.samsungdm.com` were discovered during **S24 SM-S921B setup traffic analysis** (DNS query capture during enrollment phase, see `references/s24-frp-mdm-notes.md`). These ARE covered by the `*.samsungdm.com` wildcard in dnsmasq (and NextDNS), along with the `*.samsungdm.com` domain-level match. The `mobile.pipe.aria.microsoft.com` and `mobile.events.data.microsoft.com` Azure endpoints were also observed; Miradore uses Azure Front Door CDN so blocking all `*.azurefd.net` catches the CDN path without needing the per-deployment CNAME.

### IPv6 DNS Blocking (Critical!)

dnsmasq's `address=/domain/0.0.0.0` only blocks **IPv4** A records. The phone falls back to **IPv6** AAAA records and reaches the server anyway. You MUST also add IPv6 blocking with `address=/domain/::` for every blocked domain.

Without this, the phone's Miradore/Knox DM will still enroll successfully even when the hotspot is blocking IPv4. Verified on SM-A546E with Miradore v2.18.8: IPv6 completely bypassed the hotspot DNS block.

### Pre-Enrollment Detection via MTP

Check if MDM is pre-enrolled (not yet active) by examining app data via MTP:

```bash
# Mount phone
go-mtpfs /tmp/mtp_mount
ls /tmp/mtp_mount/Android/data/ | grep -iE 'miradore|provision|mdm|knox'
```

**Key indicators of pre-enrollment state:**
- `com.miradore.client.v2` exists in Android/data/ — MDM agent is installed
- `com.android.managedprovisioning` exists — MDM provisioning app present
- Miradore log contains `"Not Work Profile or Fully Managed"` — enrollment incomplete
- Miradore log shows `NETWORK_ERROR` on registration attempts — can't reach server
- Log line: `Admin does not have KNOX_APP_MGMT` — MDM hasn't received Knox privileges yet
- IMEI/MAC masked as zeros in log — device not yet registered

Read the Miradore log for server URL and enrollment key:
```bash
cat /tmp/mtp_mount/Android/data/com.miradore.client.v2/files/miradore.log.0
```

**What the log reveals:**
```log
Miradore Online client v.2.18.8 (build 468)
IMEI: 000000000000000
WiFi MAC: 02:00:00:00:00:00
Model: SM-A546E
Firmware: Android 14
EnrollmentKey: ba7a5bc2-4927-42d9-a988-57b9345f9f71
Server: gateway.miradore.com
Error: Unable to resolve host "gateway.miradore.com": No address associated with hostname
```

#### Hotspot Setup with DNS Blocking

On the Linux PC, create a WiFi hotspot that provides internet access but blocks the MDM server:

```bash
# 1. Create hotspot
nmcli device disconnect wlo1
nmcli device wifi hotspot ifname wlo1 ssid "MDM-Bypass" password "bypass1234"

# 2. Write dnsmasq config to block MDM server
echo "address=/gateway.miradore.com/0.0.0.0
address=/miradore.com/0.0.0.0
address=/mdm.miradore.com/0.0.0.0\naddress=/api.miradore.com/0.0.0.0\naddress=/samsungdm.com/0.0.0.0\naddress=/samsungdm.com/::\naddress=/dir-apis.samsungdm.com/0.0.0.0\naddress=/dir-apis.samsungdm.com/::\naddress=/gsl.samsunggsl.com/0.0.0.0\naddress=/gsl.samsunggsl.com/::\naddress=/eu-gslu.samsunggsl.com/0.0.0.0\naddress=/eu-gslu.samsunggsl.com/::\naddress=/pinning-02.secb2b.com/0.0.0.0\naddress=/pinning-02.secb2b.com/::" | sudo tee /etc/NetworkManager/dnsmasq-shared.d/block-miradore.conf

# 3. Restart NM to pick up dnsmasq config
sudo systemctl restart NetworkManager
nmcli connection up Hotspot

# 4. Verify
nslookup gateway.miradore.com 10.42.0.1  # → 0.0.0.0 (blocked)
nslookup google.com 10.42.0.1            # → real IP (still works)
```

Then on the phone:
1. Connect to the hotspot (password shown by `nmcli dev wifi show-password`)
2. Setup wizard proceeds past the WiFi screen
3. MDM enrollment attempt hits 0.0.0.0 and fails silently
4. Phone boots to home screen with MDM never activated

**CRITICAL: Update check blocks setup.** The Android setup wizard's "Checking for updates" step requires internet access to Google/Samsung servers. If ALL MDM domains are blocked (including Samsung DM), the update check may fail with "Couldn't update, check your network" — blocking the entire setup wizard. Solution: use a TWO-PHASE approach:
1. Phase 1: Remove all DNS blocks. Phone completes update check.
2. Phase 2: RE-APPLY DNS blocks before setup reaches the MDM enrollment step (the update check happens before MDM enrollment).
The window between update completion and MDM enrollment is typically 5-30 seconds depending on network speed. Start a fresh tcpdump and watch for MDM domain TLS SNI — that's your cue to re-block.

```bash
# Watch for MDM enrollment TLS SNI in real-time:
sudo tcpdump -i wlo1 -nn 'host <phone_ip> and tcp port 443' | \
  while read line; do
    if echo "$line" | grep -qE 'miradore|samsungdm|samsunggsl'; then
      echo "PANEL BEAT — MDM enrollment detected, re-blocking..."
      sudo cp /etc/NetworkManager/dnsmasq-shared.d/block-miradore.conf \
        /etc/NetworkManager/dnsmasq-shared.d/block-mdm-enabled.conf
      # (pre-create and cp the config back in, or write it inline)
    fi
  done
```

**Cellular bypass risk:** The phone may use LTE/5G for its network connection instead of the hotspot. The hotspot DNS blocks are only effective while the phone has NO SIM card installed or is in airplane mode. With mobile data active, Miradore/Knox DM will phone home through the cellular data connection regardless of hotspot DNS settings. If a SIM is inserted, remove it or put the phone in airplane mode before connecting to the hotspot. The setup wizard may still require a network connection — the hotspot provides that, and the phone's cellular data stays off.
5. Miradore app shows `"Not Work Profile or Fully Managed"` permanently

**Portability:** Same technique works at the router level — but you MUST block both IPv4 and IPv6 DNS entries. Most router DNS configs only handle A records, so you may also need to disable IPv6 on the phone or use a DNS firewall instead.

### Path 8: NextDNS — Permanent Portable MDM Block (No Laptop Needed)

Android's `Settings → Connections → Private DNS` (DNS-over-TLS/DoT) works with NextDNS to permanently block MDM servers on both WiFi AND mobile data — no laptop, no hotspot, no router config. Survives network changes, SIM swaps, and reboots.

**Why NextDNS specifically:** Unlike `dns.adguard-dns.com` (which blocks ALL internet via over-aggressive filtering — "Connected, no internet" on the phone), NextDNS lets you block ONLY the domains you specify via denylist. Google, Play Store, Samsung updates all work normally. Only Miradore/Knox DM servers are killed.

**Setup (5 minutes):**
1. Open `my.nextdns.io` in any browser, sign up (free tier: 300k queries/month from a single profile)
2. Go to **Security tab** → disable every built-in blocklist (ads, trackers, threat feeds, parental controls — uncheck ALL toggle switches)
3. Go to **Denylist tab** → paste these domains (one per line):
   ```
   *.miradore.com
   *.samsungdm.com
   *.samsunggsl.com
   ```
4. Your profile has an ID (e.g., `bedc7a`). The DNS-over-TLS endpoint is `bedc7a.dns.nextdns.io`
5. On the phone: **Settings → Connections → More connection settings → Private DNS** → `bedc7a.dns.nextdns.io`

**Verification:** Open Chrome on the phone → `google.com` loads normally. In browser, try `gateway.miradore.com` → "Site can't be reached" (DNS blocked). Same result on WiFi and on mobile data.

**Caveat:** NextDNS's TLS handshake requires a working internet connection. If the phone is on a network where DNS is already blocked, set Private DNS to **Off** temporarily, connect to a working network, then toggle it back on. The handshake establishes once and persists across network changes.

**Explicit subdomains:** dnsmasq's `*.samsungdm.com` wildcard blocks all subdomains including `api.gras.samsungdm.com` and `diagmon-serviceapi.samsungdm.com`. NextDNS supports the same wildcard syntax. No need to list subdomains individually — the wildcard catches them all.

**WiFi card naming:** Intel WiFi interfaces typically appear as `wlo1` (iwlwifi). If different, replace `wlo1` with the appropriate interface from `ip link show | grep wl`.

**CRITICAL dnsmasq-shared.d caveat:** NM's hotspot mode runs its OWN dnsmasq instance that reads from `/etc/NetworkManager/dnsmasq-shared.d/` — NOT `/etc/NetworkManager/dnsmasq.d/` (which is for the system-wide dnsmasq service). Writing the block config to `dnsmasq.d/` silently does nothing. Always use `dnsmasq-shared.d/` for hotspot DNS rules. After writing, restart NM with `sudo systemctl restart NetworkManager` then bring up the hotspot.

**CRITICAL: NM connection DNS options persist separately.** `nmcli connection modify Hotspot ipv4.dns-options "address=/domain/0.0.0.0"` stores the DNS override IN the connection profile. This persists even after deleting the dnsmasq config file — the phone still gets 0.0.0.0 for blocked domains. To fully clear DNS blocks, you MUST do BOTH:
1. `sudo rm /etc/NetworkManager/dnsmasq-shared.d/block-*.conf`
2. `nmcli connection modify Hotspot ipv4.dns-options ""`
3. `sudo systemctl restart NetworkManager`

Forgetting step 2 leaves the DNS block active indefinitely via the NM connection profile. Check with `nmcli connection show Hotspot | grep dns-options`.

**Hostapd vs NM:** You do NOT need to manually configure hostapd when using `nmcli dev wifi hotspot`. NM handles hostapd config automatically. Skip hostapd.conf entirely.

**Full phone-side flow after hotspot is live:**
1. User connects to hotspot from phone's WiFi settings
2. Setup wizard proceeds past WiFi screen normally
3. MDM enrollment attempt hits 0.0.0.0, fails silently
4. Phone boots to home screen — Miradore stays in pre-enrollment
5. BUT: if phone previously connected to another network (cellular data), DNS may be cached. Put phone in airplane mode before connecting to hotspot, then turn WiFi on.

**Traffic monitoring with the phone on your hotspot:**\nSee the **MDM Domain Discovery via Traffic Capture** section above for TLS SNI extraction and DNS analysis techniques. Use tshark to extract TLS SNI values — this reveals hidden MDM server domains (especially Samsung DM infrastructure) that aren't visible from DNS alone.

#### Developer Options MDM-Locked

On pre-enrollment devices, Developer Options may be blocked by DevicePolicyManager even though the MDM hasn't fully enrolled. The restriction comes via ManagedProvisioning app policies applied before full enrollment completes.

**Verified on:** Samsung A54 SM-A546E with Miradore pre-enrollment — `Settings > Developer options` shows "not available" with MDM block. There is NO USB-level or AT-command bypass for this on OneUI 6.x. The DNS hotspot or router-level block is the only path.

See `references/miradore-pre-enrollment-detection.md` for the full session transcript including AT command probing results and USB descriptor analysis.

### Service Codes on OneUI 6.x

Samsung dialer codes (`*#<code>#`) access firmware-level menus that may bypass MDM restrictions on some ranges. Tested on SM-A546E (Android 14, OneUI 6.1) with Miradore pre-enrollment:

| Code | Function | Result | Notes |
|------|----------|--------|-------|
| `*#0808#` | USB Settings | ✓ Opens | Options limited to MTP or RNDIS+DM+ACM. No ADB toggle. |
| `*#*#4636#*#*` | Testing/Phone Info | ✗ Blocked | Android framework testing menu — blocked by OneUI 6.x. Does nothing. |
| `*#0011#` | Service Mode | ✓ Opens | Q-sequence patched — see below |
| `*#2263#` | Band Selection | ✓ Opens | ServiceMode main menu. No ADB options found. |
| `*#9900#` | SysDump | ✓ Opens | Has Run dumpstate/logcat, Debug Level, Upload Mode |

`*#0808#` USB settings only shows **MTP** (PID 0x6860) or **RNDIS+DM+ACM** (PID 0x6862). No "MTP+ADB" option — the ADB toggle has been removed from service menu on newer Samsung firmware. ADB is now exclusively controlled by Developer Options' "USB Debugging" toggle, which is blocked by MDM DevicePolicyManager.

**RNDIS+DM+ACM mode (0x6862):** 5 USB interfaces — RNDIS networking, CDC ACM serial, and vendor debug. RNDIS gives the PC an address in 192.168.69.0/24 or 192.168.30.0/24 (subnet varies per connection — observed both 69.x and 30.x on different sessions). The phone (typically the gateway IP of the subnet) responds to ping but has **no listening ports** — `adb connect` returns "Connection refused." RNDIS enables outbound network from the phone through the PC but no inbound services. The ACM serial (`/dev/ttyACM0`) is present in this mode but owned root:dialout (mode 660) — AT command behavior is identical to MTP mode (same PACM proxy). Find phone IP: `sudo cat /var/lib/NetworkManager/dnsmasq-wlo1.leases` or scan the subnet with `nmap -sn`. Phone DHCP hostname appears in leases (e.g., `Galaxy-A54-5G`, `Galaxy-S24`).

**`*#0011#` Q-sequence (CONFIRMED PATCHED on OneUI 6.1 / Android 14):**
The known ADB-enable sequence `*#0011#` → Menu → Back → Back → Menu → Key Input → **Q** → OK does NOT work on A54 SM-A546E firmware. After entering Q and OK, `adb devices` shows nothing regardless of USB mode. This patch applies to OneUI 5.1.1+ devices. If it works on a device, document exact firmware version.

**`*#9900#` Debug Level HIGH:**
This menu lets you set Debug Level to HIGH / MEDIUM / LOW. Setting to HIGH:
1. **Reboots the phone immediately** — requires full power cycle
2. Persists across reboot (confirmed survives boot cycle)
3. Does NOT enable ADB by itself — `adb devices` still shows nothing after reboot with Debug Level HIGH
4. Does NOT unblock Developer Options (MDM DevicePolicyManager restrictions remain)
5. May enable additional AT commands (not verified — PACM proxy still blocks on stock firmware)

The Q-sequence also fails AFTER Debug Level HIGH has been set and the phone rebooted. Debug Level HIGH enables deeper kernel logging (logcat, ramdumps) but does not affect ADB/Developer Options gatekeeping at the Android framework level.

### Path 6: TFT Unlock Tool (Multi-Brand Free Commercial Tool)
TFT Unlock is a **free** Windows-only tool covering Samsung, Xiaomi, Oppo, Vivo, Realme FRP/MDM/unlock/EDL. Unlike Chimera (paid subscription), TFT is distributed through ad-wall download farms — no purchase needed.

**Where to get it:**
- Official site: tfttool.com (v7 / v6.2.1.1 available)
- Download servers: filexspace.com, earnarab.com (redirect chains through playstretch.host, structurebee.icu)
- **Not direct download** — requires real browser interaction (ad walls, popunders, countdown timers)
- Archive is password-protected: password `123`
- Size: ~302-310 MB
- See `references/tft-unlock-tool.md` for full acquisition and analysis details

**What it covers (v6.2.1.1):**
- Samsung: A12, A21s, A31, A51, A71, J2/J5/J7/J8, M11/M21/M31/M51
- Xiaomi: Redmi Note 7/8/9/10, Redmi 6A-10A
- Oppo/Vivo: A5/A9/F11/F15/Reno, Y12/Y15/Y17/Y20/V20
- Realme: C3/C11/C15/C25, 6/7/8 Pro

**Linux workflow:** Same as Chimera — Windows VM with USB passthrough (see references/chimera-tool-knox.md for setup).

---

## Common Pitfalls

0. **Tailscale VPN hijacks hotspot DNS.** When Tailscale (or any local VPN) is active on the hotspot host, DNS queries from hotspot clients route through Tailscale's DNS instead of the hotspot's dnsmasq. This silently bypasses ALL dnsmasq-based DNS blocks — MDM domains resolve to their real IPs because Tailscale's DNS resolver has no blocklist. Symptoms: dnsmasq configs verify correctly from the host (`nslookup gateway.miradore.com 10.42.0.1` returns 0.0.0.0), but the phone successfully reaches the MDM server. The phone's traffic pcap shows MDM TLS handshakes completing. Fix: Stop Tailscale with `sudo tailscale down` while the hotspot is active for MDM-blocking sessions. The VPN must be fully disconnected — simply disabling exit node routing is insufficient because Tailscale intercepts DNS at the system level regardless of routing config. Verify: `resolvectl status | grep wlo1` should show the hotspot dnsmasq (10.42.0.1) as the DNS server, not Tailscale's MagicDNS (100.x.x.x).

1. **Date/time mismatch kills ALL TLS — not just MDM.** When the phone's date/time is manually changed (e.g., to try to break MDM certificate pinning), EVERY HTTPS connection fails because TLS certificate validation rejects expired/future certificates. Symptoms: "Connected, no internet" in the status bar, Chrome won't load any page. The hotspot is working perfectly — DNS resolves, NAT masquerades, packets flow — but the phone rejects all TLS (and QUIC) connections due to clock skew. Fix: `Settings → General Management → Date and Time → Automatic date and time → ON`. This was the root cause in one session where the hotspot appeared broken for 30+ minutes despite iptables, dnsmasq, and NAT all being verified functional. Do NOT set a wrong date/time to break MDM unless you can accept zero internet access on the phone.

2. **UFW silently breaks hotspot NAT.** When `ufw` is active (common on Ubuntu/Kubuntu), its default FORWARD policy DROPs packets from the hotspot subnet even though NetworkManager's NAT masquerade rule is correct. The hotspot appears functional (DHCP works, DNS resolves, 24K+ packets masqueraded) but the phone gets "Connected, no internet." This is especially insidious after a laptop crash or NetworkManager restart because ufw gets reactivated. Fix: `sudo ufw disable`. Verify with `sudo iptables -L FORWARD -n -v | head -5` — the FORWARD chain should show `policy ACCEPT`.

3. **Knox re-enrollment is server-side** — Even if you remove all Knox packages, the device may re-enroll on next boot if Samsung's servers have it registered. The only permanent fix is either Samsung official unlock or hardware Knox bypass (if available).
2. **Chimera KG Bypass is Windows-only** — Need a Windows VM with USB passthrough on Linux. See `references/chimera-tool-knox.md` for details.
3. **AT+SWATD=1 fails on OneUI 6.x** — PACM protected, no USB-level ADB enable. Need Developer Options from phone screen. The `AT+SWATD` command however DOES work at the modem level — the modem acknowledges it even if the AP blocks the USB switch. Known parameter mapping: `0` = CHANGE TO DDEXE (Download/Debug mode, both DR and ATD channels), `1` = CHANGE TO ATD (AT Data mode), `2` = ATD (already in ATD, no change), `3-5` = ERROR. The DDEXE mode switch only affects the modem's internal USB configuration — it does NOT change the device's overall USB PID (stays at 0x6860 MTP) because the AP-side USB gadget driver controls the actual USB port.
4. **Heimdall 1.4.2 is too old for 2024+ devices** — The ODIN protocol changed on Exynos 1380+ era devices. Heimdall's 0x42/0x64 control transfer handshake fails with pipe errors. The bootloader enumerates CDC ACM (interface 0, interrupt EP 0x82 IN) + CDC Data (interface 1, bulk EP 0x01 OUT, 0x81 IN) but speaks a proprietary protocol not publicly documented. Bulk-endpoint probing with `b'ODIN\\x00'` has inconsistently returned a 4-byte response `4c 4f 4b 45` ("LOKE") — possibly a bootloader status code, but cannot be reproduced reliably after USB reset. Other probes (`b'\\x00'*64`, `struct-packed commands`, `SAMSUNG`, vendor control transfers) all time out. No reliable protocol has been established via open-source tools. Try jodin3 or odin4 (Samsung's official ODIN for Windows) instead. The download mode on 2024+ Exynos is essentially a black box for Linux tools.
5. **Download mode is WRITE-ONLY** — Cannot read partitions, only flash signed firmware. Even heimdall's PIT read (`heimdall print-pit`) fails on 2024+ devices — protocol init fails before any data transfer.
6. **Hardware Knox warranty bit** — If tripped, Knox MDM may persist through factory resets.
7. **Samsung docs blocked by 403/404** — Standard browser/curl access to Samsung developer docs often fails. Use `markitdown` MCP tool with full doc URLs (e.g., `https://docs.samsungknox.com/admin/knox-guard/`) to convert pages to readable markdown. Direct curl with `grep` filtering also works for extracting key text snippets.
8. **GSM tool downloads are behind ad walls** — Tools like TFT Unlock, SamFw, and most free GSM unlockers are distributed through filexspace.com / earnarab.com redirect farms. The actual file is behind popunders, countdown timers, and referral tracking. A real browser session is required — curl/wget hits a landing page, not the file. Archive is always password-protected (commonly `123`).
9. **Password-protected archives are the norm** — Every GSM tool download (.zip/.rar) has a password (usually `123`). Always ask the source page before attempting extraction. If the page doesn't show it explicitly, check the page source or page title. Also: some archivers (7z) need the exact extension — if it downloads as a file without an extension, add `.zip` or `.rar` manually.

---

## Chimera Tool Details

See `references/chimera-tool-knox.md` for:
- Pricing tiers and credit costs
- Samsung KG Bypass changelog details
- Linux workarounds (VM USB passthrough)
- Supported models list

## Knox Guard Server Architecture

See `references/knox-guard-architecture.md` for:
- Server-client model (Knox Guard servers ↔ Knox Agent ↔ TEE)
- Device status lifecycle (Upload → Pending → Accept → Manage → Lock/Unlock)
- Offline lock mechanism and PIN unlock
- Hardened Security mode (Galaxy S26+)
- REST API endpoints
- Official documentation URLs

## Research Reports

See `/home/lin/knox-kg-bypass-research.md` for comprehensive research on OneUI 6.x Knox KG bypass methods covering:
- Commercial tool methods (Chimera Tool workflow)
- Client-side bypass (ADB, combo firmware, developer options)
- Server-side bypass (official unlock, REST API)
- Warranty bit and enrollment vulnerabilities
- OneUI 6.x specific challenges

## TFT Unlock Tool

See `references/tft-unlock-tool.md` for:
- Tool overview and features
- Download site deobfuscation (filexspace, earnarab redirect chains)
- RE analysis approach (Ghidra, ILSpy, Detect It Easy)
- What to look for when reversing (license check, USB protocols, unlock methods)