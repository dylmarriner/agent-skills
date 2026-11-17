---
name: samsung-mdm-bypass
description: Bypass Miradore/Samsung MDM enrollment by DNS-blocking MDM servers during Android setup. Covers complete domain list (conservative), hotspot creation, traffic analysis, NextDNS permanent fix, MTP backup/restore workflow, service code tricks, and known pitfalls for Samsung One UI 6.x devices.
version: 1.1.0
---

# Samsung MDM Bypass

Bypass Miradore / Samsung Knox MDM enrollment on devices that auto-enroll during setup. The core approach: intercept DNS to block MDM server communication during Android setup, preventing enrollment while allowing everything else through.

## Trigger Conditions

- User has a Samsung device that auto-enrolls in MDM during setup
- Miradore, Knox Manage, or Samsung DM is pre-installed
- Device shows "Checking for updates" or MDM enrollment screen during setup
- User wants to use the device without MDM restrictions
- Goal: prevent MDM enrollment, NOT just FRP bypass

## Quick Start

1. Create DNS-blocked hotspot on Linux
2. Phone connects during setup, MDM servers resolve to 0.0.0.0
3. Setup completes without MDM enrollment
4. Optional: NextDNS for permanent mobile-data-safe blocking

## Flow A — DNS-Blocked Hotspot (PREFERRED)

### Step 1: Check for Leftover FRP Configs

If the hotspot was previously used for FRP bypass, it may have redirects for Google domains that will break Play Store:

```bash
ls /etc/NetworkManager/dnsmasq-shared.d/
sudo rm -f /etc/NetworkManager/dnsmasq-shared.d/frp*
```

**CRITICAL:** dnsmasq's `--conf-dir` reads **every file** in the directory regardless of extension — renaming to `.disabled` does NOT stop it. Always remove/delete, never rename.

### Step 2: Create Hotspot

```bash
nmcli device disconnect wlo1
nmcli device wifi hotspot ifname wlo1 ssid "MDM-Bypass" password "bypass1234"
```

Default password that NetworkManager generates is usually something simple — check with `nmcli connection show Hotspot -s | grep psk`.

### Step 3: Start Traffic Capture (Optional — to discover new MDM domains)

```bash
sudo tcpdump -i wlo1 -nn -s0 -w /tmp/phone_setup.pcap 'host <phone-ip>'
```

### Step 4: Analyze MDM Domains

During setup, extract TLS SNI to discover the exact domains the MDM agent hits:
```bash
sudo tshark -r /tmp/phone_setup.pcap \
  -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name \
  | sort | uniq -c | sort -rn
```

### Step 5: Block MDM Domains Only (Conservative)

Do NOT block FOTA (firmware update), Google, Samsung cloud, or Microsoft telemetry domains — those break Play Store, system updates, and other normal phone functions. Only block the specific MDM enrollment endpoints.

```bash
sudo tee /etc/NetworkManager/dnsmasq-shared.d/block-mdm.conf << 'EOF'
# Only Miradore + Samsung MDM enrollment — NOT FOTA, Google, or telemetry
address=/miradore.com/0.0.0.0
address=/miradore.com/::
address=/gateway.miradore.com/0.0.0.0
address=/gateway.miradore.com/::
address=/api.miradore.com/0.0.0.0
address=/api.miradore.com/::
address=/samsungdm.com/0.0.0.0
address=/samsungdm.com/::
address=/api.gras.samsungdm.com/0.0.0.0
address=/api.gras.samsungdm.com/::
address=/diagmon-serviceapi.samsungdm.com/0.0.0.0
address=/diagmon-serviceapi.samsungdm.com/::
EOF
```

Then restart the hotspot DNS:

```bash
# dnsmasq kill + NM restart clears any cached rules
nmcli connection down Hotspot
sleep 1
nmcli connection up Hotspot
```

Verify:
```bash
dig miradore.com @10.42.0.1 +short
# Expected: 0.0.0.0
dig google.com @10.42.0.1 +short
# Expected: some real IP (142.250.x.x), NOT 10.42.0.1
dig accounts.google.com @10.42.0.1 +short
# Expected: real Google IP, NOT 10.42.0.1
```

### Step 6: Phone Reconnect

Phone must forget and reconnect to flush DNS cache. During setup, MDM enrollment fails silently, setup proceeds normally.

## Flow B — NextDNS (Permanent, Portable)

No laptop needed. Works on WiFi + mobile data, anywhere.

1. Sign up at my.nextdns.io
2. **Denylist tab** — add ONLY MDM enrollment domains (NOT FOTA, Samsung cloud, or MS telemetry):
   ```
   *.miradore.com
   *.samsungdm.com
   api.gras.samsungdm.com
   diagmon-serviceapi.samsungdm.com
   gateway.miradore.com
   ```
   Do NOT add `*.samsunggsl.com`, `mobile.events.data.microsoft.com`, or FOTA domains — those break Play Store and system updates.
