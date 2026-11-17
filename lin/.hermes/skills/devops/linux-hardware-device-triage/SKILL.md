---
name: linux-hardware-device-triage
description: "Use when a Linux device isn't detected or needs drivers."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [linux, hardware, drivers, firmware, wifi, bluetooth, diagnostics, dmi, bios, udev]
    related_skills: [linux-laptop-performance-tuning, linux-thermal-throttling-triage, webcam-rtsp-bridge]
---

# Linux Hardware / Device Triage

"X doesn't work, install the drivers" is a request to *diagnose*, not to install.
The deliverable is a verdict — which rung of the presence ladder fails — plus the
actual next action, and an explicit statement of what software cannot distinguish.

## When to Use

- "Install the wifi/audio/camera/bluetooth drivers", "the X isn't recognised",
  "the device disappeared", "no wifi networks show up".
- Any model-specific advice (which card, which firmware file, which package) — you
  need the real model first, and it is usually not the one on the label.
- After a hardware swap, drive clone, reimage, or kernel upgrade.

## Non-negotiables

1. **Hardware identity comes from firmware, not from labels.**
   `/sys/class/dmi/id/{sys_vendor,product_name,product_version,board_name,bios_version,bios_date}`
   is authoritative; corroborate with `hostnamectl`. WHY: a static hostname (and
   asset tag, and mount label) is set once and survives drive cloning and
   reimaging, so it can name a laptop the machine never was — and a wrong model
   makes every downstream recommendation wrong.
2. **Establish presence before touching packages.** A driver install is only the
   correct fix when triage lands on *enumerated but unbound* or *bound but
   firmware-refused*. Installing a package so the answer looks responsive is a
   no-op against hardware the kernel never saw.
3. **Silence in the driver's log means the device was never probed — not that
   firmware is missing.** An empty `dmesg | grep <driver>` sends you hunting
   firmware for a radio that isn't there. Firmware problems say "firmware"
   loudly; quiet means no device.
4. **Never conclude "no hardware" from one missing function.** Combo modules
   expose their functions on different buses (WiFi over PCIe, its Bluetooth half
   over USB; codec over HDA/PCI, amp over I2C). One half enumerating while the
   other is absent proves the module is *present* and that one function is not
   enumerating — a different fix from "card missing".
5. **Read firmware/UEFI settings; never write them.** They are readable live
   from `/sys/class/firmware-attributes/` (see Procedure), but a write is a
   persistent NVRAM change — hand the user the F10/BIOS step instead, even when
   the interface would accept your write.
6. **Non-destructive re-probe before a verdict.** A rescan plus a module reload
   clears a stuck function and costs nothing; declare hardware dead only after it.
7. **Report the physical ladder** (power drain → firmware defaults → reseat in the
   correct slot → replace/dongle), and say plainly which causes software cannot
   distinguish. Also say plainly when you installed and changed nothing.
8. **Treat raw removable-media imaging as destructive.** Before writing, identify
   the exact whole-disk target with `lsblk` (path, model, size, transport, partitions),
   obtain explicit user confirmation to erase that device, and re-check identity
   immediately before the write. Unmount its partitions, write the image, flush
   writes, then verify the written image-length bytes against the source. Never
   infer completion from a started command, timeout, or partial comparison.

## Procedure

### Removable boot-media imaging

When the user asks to create a bootable USB, first inspect the image and enumerate
removable disks; do not choose a target by stale mount labels or guess from device
names. Show the exact target and erase consequence, and wait for explicit consent.
After consent, re-enumerate the target, confirm it is still the same whole disk,
unmount its partitions, write the image to the whole-disk node, flush, and compare
exactly the image's byte length from source to device. If execution is blocked or
interrupted, state that the media is not verified; do not claim it was created or
send the user to a manual workaround as though the requested operation succeeded.

### 0. Identity, then scope

```bash
for f in sys_vendor product_name product_version board_name bios_version bios_date; do
  printf '%-16s %s\n' "$f" "$(cat /sys/class/dmi/id/$f 2>/dev/null)"; done
hostnamectl --static; hostnamectl | grep -i 'Hardware Model'
sudo -n true 2>&1 && echo 'sudo: passwordless' || echo 'sudo: needs password (do not emit root commands)'
```

Settle whether you have root *before* writing commands that need it.

### 1. Presence ladder — find which rung fails

