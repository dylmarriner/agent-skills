# OPPO A40 (CPH2669) — Root Assessment

## Device Info
- **Model:** CPH2669 (OP5B16L1)
- **Manufacturer:** OPPO
- **Android:** 16 (BP2A.250605.015) — May 2026 build
- **SoC:** Qualcomm SM6115 (bengal platform)
- **Kernel:** Linux 5.15.180-android13-8-o-01037 (Clang 14.0.7)
- **Arch:** arm64-v8a

## Boot State
- **Bootloader:** LOCKED (flash.locked=1)
- **Verified Boot:** green (full AVB)
- **vbmeta device state:** locked
- **SELinux:** Enforcing (u:r:shell:s0)
- **Build type:** user (not userdebug/eng)
- **ro.secure:** 1
- **ro.debuggable:** 0

## ADB Access
- ADB works as `shell` (uid=2000) only
- No root
- No Magisk present
- `/data/local/tmp/` writable

## Partition Layout
- Standard A/B slots (boot_a/b, vbmeta_a/b, etc.)
- `oplusstanvbk_a/b` — OPPO stable storage (carries lock/boot state across flashes)
- `oplusreserve[3-5]` — OPPO reserved partitions
- `persist` — FRP flag storage
- `splash_a/b` — boot splash
- `super` — dynamic partition (Android 10+)
- `vbmeta_system_a/b`, `vbmeta_vendor_a/b` — additional AVB layers

## Device Interfaces
- `/dev/qseecom` — Qualcomm SEE, but `system drmrpc` only (no shell access)
- `/dev/diag` — not accessible from shell
- `/dev/ffs-diag`, `ffs-diag-1`, `ffs-diag-2` — FunctionFS diag but wrapper only
- `/dev/kgsl-3d0` — GPU accessible but no known exploit path
- `/dev/msm_sps` — SPS interface
- `/dev/ttyEUD0` — USB debug serial? untested
- `/dev/ttyGS0` — gadget serial (possible ACM channel)

## Root Paths Evaluated

### 1. Bootloader Unlock via OPPO Deep Testing
- OPPO requires Deep Testing app authorization
- A40 is a budget A-series device — NOT in OPPO's official Deep Testing support list
- Even if approved, requires OPPO account + device binding period
- **Status:** Not available for this model

### 2. Kernel Exploit
- Kernel 5.15.180 on Android 16 — no known public exploit
- All common CVEs (pipe, etc.) patched in this kernel version range
- **Status:** No known path

### 3. Qualcomm EDL Mode
- SM6115 has EDL mode via test point (likely under back cover near SoC)
- However: OPPO signs their firehose programmers
- No public leaked firehose programmer for OPPO SM6115/bengal
- **Status:** Dead without signed firehose programmer

### 4. AT Command / Diag Exploit
- OPPO does NOT expose Samsung-style AT command CDC ACM from MTP
- No QPST/diag channel accessible from shell
- **Status:** No path

### 5. Fastboot
- `adb reboot bootloader` does not reach functional fastboot on this device
- OPPO bootloaders on modern ColorOS may not expose fastboot over USB
- **Status:** No fastboot access

## Conclusion

**The OPPO A40 (CPH2669) on Android 16 cannot currently be rooted via any known public method.** The device is fully locked down:
- Bootloader locked with no official unlock path for this model
- Production build with full AVB + SELinux
- No kernel exploits for Android 16 / kernel 5.15.180
- No leaked firehose programmer for OPPO SM6115

### What Would Change This
1. OPPO adds A40 to Deep Testing support list → bootloader unlock → Magisk
2. A leaked firehose programmer surfaces → EDL flash Magisk-patched boot
3. A kernel-level CVE is discovered for 5.15.x Android common kernels
4. A Qualcomm BootROM-level exploit emerges for SM6115
