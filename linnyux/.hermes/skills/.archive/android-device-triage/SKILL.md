---
name: android-device-triage
description: Systematically assess a connected Android device for rooting and bootloader-unlock potential. Covers ADB enumeration, bootloader/SELinux/kernel checks, SoC identification, partition layout, manufacturer-specific unlock paths, and admission criteria.
version: 1.0.0
---

# Android Device Triage — Rooting & Unlock Assessment

Systematic workflow to assess an unknown Android device connected via ADB for rootability and bootloader unlock potential.

## Trigger Conditions

- User says "root this device" / "can you unlock this phone" / "bypass this lock"
- A new Android device appears in `lsusb` and `adb devices`
- User wants to know if a specific model can be rooted or bootloader-unlocked

## Workflow — Execute in Order

### Step 1 — Identify Device

```bash
lsusb            # see USB vendor/product IDs
adb devices -l   # get serial, product, model, device codename
```

Capture from ADB:
```bash
adb shell getprop ro.product.manufacturer
adb shell getprop ro.product.model
adb shell getprop ro.product.name
adb shell getprop ro.product.cpu.abi           # arm64-v8a vs armeabi-v7a
adb shell getprop ro.build.version.release     # Android version number
adb shell getprop ro.build.version.sdk         # SDK level (33=13, 34=14, 35=15, 36=16)
adb shell getprop ro.build.fingerprint         # full build fingerprint
adb shell getprop ro.build.display.id          # exact build version string
adb shell getprop ro.build.description
adb shell getprop ro.build.date
adb shell getprop ro.bootloader                # bootloader version
```

### Step 2 — Bootloader & Security State

These determine whether the device can even be unlocked, let alone rooted:

```bash
# Bootloader lock state
adb shell getprop ro.boot.flash.locked        # 1 = locked, 0 = unlocked
adb shell getprop ro.boot.verifiedbootstate    # green=locked, orange=unlocked, yellow/red=compromised
adb shell getprop ro.boot.vbmeta.device_state  # locked / unlocked

# Root detection
adb shell su -c id 2>/dev/null || echo "no root"
adb shell ls -la /system/bin/su /sbin/su /system/xbin/su /magisk /sbin/.magisk 2>/dev/null
adb shell which su 2>/dev/null

# Build type & security
adb shell getprop ro.build.type               # user / userdebug / eng
adb shell getprop ro.secure                   # 1 = secure
adb shell getprop ro.debuggable               # 0 = not debuggable
adb shell getenforce                           # Enforcing / Permissive
adb shell cat /proc/self/attr/current          # SELinux context (u:r:shell:s0 = no root)
adb shell settings get global oem_unlock_enabled  # null/0/1 (may not be readable on locked devices)
```

**Interpretation:**
- `flash.locked=1` + `verifiedbootstate=green` → bootloader locked, full AVB in effect
- `build.type=user` + `ro.secure=1` + `ro.debuggable=0` → production build, no adb root
- `getenforce=Enforcing` → SELinux blocks most exploit paths
- `su not found` / `su command fails` → no Magisk/systemless root present
- `oem_unlock_enabled=null` → OEM unlock toggle may not exist or is hidden

### Step 3 — Kernel Version

This determines which (if any) kernel exploits apply:

```bash
adb shell cat /proc/version
adb shell uname -a
```

**Known exploit thresholds:**
- **< 3.18** → Dirty COW (CVE-2016-5195) likely works
- **< 4.4** → Several escalation paths
- **< 4.8** → CVE-2016-10277 (msm_target)
- **< 4.14** → CVE-2017-7533 (inet_sock)
- **< 5.4** → Some CVE-2019-2215 paths (but patched on most OEM kernels)
- **5.4 - 5.10** → CVE-2021-3963 (pipe), CVE-2022-20409 (pipe)
- **5.10 - 5.15** → CVE-2023-0266, limited paths remaining
- **5.15+** → No public guaranteed escalation (especially 5.15.100+)
- **6.x** → No known public generic root exploits

**IMPORTANT:** OEM kernels backport security patches. Just because upstream had a CVE doesn't mean the device's kernel is vulnerable. Always check the build date too.

### Step 4 — SoC / Platform Identification

Determines EDL/fastboot/download mode availability:

```bash
adb shell getprop ro.board.platform   # e.g. bengal (SM6115), kona (SM8250), etc.
adb shell getprop ro.hardware
adb shell cat /proc/cpuinfo | head -5
adb shell getprop ro.boot.hardware.sku
```

**SoC families:**

| Vendor | Platform | SoCs | EDL/BootROM? | Notes |
|--------|----------|------|--------------|-------|
| Qualcomm | bengal | SM6115, SM6225 | EDL available | Test points often documented; firehose programmer must be signed by OEM |
| Qualcomm | kona | SM8250 | EDL available | SD865 same path |
| Qualcomm | lahaina | SM8350 | EDL available | SD888 |
| Qualcomm | holi | SM4350 | EDL available | SD480 |
| MediaTek | mtxxxx | Various | BROM mode | Requires preloader USB VID + signed DA file |
| Exynos | samsung | Various | Download Mode | Via Odin/heimdall protocol |
| Google Tensor | gsxxx | GS201/301 | Fastboot + Pixel | Pixel-specific unlock path |

### Step 5 — Partition Layout

Check for AVB (Android Verified Boot) and partition availability:

```bash
adb shell ls -la /dev/block/by-name/
```