3. **Disable all default blocklists** (Security tab)
4. Copy DNS-over-TLS address (e.g. `abc123.dns.nextdns.io`)
5. On phone: Settings → Private DNS → paste address

## Flow C — Service Code Tricks (One UI 6.x)

### `*#0808#` — USB Settings

Only two options on One UI 6.x on A54/S24:
- **MTP** (0x6860) — file transfer + modem serial
- **RNDIS + DM + ACM** (0x6862) — RNDIS networking + CDC serial + dev mode

No standalone "ADB" option on newer firmware. ADB is controlled by Developer Options toggle only.

### `*#0011#` — Service Mode

Q ADB backdoor sequence: Menu → Back → Back → Menu → Key Input → Q → OK
**STATUS:** Dead on One UI 6.x (Android 14). Samsung patched it.

### `*#9900#` — SysDump Menu

Set Debug Level to HIGH — triggers reboot. Enables detailed logging but does NOT directly enable ADB on latest firmware.

### `*#*#4636#*#*` — Phone Info

Testing/Phone Info menu. Blocked on One UI 6.x by Samsung's Phone app.

## Flow D — MTP Backup Before Reset

Backup the phone before factory resetting. MTP is the only reliable method since ADB is typically blocked by MDM.

### Prerequisites

- Phone screen unlocked (MTP access requires unlocked screen on One UI 6.x)
- USB cable connected
- `jmtpfs` installed: `sudo apt install -y mtp-tools jmtpfs`

### Verify Detection

```bash
lsusb | grep Samsung
# Should show "04e8:6860" (MTP mode)
# If not, phone may be in different USB mode or screen locked
```

### Mount

```bash
mkdir -p /tmp/phone-mount
jmtpfs /tmp/phone-mount   # runs as FUSE daemon
# Check it worked:
ls /tmp/phone-mount/Internal\ storage/
```

If you get "Input/output error" or empty directory: phone screen is locked. Unlock and retry.

### Backup Important Folders

```bash
mkdir -p ~/phone-backup
for dir in DCIM Pictures Documents Download Music Movies Recordings; do
  cp -r "/tmp/phone-mount/Internal storage/$dir" ~/phone-backup/
done
```

Skip `Android/` and `data/` directories — they're app caches that will be regenerated, and MTP is slow/lossy with small files.

### Verify Size

```bash
du -sh ~/phone-backup/
```

### Unmount

```bash
fusermount -u /tmp/phone-mount
rmdir /tmp/phone-mount
```

### Restore (After Reset)

Same process but reverse:

```bash
mkdir -p /tmp/phone-restore
jmtpfs /tmp/phone-restore
for dir in DCIM Pictures Documents Download Music Movies Recordings; do
  cp -r ~/phone-backup/"$dir" "/tmp/phone-restore/Internal storage/"
done
fusermount -u /tmp/phone-restore
rmdir /tmp/phone-restore
```

### MTP Troubleshooting

- **"Transport endpoint is not connected"** — stale FUSE mount from a previous attempt. Run `sudo umount -l /tmp/a54* 2>/dev/null; sudo rm -rf /tmp/a54*`, recreate directories fresh.
- **"Input/output error" on mount point** — phone screen probably locked. Unlock and retry.
- **Empty directory after mount** — same cause. Screen must be unlocked on One UI 6.x.
- **`du -sh` shows 0 bytes** — FUSE MTP doesn't report sizes via stat(). Actual files are accessible via `find` and `cp`. Use `cp -r` then `du -sh` on the local copy.
- **`rsync` times out** — MTP FUSE is slow for recursive operations. Prefer `cp -r` per-folder instead.
- **`cp` reports "failed to close" on .thumbnails** — these are Samsung MTP bugs with hidden thumbnail cache files. The actual user data (photos, videos, documents) transfers correctly. Ignore these errors.
- **Phone not detected (no 04e8:6860)** — unplug and replug USB; on the phone, tap the USB notification and ensure "File transfer / Android Auto" or "MTP" is selected.

## Key Pitfalls

1. **DNS blocking prevents SERVER enrollment, not LOCAL admin** — If Miradore already has `DEVICE_ADMIN_ENABLED`, blocking the server stops policy updates and registration, but local restrictions (Developer Options locked, APK sideload disabled) remain active. Prevention is better than cure — block DNS BEFORE the phone first connects.

2. **UFW silently kills hotspot internet** — ufw DROPs forwarded packets by default. Symptoms: phone connects to hotspot but has no internet. Fix: `sudo ufw disable`.

3. **Wrong date/time breaks ALL TLS** — Setting device date/time wrong to break MDM cert validation kills ALL HTTPS. Phone loses all internet. Revert to automatic date/time.

