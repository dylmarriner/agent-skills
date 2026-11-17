---
name: windows-native-usb-tooling
description: Run USB device tooling natively on Windows over SSH.
---

# Windows Native USB Device Tooling

For mobile/GSM RE tools that must actually RUN on a genuine Windows machine — the Exynos download-mode unlock toolchain (`protocol.py`, `a54_watch_dell.py`), Octoplus, Medusa, Chimera — not static-analysis-on-Linux. Static PE decompilation belongs in `windows-re-toolkit`; this skill is about getting libusb/pyusb and commercial client tooling to work natively on a Windows box you reach over SSH.

## When to use
- Driving the Exynos download-mode tool against a phone physically attached to a Windows PC (not a Wine/VM on Linux).
- Installing/activating commercial GSM tools that refuse to run under Wine and need genuine Windows runtime + USB driver stack.
- Any pyusb/libusb script that "found the device" but can't open/config it on Windows.

## Core trap: WinUSB driver binding
On Linux, kernel `usbfs` attaches the driver to a raw USB device automatically — libusb/pyusb just works (this is why the exynos toolchain runs on kubuntux with zero driver setup).

On real Windows the SAME code enumerates the device but dies at config:

```
[INFO] Found Exynos device:   (0x685D) bus=1 addr=9
[ERROR] Failed to get config: Operation not supported or unimplemented on this platform
Failed to connect to Exynos device
```

`Operation not supported or unimplemented on this platform` = **`LIBUSB_ERROR_NOT_SUPPORTED`**. It is a driver-binding wall, NOT a protocol failure and NOT a bad device. The device shows its VID:PID (looks present) but pyusb cannot read its USB config because no WinUSB/libusb-compatible driver is bound to the interface. Check the driver first; never chase protocol bugs when a Windows box "can't open" a device.

## Fix: headless Zadig WinUSB bind (driven over SSH, no GUI)
```bash
# stage zadig.exe on the Windows box, then:
C:\...\zadig.exe --vid 0x04E8 --pid 0x685D --list      # confirm the instance
C:\...\zadig.exe --vid 0x04E8 --pid 0x685D --install   # bind WinUSB to that VID/PID — requires ADMIN
python C:\...\protocol.py --frp-lock --reboot           # native run now gets past config
```
- **Re-apply per device re-plug.** A phone in download mode drops and re-binds the USB interface on each power cycle, so the WinUSB driver must be re-installed every time the device is re-inserted.
- Make the loop script watch for `0x685D` and re-bind + re-attempt (the `a54_watch_dell.py` pattern).

## Windows host preflight (before assuming it will work)
- **Admin shell:** `[Security.Principal.WindowsIdentity]::GetCurrent()` → `IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)` — Zadig driver install silently fails without admin.
- **Python** present for the pyusb toolchain (`C:\Python314\python.exe` typical).
- **.NET Framework 4.x** (`C:\Windows\Microsoft.NET\Framework64\...` shows e.g. `4.0.30319.42000`) for commercial .NET clients.
- Check `Get-PnpDevice | Where InstanceId -match '04E8'` to confirm the target phone is actually attached and enumerating.
- Note: PowerShell code with inner single quotes breaks over a single-quoted bash `ssh '...'`. Write the `.ps1` to a temp file, `scp` it over, run `powershell -ExecutionPolicy Bypass -File ...`.

## Tailnet Windows-host shell triage
Several Windows boxes may sit on the tailnet; find which one gives you a shell before planning the work:
```bash
for p in 22 5985 5986 3389 445 135; do
  timeout 3 bash -c "echo > /dev/tcp/<IP>/$p" 2>/dev/null && echo "$p OPEN" || echo "$p closed"
done
```
- **22 open** → OpenSSH works; `ssh user@IP 'hostname & ver'` gives a full shell. Get admin username from memory/knowledge.
- **Only 445+135 open** → SMB/RPC only: you can drop files over SMB but CANNOT execute anything remotely until OpenSSH or WinRM (5985/5986) is enabled on that box.
- `tailscale ping --c 2 <IP>` confirms reachability independent of port scans.

## Verified example (2026-08-24)
Tailnet Dell `desktop-g188o69` (100.104.200.49), Win11 Pro 10.0.26200 amd64, ISADMIN=True, Python 3.14, .NET 4.8, 25GB free. Native `protocol.py --frp-lock` loop found the A54 at `04E8:685D (bus=1 addr=9)` but every attempt hit `Failed to get config ... not supported` — confirmed as the missing WinUSB bind, with `zadig.exe` already staged but never applied. The other Windows box (`desktop-84nabpj`) answered tailnet ping but had only 445+135 → no shell, file-drop only.

## Pitfalls
- `ssh 'powershell "<inner-single-quotes>"'` breaks the outer single-quoted string — always use a staged `.ps1` + `scp` + `-File`.
- A download-mode device left in a stuck Odin session won't re-enumerate cleanly — physical unplug + power cycle to recover (see `exynos-download-mode`).
- Zadig install writes are per-interface; if the tool still fails after install, re-run `--list` to confirm the right instance/interface got the WinUSB driver.