---
name: motorola-bootloader-unlock
description: "Unlock a Motorola bootloader; fix portal/OEM/FRP gates."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [motorola, moto, fastboot, bootloader, unlock, qualcomm, edl, frp]
    related_skills: [samsung-unlock, samsung-usb-protocol, exynos-download-mode]
---

# Motorola Bootloader Unlock

## When to Use

- Any Moto/Motorola device headed for a custom ROM, root, or NetHunter.
- Any `fastboot oem unlock` that fails, or returns a `(bootloader)` refusal.
- Deciding whether a given Moto unit is worth attempting at all — CID / SKU / FRP pre-flight.
- Qualcomm EDL (9008) work on a Motorola device.

Not for Samsung/Exynos devices; those have their own skills (`samsung-unlock`, `samsung-usb-protocol`, `exynos-download-mode`).

## How this user wants it run

- Execute, don't narrate. Send the command, report the literal result.
- Never present options. Pick the path and run it.
- **When the user pivots to a sub-problem, drop the previous thread entirely** — no background jobs, no adjacent work, no preamble. Working the old thread while the user is talking about the new one reads as ignoring them.
- Answer the question that was actually asked, first. "How do I do X when it's locked?" is a question about X, not about the plan around X.
- Report a failure as what it literally is. A refusal caused by a missing prerequisite is not a rejection, and calling it one sends the user off chasing the wrong thing.

## Step 0 — identify the device before touching anything

```bash
fastboot devices
fastboot getvar all
```

The subset that decides everything:

| var | why it matters |
|---|---|
| `product` / `sku` / `carrier_sku` | codename + exact variant |
| `ro.carrier` | software channel — retail vs carrier-locked |
| `cid` | **eligibility** (table below) |
| `securestate` | `oem_locked` / `flashing_unlocked` |
| `frp-state` | `protected (N)` = a Google account is armed |
| `fdr-allowed` | whether recovery is permitted to wipe |
| `iswarrantyvoid` | Moto has no Knox-style fuse; unlock is reversible via relock on stock |
| `current-slot`, `slot-unbootable:_x` | A/B state |

Current Moto bootloaders are UEFI (`MBM-3.0-uefi-*`) and **have no `fastboot oem edl`** — dump `fastboot oem help` to see what abl actually accepts rather than assuming.

## Step 1 — extract the unlock data

```bash
fastboot oem get_unlock_data 2>&1 | grep -oP '^\(bootloader\) \K.*' \
  | sed 's/^Unlock data://' | tr -d '\n' > ~/unlock-data.txt
wc -c < ~/unlock-data.txt    # expect ~155 chars
```

**Never retype this string, and never transcribe it into chat.** It is ~155 chars of opaque hex with `#` separators. A single dropped character makes the portal answer "does not qualify", which reads exactly like a hardware refusal. Hand over the **file path** plus a length and a hash, never a retyped copy:

```bash
wc -c < ~/unlock-data.txt; sha256sum ~/unlock-data.txt
```

Before blaming the phone, re-pull and diff — a fresh pull must be byte-identical to the saved file.

## Step 2 — the portal

```
https://en-us.support.motorola.com/app/standalone/bootloader/unlock-your-device-b
```

- Sign-in is mandatory; there is no anonymous form. **Any account works** — the portal does not check the account against the device.
- **There is no NZ portal.** `en-nz.support.motorola.com` does not resolve. NZ/AU use `en-au.support.motorola.com`; `en-us` and the UK host are the same custhelp backend under a different locale prefix. Region does not change eligibility.
- **Do not drive this portal from an automated browser.** Google SSO answers "This browser or app may not be secure" and the Moto ID form escalates to a reCAPTCHA image challenge. The working path: the user signs in from their own browser and you take the code from there. A browser bridge is usable **only** if it reports an attached tab — a running bridge server with no browser attached is not.
- **"Your device does not qualify for bootloader unlocking" has three meanings and the portal uses identical words for all of them:** (1) malformed/truncated/line-broken unlock data, (2) a transient backend error that clears on retry, (3) a genuine refusal. Re-verify the string and the CID before believing (3).
- A "Congratulations" page is only the approval. The bootloader is still locked; the code arrives by email to the account used.

## Step 3 — the two gates that actually block the unlock

The code is necessary but not sufficient.

**Gate A — the OEM-unlocking toggle.** Without it, `fastboot oem unlock <CODE>` returns:

```
(bootloader) Check 'OEM unlocking' in Android Settings > Developer Options
FAILED (remote: '')
```