4. **Phone uses cellular data if WiFi drops** — When hotspot restarts, phone may switch to mobile data and bypass DNS blocks. Disable mobile data during setup or use airplane mode + WiFi.

5. **Samsung DM domains keep changing** — Always run traffic capture during setup to discover new domains. They vary by carrier, region, and MDM provider. The list above covers Miradore on NZ Samsung devices but may need extension.

6. **RNDIS + ADB over TCP still blocked** — Even when phone is in RNDIS+DM+ACM mode and Debug Level HIGH, ADB daemon won't start if MDM has `adb_enabled=0` in settings database.

7. **AT+SWATD changes modem mode, not USB gadget** — Modem responds with `CHANGE TO DDEXE` but Android AP controls the actual USB PID. PACM(AP) proxy blocks the AP-side mode switch. Don't waste time trying to enable ADB via AT commands on One UI 6.x.

8. **NextDNS needs internet for TLS handshake** — Phone must have working internet before setting Private DNS. If on a hotspot with broken DNS, the TLS connection to NextDNS's resolver fails.

9. **dnsmasq `--conf-dir` reads ALL files regardless of extension** — NetworkManager's dnsmasq is started with `--conf-dir=/etc/NetworkManager/dnsmasq-shared.d`. This flag reads every file in that directory, not just `*.conf` files. A file renamed to `.disabled` is STILL loaded. To remove a config, delete the file entirely or move it outside the directory. Kill the dnsmasq process and restart the hotspot to clear cached rules. Symptom: DNS queries still return the old redirected IP after you thought you disabled a rule.

10. **FRP redirects break Play Store and Google services** — If the hotspot was previously used for FRP bypass with rules redirecting Google domains (`accounts.google.com`, `android.clients.google.com`) to the hotspot gateway, these break Google authentication. For MDM bypass (not FRP), these redirects must NOT be present — only MDM domains should be blocked. If Play Store doesn't work on the hotspot, check for leftover FRP rules in dnsmasq config files. Always run `sudo rm -f /etc/NetworkManager/dnsmasq-shared.d/frp*` before applying MDM blocks.

11. **MTP requires phone screen unlocked** — On One UI 6.x, MTP access via USB is blocked when the screen is locked. The phone shows up in `lsusb` as 04e8:6860 but `jmtpfs` returns "I/O error" or empty directory listings. Unlock the phone before attempting backup. Screen timeout auto-locks after ~30s — keep the phone awake during transfer.

12. **Conservative blocklist — don't block FOTA** — Samsung firmware update servers (`fota.samsungdm.com`, `gralt.samsungdm.com`, etc.) are NOT MDM enrollment domains. Blocking them prevents system updates and may cause the phone to show "cannot verify network" errors during setup. Only block `samsungdm.com` root and the specific `api.gras` / `diagmon-serviceapi` enrollment subdomains.

13. **Hotspot DNS changes don't apply until dnsmasq restarts** — Editing the conf file is not enough if dnsmasq already has the old rules cached. Kill the dnsmasq process and restart the hotspot: `nmcli connection down Hotspot; sleep 1; nmcli connection up Hotspot`. Verify with `dig <domain> @10.42.0.1 +short` before connecting the phone.

## Evidence: Successful Bypass

On a Samsung S24 (S921BXXSFDZE1) with Miradore MDM:
- DNS blocklist prevented enrollment during setup
- Phone completed setup wizard and reached home screen
- No MDM admin visible in Settings → Security → Device Admin
- Developer Options accessible after Build Number tap

On Samsung A54 (A546E) where DNS block was applied AFTER initial boot:
- Miradore already had `DEVICE_ADMIN_ENABLED` from initial setup
- Server enrollment FAILED (3 failed registration attempts confirmed in log)
- Developer Options remained locked by local policy
- Phone usable with restrictions — need NextDNS for permanent blocking

## Network Analysis Commands

```bash
# Capture all phone traffic during setup
sudo tcpdump -i wlo1 -nn -s0 -w /tmp/setup.pcap 'host <ip>'

# Extract DNS queries
sudo tshark -r /tmp/setup.pcap -Y "dns.flags.response == 0" \
  -T fields -e dns.qry.name | sort | uniq -c | sort -rn

# Extract TLS SNI (server names)
sudo tshark -r /tmp/setup.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn

# Check for DNS failures
sudo tshark -r /tmp/setup.pcap \
  -Y "dns.flags.response == 1 and dns.flags.rcode != 0" \
  -T fields -e dns.qry.name

# Get top destination IPs
sudo tshark -r /tmp/setup.pcap -T fields -e ip.dst | sort | uniq -c | sort -rn | head -20

# Verify hotspot DNS is working correctly
dig miradore.com @10.42.0.1 +short
dig google.com @10.42.0.1 +short
dig accounts.google.com @10.42.0.1 +short
```
