# Device-mode & driver triage over SSH (Samsung on a remote Windows box)

Session-derived detail (2026-08-26, Dell `desktop-g188o69` 100.104.200.49, user `sbkha`, built-in OpenSSH). Complements the SKILL.md body — this is the "is it actually there, in what mode, and which driver binds it" playbook on top of the WinUSB/binding core trap.

## Live vs ghost USB ground truth (THE key correction)
Both `pnputil /enum-devices` and a bare `Get-PnpDevice` list **ghost/cached driver nodes** — devices from previous connections and anything registered in the driver store — with `Status: Unknown`. They look present and will mislead you (a "Samsung Mobile USB Composite Device" and a "SAMSUNG USB COM3" both showed up as ghosts before anything was plugged in, thanks to earlier staged unlock work).

**Authoritative "what is physically on the bus right now":**
```powershell
Get-PnpDevice | Where-Object { $_.Present -and $_.InstanceId -like 'USB*VID_04E8*' } | Select Status,Class,FriendlyName,InstanceId | Format-List
[System.IO.Ports.SerialPort]::GetPortNames()   # live COM ports separately
```
- `Present=$false` / `Status=Unknown` without `Present` ⇒ ghost; ignore for state.
- `WMI Win32_PnPEntity where Status='OK'` returned **nothing** for the Samsung nodes even when present — do not use WMI status as the presence signal; use `Get-PnpDevice Present`.

## Samsung VID/PID mode map (04E8)
- **`04E8:685D`** = DOWNLOAD MODE. Exposes download-mode COM/DFU interfaces; on the unlocked tooling this is the WinUSB-bound (libwdi/`samsung_usb.inf`, class **Ports**) target for `protocol.py`. Landing here is the actual goal for the Exynos unlock/readback path.
- **`04E8:6860`** = NORMAL / MTP composite (booted phone). Child functions: `&MODEM` (Samsung Mobile USB Modem → a live COM port), `&MS_COMP_MTP` (MTP/WPD), `&ADB` (Android ADB interface, only when USB debugging is on). Distinguish the two modes by PID before planning anything.

## Samsung modem AT restriction in AP (booted) mode
A phone in normal (6860) mode presents a `SAMSUNG Mobile USB Modem` serial (e.g. COM8). It answers AT (structured `OK`, no timeout) but **blocks model/IMEI info queries**:
```
ATI / AT+GMM / AT+GSN / AT+CGSN  ->  +CME Error:PACM(AP),NOT_ALLOWED
```
`PACM(AP)` = the modem is under AP control and refuses those queries while booted. So you **cannot read model/IMEI over the modem port in normal mode**. Identify the unit via download-mode ODIN handshake or on-screen, not `ATI` on the booted modem port. Do not mistake the structured error for a dead port.

## Node-cycling to force an already-installed driver to bind
When the right driver is already in the store but an interface sits `Status: Unknown` (not bound), `pnputil` on this build has **no `/update-device`** — it's the slim verb set (`/add-driver /delete-driver /export-driver /enum-drivers /enum-devices /disable-device /enable-device /restart-device /remove-device /scan-devices`). Check `pnputil /?` before assuming `/update-device` exists. The reliable rebind is:
```powershell
pnputil /remove-device 'USB\VID_04E8&PID_6860&ADB\6&xxxxxxxx&0&0003'   # the exact instance id
pnputil /scan-devices
```
then Windows re-enumerates and auto-selects the best-match installed driver.

## Samsung ADB driver: use Samsung's, NOT Google's
The official Samsung `ssudadb.inf` (AndroidUsbDeviceClass, WHQL "Microsoft Windows Hardware Compatibility Publisher") is typically **already in the Dell's driver store**. Use it.
- Google's `android_winusb.inf` (google `usb_driver_r13`) does **not** carry the exact `USB\VID_04E8&PID_6860&ADB` node entries (it has Samsung entries in a different format), so it cannot bind this interface.
- `pnputil /add-driver android_winusb.inf` fails with `The publisher of an Authenticode(tm) signed catalog has not yet been established as trusted`, and still fails even after `certutil -f -addstore TrustedPublisher <cat>` — don't fight it. For Samsung ADB, match against the installed `ssudadb.inf` instead.

## ADB interface vanishing on rescan = USB debugging is OFF
A reset phone at the FRP gate (fresh factory reset) advertises the ADB interface only transiently; after `remove-device` + `scan-devices` the `&ADB` node **disappears** and `adb devices` is empty. Tell: the ADB function withdraws on re-enumeration. USB debugging defaults OFF after reset and can't be enabled through the FRP/login screen ⇒ **ADB is a dead end on an FRP-gated reset phone**. Route to download mode (685D) and the WinUSB/protocol or Octoplus path instead. Don't burn time installing ADB drivers for a phone that won't keep the interface up.

## Getting model/firmware when you can't read it off the bus
On a booted phone with unrestrictive setup this is easy over ADB (`adb shell getprop ro.product.model`), but at the FRP gate that's unavailable. Identify the unit from: (a) the phone's own About/screen, or (b) the download-mode (685D) ODIN handshake, or (c) the staged tooling directory contents (e.g. `probe_s24*.py` + `protocol.py` staged ⇒ S24 class).

## Session facts (context reference)
- Live device serial on the Dell this session: `R58W500YA5L`; a DIFFERENT serial (`R94Y507A8YJ`) appeared only as a ghost node from prior connections — serial changes are another ghost-vs-live sanity check.
- The `exynos/` staging dir on the Dell held `protocol.py`, `zadig.exe`, `winusb_685d.inf`, `winusb_install.exe`, `pit_dump.bin`, `probe_s24*.py`, `a54_watch_dell.py` ⇒ the download-mode WinUSB + custom Python protocol workflow is the established path there.