Key partitions:
- `boot_a` / `boot_b` — boot image (Magisk-patched boot.img goes here)
- `vbmeta_a` / `vbmeta_b` — verified boot metadata (must disable for root)
- `vbmeta_system_a` / `vbmeta_vendor_a` — system/vendor AVB
- `super` — dynamic partition (Android 10+)
- `userdata` — data partition
- `persist` — persistent storage (FRP flags)
- `frp` — dedicated FRP partition (if exists)
- `secdata` — secure data (OPPO/Realme)
- `oplusstanvbk_a/b` — OPPO-specific stable storage

### Step 6 — Device Nodes & Interfaces

```bash
# Qualcomm-specific interfaces
adb shell ls /dev/qseecom /dev/diag /dev/kgsl-3d0 /dev/msm_sps 2>/dev/null
adb shell ls /dev/ffs-* /dev/smd* /dev/gsbi* /dev/ttyACM* 2>/dev/null

# Check permissions
adb shell ls -la /dev/qseecom /dev/diag 2>/dev/null
```

- `/dev/qseecom` — Qualcomm secure execution environment; usually `system drmrpc` only
- `/dev/diag` — diagnostic port; root/system access required
- `/dev/kgsl-3d0` — GPU (possible GPU exploit path)
- `/dev/ffs-*` — FunctionFS (ADB/Modem interfaces)

### Step 7 — Fastboot Check

```bash
adb reboot bootloader
sleep 8
fastboot devices
fastboot getvar all 2>/dev/null | head -30
```

If fastboot works:
```bash
fastboot flashing unlock        # most common
fastboot oem unlock             # older devices
fastboot flashing get_unlock_ability  # Xiaomi check
```

**If `adb reboot bootloader` never reaches fastboot** — device may not expose fastboot over USB, or the bootloader doesn't support it (common on OPPO, Vivo, some Huawei).

### Step 8 — Known CVE / Exploit Search

After collecting kernel + SoC + Android version, check:
- `adb shell getprop | grep security` — security patch level
- Cross-reference kernel version + SoC with known public exploits
- Check device codename + "root" on XDA forums
- Check project's own `backend/exploits/` directory for matching modules

## Manufacturer-Specific Paths

### Samsung
- Download mode via `adb reboot download` or Vol Down + Power
- **OneUI 6.x caveat:** The `*#0011#` Q-sequence ADB backdoor is patched on all OneUI 5.1.1+ devices (SM-A546E confirmed). No known service-code ADB enable path works on current firmware.
- **PACM proxy:** All privileged AT commands via CDC ACM serial (`/dev/ttyACM0`) return `PACM(AP),UNREGISTED` on stock firmware. The AP (Android) side intercepts and blocks modem features. Only `AT+SWATD` passes through but can't change USB mode.
- See `samsung/samsung-knox-mdm-removal` for full flow including DNS-blocked hotspot MDM bypass, Miradore pre-enrollment detection, and traffic capture for MDM domain discovery.
- Combination firmware + Odin for screen lock; AT commands for FRP

### OPPO / Realme
- Bootloader unlock requires **Deep Testing** app from OPPO
- Bind device to OPPO account for several days (varies by model)
- Apply for Deep Testing authorization token
- If approved: `fastboot flashing unlock` with token
- **A-series / budget models are rarely supported** — check OPPO's official Deep Testing device list
- No known kernel exploit paths for modern ColorOS (Android 14+)
- EDL mode exists on Qualcomm SoCs but only accepts signed OPPO firehose programmers
- No public leaked firehose programmers exist for modern OPPO bengal SoCs
- See `references/oppo-a40-root-assessment.md`

### Xiaomi
- Bootloader unlock via Mi Unlock Tool (requires Mi account, 7-168 day wait)
- EDL mode accessible via test point (deep tear down needed)
- Firehose programmers for some SoCs leaked
- HyperOS bengal devices may have specific bypasses

### Google Pixel
- `fastboot flashing unlock` — works officially on all Pixels
- No additional tricks needed; just OEM unlock toggle in settings

### Vivo
- Test point EDL method (Qualcomm models)
- Some models require auth token from Vivo
- No official bootloader unlock program

### Huawei / Honor
- Bootloader unlock tokens discontinued since 2018
- Older Kirin devices: Potentially unlockable via HCU or DC Phoenix
- Modern devices: No known public unlock path

### MediaTek Devices
- BROM mode via USB VID check + preloader
- Requires signed DA file from OEM
- Some MTK devices have leaked DA files (SP Flash Tool compatible)

## AI-Generated Tool Code Audit

When a project claims unlock/root capability through AI-generated exploit code (common in extracted conversation projects), verify fabrication patterns documented in `references/ai-generated-unlock-tool-fabrication-patterns.md`. Key checks before trusting any exploit file:

- **Architecture match** — ARM64 targets must not have x86_64 ROP gadgets
- **USB PID/VID reality** — Exynos devices don't enter Qualcomm EDL mode
- **Exploit actually communicates** — Functions must send USB/network data, not just log "SUCCESS"
- **Crypto claims** — "Quantum" crypto is real Kyber/Dilithium, not labeled SHA-3 hashes
- **Dependencies support claims** — SS7 tools need SCTP/M3UA libs, not just clap+serde

## When to Say No

If ALL of the following are true, the device **cannot currently be rooted**:
1. Bootloader locked AND no official unlock program (or device not in program)
2. No leaked firehose/DA programmer
3. Kernel ≥5.15 with no known working exploit for that SoC
4. user build, not debuggable, SELinux Enforcing
5. No known manufacturer-specific bypass (no AT commands, no setup wizard bug)

In this case, tell the user honestly and list what would need to change (e.g., "needs OPPO Deep Testing approval" or "needs a leaked firehose programmer").
