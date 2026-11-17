# Samsung/Qualcomm/MediaTek Boot-Mode USB Detection

Verified signature table + udev-monitor technique for catching a phone the
instant it enters a boot/download mode over USB. Built for the S24 (SM-S921B,
Exynos 2400) but the IDs cover Odin, EUB/BROM, Qualcomm EDL, and MediaTek
BROM/preloader broadly.

## USB VID:PID signature table

| Mode | VID | PID(s) | Notes |
|------|-----|--------|-------|
| **Odin download** (Thor protocol) | `04e8` | `685d` (S24 confirmed), `6601`, `68c3`, `68ef`, `4eee`, `4eef` | `685d`/`6601` also from techeia driver table; `68c3/68ef/4eee/4eef` from odin4's own udev rule |
| **Exynos USB Boot / EUB** (BROM-level, software testpoint/zadig) | `04e8` | `1234`, `1100` | What Sigma/zadig uses for EUB; the driver shows VID_04E8 + PID_1234 or PID_1100 |
| **Qualcomm EDL** (Snapdragon only) | `05c6` | `9008`, `900e`, `901d`, `9006` | EDL is Snapdragon-only — NZ/global S921B is Exynos, does NOT do EDL |
| **MediaTek BROM / BootROM** | `0e8d` | `2000`, `2001` | Redmi Note 13 5G (Dimensity 6080, MT6833V) enters here; `2001` = BROM with DA loaded |
| **MediaTek Preloader** | `0e8d` | `0003` | Some Dimensity boots settle in preloader instead of full BROM — check both |
| **Normal MTP/ADB** (do NOT alert on) | `04e8` | `6860` | Deliberately excluded so normal plug-in doesn't false-trigger |

Key gotcha: a phone in boot mode often re-enumerates to a *different* VID:PID
than its normal MTP/ADB identity, so `lsusb` alone right after plugging in can
show "nothing" if you're watching for the normal ID. Always watch the boot-mode
IDs specifically.

## Chipset-verification lesson (Redmi Note 13 5G)

**NEVER assume the SoC from the model name.** The universal-unlock-suite's
`RedmiNote13Forcer` class was written assuming the Redmi Note 13 5G is a
Qualcomm Snapdragon 4 Gen 2 (SM4450) — it polled `QUALCOMM_VID/QUALCOMM_EDL_PID`
(05c6:9008) and would have waited forever. The actual device is a **MediaTek
Dimensity 6080 (MT6833V, codename 'gold', global variant)** with boot path
preloader `0e8d:0003` → BROM `0e8d:2000/2001`. Always confirm via `lsusb` +
`adb shell getprop ro.board.platform` / firmware codename before writing
device-specific code. MediaTek devices also use `/dev/block/by-name/`
partition paths (not Qualcomm's `bootdevice/by-name/`).

## udev monitor (instant, no polling)

The best "monitor for my phone connecting in boot mode" tool is a udev rule
firing on `ACTION=="add"` — sub-second detection, no cron/polling lag.

Rule file `/etc/udev/rules.d/99-s24-monitor.rules`:

```
SUBSYSTEM=="usb", ACTION=="add", \
  ATTR{idVendor}=="04e8", \
  ATTR{idProduct}=="6601|685d|68c3|68ef|4eee|4eef|1234|1100", \
  RUN+="/home/<user>/s24_mode_notify.sh"

SUBSYSTEM=="usb", ACTION=="add", \
  ATTR{idVendor}=="05c6", \
  ATTR{idProduct}=="9008|900e|901d|9006", \
  RUN+="/home/<user>/s24_mode_notify.sh"

# MediaTek BROM/preloader (Redmi Note 13 5G Dimensity 6080)
SUBSYSTEM=="usb", ACTION=="add", \
  ATTR{idVendor}=="0e8d", \
  ATTR{idProduct}=="2000|2001|0003", \
  RUN+="/home/<user>/s24_mode_notify.sh"
```

Pitfalls (learned the hard way):
- **udev strips PATH** — the RUN script must `export PATH="/usr/bin:/bin:/usr/sbin:/sbin"` at the top or `curl`/`date`/`hostname` silently fail.
- **udev env**: use `ID_VENDOR_ID`, `ID_MODEL_ID`, `ID_MODEL`, `ID_SERIAL_SHORT` (not the ATTR-style names) inside the RUN script.
- **Dedup by device signature** (`VID:PID:serial`) in a state file — otherwise a persistent device fires the RUN on every reload/trigger. Only alert on the connect transition.
- **Make the log path `$HOME`-relative** (`LOG="${HOME:-/home/<user>}/.log"`) so the same script deploys to multiple hosts (e.g. lin + kubuntux) without editing.
- **Normal MTP/ADB (04e8:6860) must be ignored** — the udev `idProduct` match already excludes it, but also add a string-based fallback in the script so a boot-ish product string ("download"/"modem"/"exynos"/"boot") doesn't false-positive normal traffic.
- **udev RUN scripts run as root** — write to a user-owned dir for the log or it'll be root-owned.
- **write_file refuses `/etc/...`** — must use `sudo tee` via terminal for the rules file.

Reload after writing: `sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=usb`.

## Deploy to the host the phone is ACTUALLY plugged into

The monitor only fires on the physical host the phone is plugged into, so it
must be deployed to that host. **CRITICAL correction (learned the hard way):**
do NOT assume which host that is just because the RE tooling lives elsewhere,
and do NOT bulk-deploy the rule to every box on the tailnet unprompted. This
backfired: tooling was on kubuntux, so the rule was deployed there — but the
user was physically plugging the phone into the current host (lin) and got
frustrated ("what the fuck, i'm plugging it into this laptop").

Correct sequence:
1. First `lsusb` on the **current** host — if the phone shows up there, that's
   the box to monitor; install the rule locally and you're done.
2. If it's not on the current host, check the box the user is physically at
   before reaching for remote boxes.
3. Only deploy to a second host when the user confirms that's where the device
   plugs in. Installing on a wrong box is wasted work and reads as not paying
   attention to where the user is.
