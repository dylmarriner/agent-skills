# Remote Samsung FRP unlock — exynos tool on a remote Windows box

Session reference (2026-08-22): A54 FRP unlock where the phone was plugged into a remote-site
Windows laptop (Dell, tailnet node `desktop-g188o69`), far from lin where the unlock tool lives.

## End-state that worked
1. SSH into the Windows box (OpenSSH, key auth — see main SKILL.md "Enabling Windows OpenSSH server").
2. Staged the exynos tool + Python libusb on the box (below).
3. Ran a persistent watcher as a scheduled task that auto-fired `--frp-lock` the moment the phone
   was seen in Download Mode, reporting each step to lin's HTTP server.

## Exynos tool staging on Windows
```bash
# from lin (tool lives at ~/Documents/universal-unlock-suite/backend/exploits/exynos/)
scp -r ~/Documents/universal-unlock-suite/backend/exploits/exynos "sbkha@<ip>:C:/Users/sbkha/exynos/"
```
On the Windows box (admin PowerShell):
```powershell
python -m pip install pyusb libusb libusb-package
# pyusb "No backend available" => DLL not found. Copy it into a searched dir:
copy C:\Python314\Lib\site-packages\libusb_package\libusb-1.0.dll C:\Python314\libusb-1.0.dll
copy C:\Python314\Lib\site-packages\libusb_package\libusb-1.0.dll C:\Windows\System32\libusb-1.0.dll
# verify backend + tool run:
python C:\Users\sbkha\exynos\protocol.py --detect   # "No Exynos device found" = backend OK
```
protocol.py imports only stdlib + pyusb, so it runs unmodified. The Dell was x86_64 — the DLL under
`libusb\_platform\windows\x86_64\` or `libusb_package\` is the right one.

## Detecting the phone on the box (not via tailnet ping)
The tailnet node `dylans-a54` staying online was NOT proof of the phone in hand — a second A54
(`galaxy-a54-5g`) existed on the mesh, and a phone in Download Mode has no network stack so it drops
off the tailnet. Use USB enumeration as ground truth:
```
wmic path win32_pnpentity where "DeviceID like '%%04E8%%'" get Name,DeviceID,Status
```
Download Mode enumerates as `04E8:685D`. Download Mode self-times-out after a few minutes back to
normal boot, so stage everything BEFORE asking the user to plug in.

## Auto-unlock watcher (persistent via scheduled task)
`Start-Process -WindowStyle Hidden python ...` over one-shot SSH did NOT stick. Scheduled task did:
```
schtasks /create /tn a54watch /tr "C:\Python314\python.exe C:\Users\sbkha\exynos\a54_watch_dell.py" /sc once /st 00:00 /f
schtasks /run /tn a54watch
```
watcher logic (a54_watch_dell.py): loop every 2s calling `usb.core.find(idVendor=0x04E8, idProduct=0x685D)`;
on hit, run `[python, protocol.py, --frp-lock, --reboot, --verbose]` via subprocess (120s timeout),
append stdout+stderr to `watch.log`, and `urllib.request.urlopen("http://<lin-ip>:<port>/report?m=...")`
each step. The 404s from lin's `python3 -m http.server` are expected — request still logs.

## Gotchas hit this session
- User "ran it" but nothing executed: browser-downloaded .ps1 was silently blocked by execution policy.
  Fix = `.cmd` wrapper with `-ExecutionPolicy Bypass -Command "irm <url>|iex"`, or `irm <url>|iex` directly.
- SSH one-liners with `; echo %ERRORLEVEL%` get mangled through ssh+cmd quoting — run bare.
- PowerShell `$_` mangled through bash/ssh quoting — use `wmic` for device queries.
- User typed `sshsetupup.ps1` (typo) and pasted error text back as commands. Minimize hand-typed steps;
  prefer download-and-double-click `.cmd` and phone-home reporting over asking for pasted output.
