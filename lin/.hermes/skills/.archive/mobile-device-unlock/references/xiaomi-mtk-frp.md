# Xiaomi/Redmi MediaTek FRP Bypass Reference

## Model-Specific BROM Entry

| Model | Chipset | BROM Entry Combo | Actual Path | VID:PID (MTP) | VID:PID (BROM) |
|-------|---------|-----------------|-------------|---------------|----------------|
| Redmi Note 13 5G | Dimensity 6080 | Vol Down alone → recovery menu (not BROM) | sideload → `adb reboot edl` | 2717:ff40 | 0e8d:2000 |
| Redmi Note 12 5G | Dimensity 1080 | Vol Down + USB plug | — | 2717:ff40 | 0e8d:0003 |
| Poco X5 5G | Snapdragon 695 | EDL (test points) | 2717:ff40 | 05c6:9008 |
| Redmi Note 11 | Dimensity 810 | Vol Up + Vol Down + USB | 2717:ff40 | 0e8d:0003 |

## mtkclient FRP Erase Sequence (Verified)

```bash
# 1. Check device is in BROM
lsusb | grep 0e8d:0003

# 2. Erase FRP
mtk e frp

# 3. On success, device reboots — FRP cleared
# If "SLA challenge failed", see SLA section below
```

## SLA/DAA Challenge (Dimensity 1200+)

Devices with Secure Boot Loader Attestation require auth before BROM commands work. mtkclient supports this via `--auth`:

```bash
mtk e frp --auth auth.file
```

Auth files are model-specific and generally require a paid service. Alternative: Windows-only tools (Hydra Tool, UnlockTool, Chimera) that have server-side SLA bypass databases.

## Recovery Mode Factory Reset

If mtkclient fails with SLA:

1. Power off
2. Vol Up + Power → Recovery mode
3. "Wipe data" → factory reset
4. Reboot → FRP prompt appears (Google account required)
5. At this point, the FRP bypass needs either the Google account OR mtkclient BROM exploit

Note: factory reset from recovery does NOT clear FRP — it makes it worse by triggering the FRP prompt at setup. Only proceed if you have the Google account credentials.

## BROM Key Combo Quirk (Dimensity)

On Dimensity devices, **Vol Up + Vol Down + USB** often brings up the *boot mode selection menu* (fastboot/recovery), NOT true BROM. This is the preloader's boot menu, not the crash-handler BROM. 

On Redmi Note 13 5G (Dimensity 6080):
- Vol Up+Vol Down + USB → boot menu
- Vol Down only + USB → recovery main menu
- **Neither** key combo reaches true BROM. Use the sideload→EDL path instead.

## Session Log — Redmi Note 13 5G (2026-07-19)

- Device: Redmi Note 13 5G, Dimensity 6080
- MTP VID:PID: 2717:ff40
- Fastboot device: `ugayaij769fufy49`
- Fastboot: accessible but bootloader locked — `fastboot erase frp` → "not allowed in locked state"
- BROM entry: Vol Down only + USB plug (Vol Up+Vol Down gives boot menu, not BROM)
- mtkclient at ~/.local/bin/mtk
- Hotspot set up as Hermes-Hotspot (WPA2, password "unlock1234") via nmcli on host WiFi interface

### Session 2 — Mi Assistant Mode & Dimensity SLA (2026-07-19)

- BROM mode unreachable via key combo. Vol Up+Vol Down → boot menu. Vol Down only → same boot menu on this unit.
- **Mi Assistant mode** (recovery → "Connect with Mi Assistant"): USB presents as **18d1:4e11** (Google Inc. Nexus One descriptor)
- Mi Assistant USB interface: class=255 subclass=66 protocol=1 — **this IS ADB sideload mode**, not fastboot. Configuration descriptor says "adb". Interface labeled "ADB Interface".
- `adb devices` shows device as `ugayaij769fufy49 sideload`. ADB shell blocked, but `adb reboot` works.
- **CRITICAL DISCOVERY**: `adb reboot edl` from sideload successfully enters BROM at **0e8d:2000** (MT65xx Preloader). This is the bypass when key combos fail.
- In BROM (0e8d:2000): mtkclient detects preloader port but **handshake fails** — Dimensity SLA/DAA blocks unauthorized commands. 5 retries → timeout → phone reboots to MTP.
- Standard `fastboot` CLI does NOT connect to 18d1:4e11 Mi Assistant device (even with `-i 0x18d1`)
- Python raw USB access to 18d1:4e11 **crashes the device** — it disconnects after `set_configuration()` or first bulk write
- **Verdict**: Getting into BROM is now solved (sideload → edl). But Dimensity 6080 BROM SLA still requires a paid tool (UnlockTool, Chimera, Hydra Tool). Free mtkclient cannot auth.
- **Full BROM entry path**: Power off → Vol Up+Vol Down + USB → boot menu → select "Connect with Mi Assistant" → `adb devices` confirms sideload → `adb reboot edl` → `lsusb | grep 0e8d:2000` confirms BROM
