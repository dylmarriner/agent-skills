---
name: android-nethunter-kernel-port
description: "Add NetHunter support to an unsupported device's kernel."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [android, kernel, nethunter, lineageos, defconfig, qualcomm, config-fragment]
    related_skills: [motorola-bootloader-unlock, exynos-download-mode]
---

# Android NetHunter Kernel Port

## When to Use

- NetHunter **Full** on a device with no prebuilt NetHunter kernel in Kali's device list.
- Any Android/QCOM kernel build where you are layering a config fragment onto a vendor defconfig.
- Deciding whether a device needs a kernel port at all, or only NetHunter Lite.

## Step 0 — measure the gap before writing anything

Most of NetHunter Full is **config, not patches**. Read the existing fragment chain first.

On many modern Qualcomm devices the following are *already enabled* in the base `vendor/<soc>-qgki_defconfig`:

| Already on | Feature |
|---|---|
| `CONFIG_USB_CONFIGFS_F_HID` | BadUSB / HID keystroke injection |
| `CONFIG_USB_CONFIGFS_MASS_STORAGE` | DriveDroid |
| `CONFIG_USB_CONFIGFS_ECM` / `_NCM` | BadUSB network MITM |
| `CONFIG_BT_RFCOMM` / `_TTY` | Bluetooth Arsenal |
| `CONFIG_CFG80211` / `CONFIG_MAC80211` | external-adapter stack |

The real gap is then just the **external USB adapter drivers** and the SDR/serial/CAN extras. "No NetHunter kernel exists" does not mean "none of NetHunter's features are compiled in" — quantify before promising a port.

See `references/nethunter-config-requirements.md` for the symbol catalogue.

## The three options you must NOT set

```
CONFIG_CFG80211_WEXT
CONFIG_MAC80211_MESH
CONFIG_WIRELESS_WDS
```

They change the memory layout of structs behind exported symbols, which changes their genksyms CRCs. Every module built against the old CRCs then refuses to load — on a device whose WiFi/charger/touch drivers are prebuilt modules you get a phone that boots with no WiFi, no touchscreen and no charging. They buy nothing for NetHunter. Treat them as forbidden and **assert their absence**, because the temptation to "fix" a missing-driver problem by setting them is exactly how this breaks.

## Merging the fragment

Layer order matters: base defconfig → OEM/device fragments → **yours last**, so yours wins. Mirror the ROM's own order — read `TARGET_KERNEL_CONFIG` in the device tree, which is a list of fragments layered over a base defconfig.

```bash
# the target name is RELATIVE to arch/<ARCH>/configs/
make -s ARCH=arm64 LLVM=1 O="$OUT" vendor/<soc>-qgki_defconfig
ARCH=arm64 scripts/kconfig/merge_config.sh -m -O "$OUT" "$OUT/.config" <fragment>...
make -s ARCH=arm64 LLVM=1 O="$OUT" olddefconfig
```

**`%_defconfig` prepends `arch/<ARCH>/configs/` itself.** Passing the full path makes it look for `arch/arm64/configs/arch/arm64/configs/...` and it dies with a bare `Error 1` naming the target and `scripts/kconfig/Makefile` — with none of that in the message. Always pass the bare name (`vendor/foo_defconfig`), never the path.

Add your config as a **new** fragment file plus one `TARGET_KERNEL_CONFIG += ...` line in the device `BoardConfig`. Never edit the OEM's fragment — one file plus one line keeps the diff reviewable and survives their updates.

## Always assert the final `.config`

`merge_config.sh` followed by `olddefconfig` **silently drops a symbol whose dependencies aren't satisfied** — the value is written, then the resolve step discards it. A fragment that looks cleanly applied can produce a kernel missing exactly the drivers it was added for.

End every merge with a check over `$OUT/.config`, two lists:

- **required** — present *and equal to the expected value*. `=y` and `=m` are different outcomes; grep for the exact `CONFIG_X=y` string (`grep -qx`), not `grep '^CONFIG_X='` which also matches `=m`.
- **forbidden** — absent. Specifically the three above.

Fail loudly and do not start the build on failure. A dropped symbol that reaches the compile stage costs a full build cycle to discover.

## Toolchain

The tree pins its compiler. Read it:

```
build.config.common → CLANG_PREBUILT_BIN=prebuilts-master/clang/host/linux-x86/clang-r<ver>/bin
```

- **Old clang versions are pruned from the AOSP prebuilts `main` branch** — only the newest few survive there. Find the pinned version on the matching `android-<ver>.0.0_r1` branch instead (`git fetch --depth 1 --filter=blob:none origin android-12.1.0_r1`, then `git ls-tree --name-only FETCH_HEAD | grep '^clang-r'`).
- **Fetch one clang, not the repo** (~30 GB otherwise):

```bash
mkdir -p toolchain && cd toolchain
git clone --depth 1 --filter=blob:none --sparse <prebuilts-url> clang
cd clang && git sparse-checkout set clang-r<ver>
git fetch --depth 1 --filter=blob:none origin android-<ver>.0.0_r1
git checkout -f FETCH_HEAD
```

- `flex` and `bison` are required for the kconfig step — `scripts/kconfig/lexer.lex.c` is generated. Their absence surfaces as `Error 127` naming that generated file, which does not say "flex".
- **Disk:** a full LineageOS tree is 250-400 GB; a standalone kernel build is ~30 GB. Check free space before committing to a build path.

## Verification status — read this before trusting a port

**The merge + assert stage is validated. The compile/flash stage is not.** A config that passes the assert is a necessary condition, not a working kernel. Do not present a port as done, or hand it to a user as installable, until a real build has produced a boot image and a device has booted it.

For reference, the platform-level concerns that a Flashable Full port has to solve and that a config-only change does not:

- devices that keep WiFi/charger/touch as **modules inside `vendor_boot`** — AnyKernel3 does not touch `vendor_boot`, so a custom kernel must ship its own `wlan.ko` with a byte-identical release string, or splice the modules into a rebuilt `vendor_boot.img`
- AVB (`BOARD_AVB_*` rollback indices) — a modified boot/vendor_boot needs verification disabled or a re-signed vbmeta
- internal-WiFi monitor/injection on `qcacld` is a driver patch plus (often) shipping your own `wlan.ko`; external USB adapters are the lower-risk path to injection and need only drivers

## Pitfalls

- **Never ship a fragment without the assert pass.** Silent symbol drops are the failure mode that costs a whole build.
- **Don't assume the pinned clang is available where you expect.** Pruning is silent: the directory simply is not in the tree on `main`.
- **Don't report a port as working from a config diff.** State what has been proven and stop there.
- **Prefer HID + external-adapter drivers as the first milestone.** Both are config-only and ABI-safe, so they cannot break the module stack; internal-WiFi injection is a separate, riskier change.

## References

- `references/nethunter-config-requirements.md` — the NetHunter config symbol catalogue and where each one is checked