```bash
lspci -nnk | grep -iA3 -E 'network|wireless|audio|display'   # on the bus at all?
lsusb                                                        # USB-attached functions
ls /sys/class/ieee80211/ /sys/class/sound/ /dev/video*       # userland-visible devices
ls -l /sys/bus/pci/drivers/<driver>/                         # device symlinks == actually bound
for d in /sys/bus/pci/devices/*; do printf '%s %s %s\n' \
  "$(cat $d/class)" "$(basename $d)" "$(basename $(readlink -f $d/driver 2>/dev/null))"; done | sort
```

The last one enumerates every PCI function with its class code and bound driver —
the fastest way to prove a whole class of device (all `0x02*` network, all `0x04*`
audio) is absent rather than merely unnamed. Enumerate by *class*, not by the
product names you expect.

`scripts/device-presence-probe.sh [keyword]` runs the whole ladder read-only in
one shot (identity, PCI+driver map, USB, class subsystems, firmware on disk,
kernel log) — use it instead of hand-typing six commands.

### 2. Kernel-side support (before claiming a driver is missing)

```bash
modinfo <module> | grep -c '^alias:'        # N device aliases = the driver covers many parts
modinfo <module> | grep -i <model-number>   # is THIS part in the table
lsmod | grep -E '^<module>|^mac80211|^cfg80211'
```

### 3. Firmware on disk

```bash
ls /lib/firmware/<prefix>*        # e.g. ls /lib/firmware/iwlwifi-8265-*
```

Modern Debian/Ubuntu ship firmware **zstd-compressed** (`<name>.ucode.zst`,
`.bin.zst`). Checking the bare upstream filename reports a false "missing" and
sends you off to install a package you already have. Always glob.

### 4. Non-destructive re-probe

```bash
sudo -n sh -c 'echo 1 > /sys/bus/pci/rescan'      # surface a function the kernel missed
sudo modprobe -r <module> && sudo modprobe <module>
sleep 2; ls /sys/bus/pci/drivers/<module>/ | grep -v -E '^(bind|unbind|module|new_id|remove_id|uevent)$'
```

### 5. Firmware/UEFI settings, read live

```bash
ls /sys/class/firmware-attributes/                 # vendor interface, e.g. hp-bioscfg (needs the vendor module loaded)
python3 - <<'PY'
from pathlib import Path
b = Path('/sys/class/firmware-attributes/<vendor-iface>/attributes')
for a in sorted(b.iterdir()):
    if any(k in a.name.lower() for k in ('wlan','wireless','radio','network','bluetooth')):
        cv, pv = a/'current_value', a/'possible_values'
        print(a.name, '=', cv.read_text().strip() if cv.exists() else '?',
              '|', pv.read_text().strip() if pv.exists() else '-')
PY
```

Attribute names contain spaces and punctuation, so iterate the directory (Python
`pathlib` or a quoted loop) — an unquoted `basename $a` shell loop dies with
`extra operand` and hides the values you were reading for.

### 6. Verdict

Quote the probe output as evidence, name the failing rung, name the physical
actions, and flag anything only a swap/test can prove. If the answer is "no
driver to install", lead with that — do not leave the user to infer it from a
wall of output.

## Pitfalls

- **Trusting the hostname for the model.** It is a label, not identity; DMI is the
  board's own answer. Get this wrong and every model-specific recommendation is
  wrong with it.
- **`.ucode` / `.bin` vs `.zst`** — a false "firmware missing" verdict; the file is
  right there compressed. Glob the prefix.
- **Empty driver log treated as firmware trouble.** No probe happened, because no
  device exists to probe.
- **One missing function read as one missing card.** Check the other buses the same
  module could be on (USB BT alongside PCIe WiFi is the classic pair) before
  saying "no hardware".
- **A BIOS/UEFI flag left unread.** "Disabled in setup" is a common cause of a
  cleanly absent device, and the vendor attribute interface usually answers it in
  one read — no reboot needed.
- **Writing to `/sys/class/firmware-attributes/`** because the file is writable.
  It persists in NVRAM; that is the user's call, in setup, not an agent's.
- **Assuming sudo.** Probe with `sudo -n true`; passwordless is common on some
  fleet boxes and absent on others, and the emitted command list differs.
- **Installing a package to appear responsive** when the device was never on the
  bus. Report the verdict instead; the honest deliverable is what actually moves
  the problem.

## Support files

- `references/wireless-radio-triage.md` — the wireless case end-to-end: the exact
  tells for absent vs unenumerated vs dead radio, combo-module ID pairing, kernel
  vs out-of-tree adapters, and the HP BIOS attribute names.
- `scripts/device-presence-probe.sh` — read-only one-shot presence ladder; accepts
  an optional grep keyword (default `network|wireless|audio|bluetooth`).
