# Redmi Note 13 5G FRP Session Log

**Device:** Redmi Note 13 5G (global), codename "gold/iron"
**Chipset:** MediaTek Dimensity 6080 (MT6833V)
**HW Revision:** ca00
**Region:** gl (global)
**Anti Rollback:** 1
**Bootloader:** Locked, unlock_ability=0 (server-blocked)
**Serial:** ugayaij769fufy49

## USB Modes Observed

| Mode | VID:PID | How to Reach | Tool |
|------|---------|-------------|------|
| MTP (locked OS) | 2717:ff40 | Power on, MTP selected | None |
| Boot menu | — (no USB) | Vol Up+Vol Down+plug | None (selection screen only) |
| Fastboot | 18d1:d00d | Boot menu → Fastboot | fastboot, PyUSB |
| Mi Assistant (sideload) | 18d1:4e11 | Boot menu → Connect with Mi Assistant | adb |
| BROM (after EDL cmd) | 0e8d:2000 | Sideload → `adb reboot edl` | mtkclient |

## Key Commands That Worked

```bash
# From fastboot (18d1:d00d):
fastboot getvar all              # Full partition map, token, etc.
fastboot getvar token            # base64 unlock token
fastboot flashing get_unlock_ability  # Returns 0 — server-locked

# From Mi Assistant (18d1:4e11):
adb devices -l                   # Shows ugayaij769fufy49 sideload
adb reboot edl                   # Switches to 0e8d:2000 BROM!

# Direct PyUSB fastboot (18d1:d00d) when standard fastboot hangs:
python3 -c "import usb.core; dev = usb.core.find(idVendor=0x18d1, idProduct=0xd00d)"
```

## What Failed (and Why)

- `fastboot flashing unlock` / `fastboot oem unlock` — FAIL (unlock_ability=0, server-blocked)
- `fastboot oem edl` — TIMEOUT. Qualcomm-only command, MediaTek ignores it.
- `fastboot erase frp` — TIMEOUT (blocked by locked bootloader, hangs)
- `fastboot oem device-info` — TIMEOUT (hangs on locked Xiaomi fastboot)
- mtkclient handshake in BROM — SLA/DAA protection on Dimensity 6080 blocks it
- Standard `fastboot devices` on 18d1:4e11 — returns empty (it's ADB sideload, not fastboot)
- `mtk crash` on 18d1:4e11 — no effect (not a MediaTek mode)
- Network FRP bypass (DNS redirect + fake HTTPS) — cert pinning blocks self-signed MITM
- **Xiaomi DA key ported to BROM** — does NOT match (BROM & DA use different RSA keys on Dimensity 6080)
- **SP Flash Tool under Wine** — loads DA, reports "Loading Da OK!", but fails at USB layer (Wine can't passthrough raw MTK USB)

## BROM Entry Path (Only Reliable Method)

1. Power off (hold ~10s, release at black screen — NOT 15s which triggers reboot)
2. Immediately hold Vol Up+Vol Down, plug USB
3. Boot menu appears → select **Connect with Mi Assistant**
4. Device at 18d1:4e11 (ADB sideload, subclass 66 protocol 1)
5. `adb reboot edl` → BROM at 0e8d:2000

**Why physical combos don't work:** Xiaomi's preloader on Dimensity 6080 intercepts Vol Up+Down → redirects to boot menu. Vol Down alone → recovery main menu. Neither reaches BROM directly.

## Dimensity SLA Block Behavior

1. Preloader detected (0e8d:2000)
2. Handshake initiated — "Handshake failed, retrying..."
3. SLA check fails — BROM rejects handshake
4. After ~60 seconds (5 retries), BROM abandons
5. Phone reboots to MTP (2717:ff40)

mtkclient v2.1.4: 36 BROM SLA keys (mostly Alcatel/Generic/Motorola), 8 DA keys (including 1 Xiaomi key at DA index 7). No Dimensity 6080 key.

## Mi Flash Tool Analysis

Mi Flash 20220507 at ~/Downloads/MiFlash20220507/:
- `da/auth_sv5.auth` — generic auth (MD5: 0191491e) — DIFFERS from firmware auth
- `da/MTK_AllInOne_DA.bin` — 14MB DA loader (handles SLA)
- `SP_Download_tool/Authentication.dll` — exports sec_init_key, sec_auth_challenge, sec_hash, sec_verify
- SP Flash Tool under Wine: loads but fails USB passthrough. Needs native Windows.
- Firmware auth_sv5.auth from gold firmware (MD5: 94e8fa99) is device-specific, differs from tool-generic

## Remaining Paths to FRP Bypass

1. **Native Windows + Mi Flash 20220507** — install on VM/bare metal, BROM → SP Flash Tool → format FRP
2. **Paid tool** — UnlockTool/Hydra/Chimera has Dimensity 6080 SLA key ($30-50)
3. **Extract BROM key from preloader** — download full firmware, extract preloader_gold.bin, reverse SLA key
