---
name: remote-windows-admin
description: Remotely admin a Windows box over Tailscale/SSH via OpenSSH.
---

# Remote Windows Administration

## When to use
You need a shell on a Windows machine — typically a remote-site node on the Tailnet — to run tooling, inspect USB/PnP devices, or drive an unlock/repair. The device (phone, dongle) is physically plugged into that Windows box; the tooling you control lives on another host.

## Key fact: Tailscale SSH does NOT work on Windows
`tailscale set --ssh` on a Windows node prints: **"The Tailscale SSH server is not supported on windows"**. Do not fight it. Tailscale SSH works on Linux nodes only. For a Windows node, enable Windows' built-in OpenSSH server instead.

## Enabling Windows OpenSSH server (once, from an admin PowerShell on the box)
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
# key auth for the Administrators group:
$key='ssh-ed25519 AAAA... your@host'
Set-Content -Path 'C:\ProgramData\ssh\administrators_authorized_keys' -Value $key -Encoding ascii
icacls 'C:\ProgramData\ssh\administrators_authorized_keys' /inheritance:r /grant "SYSTEM:F" /grant "Administrators:F"
# firewall — CRITICAL, Windows blocks 22 inbound by default:
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -Profile Any
Restart-Service sshd
```
Then from your side: `ssh <winuser>@<ip>` with your key. **You still need the exact Windows username** — ask the user (login-screen/Start-menu name, minus the `@...` for a Microsoft account). Guessing fails; `Administrator` may be disabled or lock out.

## Execution-policy trap: a downloaded .ps1 won't run
A `.ps1` downloaded in a browser and run via right-click → "Run with PowerShell" is **silently blocked** by execution policy (no error — the listener just never comes up; verify with `nc -zvw3 <ip> 22`). Bypass it with a `.cmd` wrapper, which execution policy does not apply to:
```cmd
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://<yourhost>:<port>/setup.ps1 | iex"
pause
```
User downloads the `.cmd`, right-click → **Run as administrator**. Equivalently `irm <url> | iex` in an admin PowerShell (must still be typed/pasted correctly).

## Verify remotely: phone-home pattern
Do NOT rely on the remote user pasting output — they routinely paste error text back, mis-type the filename, or run a key line as a command. Make the remote script report to an HTTP server you control:
```powershell
Invoke-WebRequest -UseBasicParsing -Uri ("http://<lin-ip>:<port>/report?m=" + [uri]::EscapeDataString($msg)) -TimeoutSec 10 | Out-Null
```
Serve files and capture the request log with `python3 -m http.server <port> --bind 0.0.0.0` (run background). The 404s in the log are fine — the request still lands and is logged. This gives ground truth of what actually ran and what errored, without trusting hand-relayed output.

## Persistent background process on Windows over SSH
`Start-Process -WindowStyle Hidden python ...` over a one-shot SSH often does NOT stick. Use a scheduled task (runs in the Services session, survives):
```
schtasks /create /tn <name> /tr "<python> <script>" /sc once /st 00:00 /f
schtasks /run /tn <name>
```
Confirm with `tasklist | findstr /i python`.

**"Started" is not persistence.** A kick that logs `*_STARTED` (or a one-shot
`schtasks /run`) proves the command ran once — nothing more. Before you claim a
remote background process is durable, read back the box: confirm the process
exists via a command-line match, confirm the restart/watchdog path (SYSTEM
scheduled task or the connect chain) is actually registered, and — for a
control-host receiver — confirm a real systemd unit is `enable`d, not just that
the port is listening (a bare `nohup python3` dies on the control host's reboot
with nothing to restart it). See the keystroke reference below for the full
ground-truth check sequence.

For a **self-healing keeper that survives reboot, lock, and software restarts**, register a watchdog loop as a SYSTEM scheduled task at startup, so it never depends on a logged-in user:
```powershell
$act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"C:\path\watchdog.ps1`""
$trg = New-ScheduledTaskTrigger -AtStartup
$pr  = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'KeepAlive' -Action $act -Trigger $trg -Principal $pr -Settings $set -Force | Out-Null
```
The watchdog script itself is an infinite `while($true)` loop that every 60s checks a listen port (`Get-NetTCPConnection -LocalPort <port> -State Listen`) and restarts the service / app if it died. `-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries` keeps it alive on a laptop on battery — the default behaviour of NOT running on battery is why many watchdogs silently never fire.

## Multi-line PowerShell over SSH: base64-EncodedCommand (quoting-proof)
Do NOT pass a multi-line PS one-liner with nested quotes through `ssh "bash"` — it gets mangled. Encode it instead; the remote runs it verbatim, quoting immune:
```bash
ps='$l = Get-NetTCPConnection -LocalPort 8124 -State Listen; if (-not $l) { Start-Process pythonw.exe ... } else { "ALREADY_RUNNING" }'
b64=$(printf '%s' "$ps" | iconv -f UTF-8 -t UTF-16LE | base64 -w0)
ssh winuser@ip "powershell -NoProfile -EncodedCommand ${b64}"
```
`-EncodedCommand` needs **UTF-16LE** base64 (hence the `iconv`). This is the reliable way to run any conditional/multi-statement PS remotely with zero quoting pain. Same trick works for setting a var then branching.

## Keep a remote Windows node always reachable (lock/asleep/off)
When a box keeps dropping off the tailnet the real cause is usually **sleep** — the NIC + Tailscale die with it, so nothing can reach it, and it looks like "offline, last seen Xm ago." A lock screen does NOT matter (sshd + your server are background services, untouched by the lock). The fixes:

1. **Disable sleep/hibernate + lid-close action** (a laptop drops off when its lid closes):
   ```
   powercfg -change -standby-timeout-ac 0
   powercfg -change -standby-timeout-dc 0
   powercfg -change -hibernate-timeout-ac 0
   powercfg -change -monitor-timeout-ac 0
   powercfg -change -monitor-timeout-dc 0
   powercfg /hibernate off
   powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
   powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
   powercfg /setactive SCHEME_CURRENT
   ```
2. **Pin sshd + Tailscale to Automatic with restart-on-fail**:
   ```
   sc.exe config sshd start= auto
   sc.exe config Tailscale start= auto
   sc.exe failure sshd reset= 60 actions= restart/5000/restart/10000/restart/30000
   ```
3. **Auto-reconnect from the control host** — a cron watcher on the controlling Linux host that polls the tailnet and fires a connect chain only on the offline→online *transition* (state file prevents log spam and repeat actions). See `references/keepalive-and-wake.md` for the full working cron→watch→connect recipe and `scripts/dell_watch.sh`-style pattern.

## Capturing keystrokes from a remote Windows box
To monitor keystrokes on the remote Windows box and stream them back to a logfile on the controlling host, see `references/windows-keystroke-monitoring.md` — a systemd-managed HTTP ingest server on the control host plus a pure-ctypes `WH_KEYBOARD_LL` keylogger (no DLL injection) on the Windows box, deployed and self-healed by the same connect/watchdog chain above. Includes the source-level hook API, character/shift/caps rendering tables, the integrity-level boundary (LL hooks can't see higher-IL/UAC input unless the logger runs elevated), and the F12 local kill switch.

## Wake-on-LAN reality (hard power-off)
A magic packet must cross the **same L2 subnet** as the asleep NIC. If the box is at a REMOTE site (tailscale relay) with no controlling node on its LAN, lin cannot wake a hard-powered-off box — WOL simply cannot transit the tailnet to a cold NIC. Be explicit about this; the best you can do remotely is prevent sleep (above) and enable WOL for the on-LAN-forwarder / future-L2 case:
```powershell
Get-NetAdapter -Physical | % {
  Set-NetAdapterPowerManagement -Name $_.Name -WakeOnMagicPacket Enabled
  Add-Content C:\path\netinfo.txt ("$($_.Name)`t$($_.MacAddress)")
}
```
Capture the MAC while it's online so a `wakeonlan <MAC>` can fire when L2 reach exists.

## Inspecting USB / PnP devices over SSH
Avoid PowerShell `$_` — it gets mangled by the shell through `ssh`/bash quoting. Use `wmic`:
```
wmic path win32_pnpentity where "DeviceID like '%%04E8%%'" get Name,DeviceID,Status
```
`%%` = literal `%` through cmd. Returns "No Instance(s) Available." when the device is absent.

## Pitfalls
- **Parsing `tailscale status` for online/offline**: the node-line field 3 is the **owner username**, not the state. Don't `awk '{print $3}'` and read it as status. Grep the node's line for the word `offline` instead: `tailscale status | grep -E "^<ip>[[:space:]]"` → online unless that line contains `offline` (online nodes show `idle;`/`active;`).
- **Guessing the Windows username** wastes turns and can trip lockouts. Ask up front.
- Command strings with `;` + `echo %ERRORLEVEL%` get mangled through ssh+cmd quoting — run commands bare, one per ssh call.
- A service can be installed but still unreachable: test with `nc -zvw3 <ip> 22` before assuming SSH is up.
- If SMB(445) is reachable but 22 is not, it is a **Windows firewall/service issue on the box**, not a tailnet routing problem — the tailnet path is fine.
- When a phone is in Samsung Download Mode it drops off the Tailnet (no network stack) — but treat **USB enumeration** (e.g. `04E8:685D`) as the source of truth for "is it in download mode on this box", not a tailnet ping (multiple same-model phones can be on the mesh).

## See also
- `exynos-download-mode` (mobile) — running the Samsung FRP/unlock tool on a remote Windows box (pyusb/libusb setup, watcher script).