Read that literally: it is **not** a key error. The bootloader checks the toggle *before* it evaluates the code, so the code has not been tested at all and stays valid. Never report the code as dead on the strength of this message.

- Nothing in fastboot exposes the flag: `oem_unlock_allowed`, `unlock_ability`, `is_unlock_allowed`, `utags` all return `not found`, and `flashing get_unlock_ability` just redirects to the portal. The toggle is only settable from Android.
- Path: `Settings → About phone → tap Build number ×7 → System → Developer options → OEM Unlocking`.
- On recent Moto it stays greyed out until the device has been online (Wi-Fi and/or SIM) for up to a week. That gate lifts on its own.

**Gate B — the locked-bootloader privilege gate.** With `securestate: oem_locked`, abl refuses every privileged `oem` command:

```
fastboot oem blankflash    → (bootloader) Command Restricted
fastboot oem qcom-on       → FAILED
fastboot oem bp-tools-on   → FAILED
```

Benign/read-only ones still work: `oem read_sv`, `oem cid_prov_req`, `oem fb_mode_set`, `oem fb_mode_clear`. If you set `fb_mode_set`, always pair it with `fb_mode_clear` so you don't leave the device booting into fastboot.

## CID eligibility — the one pre-flight check worth running

```bash
fastboot getvar cid
```

| Qualifies | Does NOT qualify |
|---|---|
| `0x0000` `0x0003` `0x0007` `0x0009` `0x000B` `0x000C` `0x000D` `0x000E` `0x0014` `0x0015` `0x00DE` `0x0032` | `0x0001` `0x0002` `0x0004` `0x0005` `0x0006` `0x0008` `0x000A` `0x000F` `0x0010` `0x0011`, plus anything absent from the left column |

Carrier-exclusive SKUs (Verizon / AT&T / Tracfone and similar) are refused regardless of CID. Eligibility is decided server-side: no generic command or paid key service overrides a refusal.

## The FRP knot

```
FRP screen        → can't reach Settings
Settings          → the only place the OEM toggle lives
OEM toggle ON     → what the bootloader checks before accepting the code
bootloader unlock → the thing that wipes /data and clears FRP
```

Circular by design. A factory reset does **not** break it — FRP survives a wipe by definition, so `fdr-allowed: yes` is not an escape and burning it costs the user data for nothing.

Breaking it needs exactly one thing: **reach Settings → Developer options once.** Full FRP removal is not required. Routes and their caveats: `references/frp-oem-toggle-gate.md`.

## Known-good sequence

```bash
fastboot getvar all                    # product, sku, cid, securestate, frp-state
fastboot oem get_unlock_data           # -> ~/unlock-data.txt ; verify length + sha256
# user signs in and requests the code at the portal, in THEIR browser
fastboot oem unlock <CODE>             # requires OEM Unlocking already ON
fastboot getvar securestate            # want: flashing_unlocked
```

Unlock wipes `/data`. Unlike Samsung there is no permanent fuse — relocking on full stock restores the stock state.

## Pitfalls

- **A refusal message is not a verdict until the input is proven byte-exact.** Re-pull the unlock data and diff it against the saved file first; a truncation is indistinguishable from a hardware block at the portal.
- **An opaque token only leaves your hands as a file.** Path + length + hash. The failure mode of a retyped copy is silent and gets misattributed to the device.
- **Don't report fastboot results without re-checking the mode.** After any reboot, re-run `fastboot devices` before the next command — one issued while the phone is back in Android returns `unknown command` / `GetVar Variable Not found`, which looks like a device fault and isn't.
- **`lsusb`'s ID database mislabels Motorola PIDs.** A current Moto enumerates as `22b8:2e82` and lsusb prints `XT1541 [Moto G 3rd Gen]`. Trust the device's own string (`sudo lsusb -v | grep iProduct`) or `getvar product`.
- **The PID changes with USB mode** — MTP-only, MTP+ADB, and fastboot are different PIDs. `bNumInterfaces: 1` with a vendor-specific class in `lsusb -v` means USB debugging is off, whatever the on-screen "USB mode" says. The debugging toggle is the only thing that matters; MTP vs charging does not affect ADB.
- **Diagnose before unlocking.** If the device is FRP-locked, resolve that first — the unlock is gated behind a settings screen the FRP lock hides.

## References

- `references/frp-oem-toggle-gate.md` — the FRP knot, documented setup-wizard escapes, and why EDL doesn't shortcut it
- `references/qualcomm-edl.md` — EDL entry methods, firehose programmers, and the `edl` tool
