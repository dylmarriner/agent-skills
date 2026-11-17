# Expose a local port on Windows to the tailnet + set audio volume remotely

Session-derived detail for the common case: you deployed a small HTTP listener on a
remote Windows box (e.g. a mic/audio streamer) and need (a) the phone / other
tailnet nodes to reach it, and (b) to mute the box's own speakers so the mic doesn't
feedback.

## A. Punch a local port through Windows netfilter with `tailscale serve`

Symptom: the service works when you curl it **from the box itself** (via its own
tailnet IP), but a remote node on the same tailnet gets `RC=28` (timeout). SSH (22)
works but your port (e.g. 8124) does not.

Root cause: Tailscale's Windows **NetfilterMode** (CLI NV netfilter mode, value 2 =
on) whitelists only Tailscale's own service ports (HTTPS 443, etc.) for inbound.
Arbitrary host ports are blocked by the netfilter, so a raw `:8124` listener is
invisible to other tailnet nodes even though localhost / the box's own tailnet IP
can reach it.

Confirm:
```powershell
tailscale debug prefs | Select-String netfilter   # "NetfilterMode": 2
```

Fix — proxy the listener onto the tailnet's whitelisted HTTPS (443) with `tailscale
serve`. No firewall rule, no netfilter edit; serve terminates the tailnet-side
HTTPS and proxies to your local port:
```powershell
# serves https://<host>.tailXXXX.ts.net/ -> http://127.0.0.1:8124  (tailnet only)
tailscale serve --bg --https=443 http://127.0.0.1:8124
tailscale serve status
```
Result: reachable from any tailnet node at `https://<host>.<tailnet>.ts.net/` —
browser and `curl -sk` both work. This is the same reachability as SSH without
touching the firewall.

Notes / pitfalls:
- Tailnet-only by default. Do **NOT** use `--funnel` for anything you don't want
  public on the internet: Funnel serves to the open web. For an audio/mic stream
  that's a privacy leak.
- `tailscale serve --https=443 <port>... off` tears it down.
- Verify with `curl -sk https://<host>.<tailnet>.ts.net/status` from your own node
  and confirm a real streamed artifact (mp3 bytes, HTTP 200 body) — `ffprobe` the
  pulled bytes to prove audio, not just that the page loads.
- If the page loads from your node but not the user's **phone** on the same tailnet,
  the suspect is the phone's MagicDNS / MobileVPN toggle, not the serve config —
  `tailscale status` on your side showing the phone node `active` narrows it.

## B. Set/master-mute the box's own volume from an SSH-only controller

You want the Windows speakers at 0 so the mic stream doesn't feed back through them.
This is NOT reachable through ordinary COM/registry from a raw SSH shell, because:

- `ssh powershell` / `schtasks` without `/it` runs in the **Services session (0)**,
  which has no audio endpoints. COM `IAudioEndpointVolume` then fails with
  `hr=0x80070057 (E_INVALIDARG)` on `GetDefaultAudioEndpoint`, and `nircmd`
  `setsysvolume`/`getsysvolume` silently produce no output / never write.
- The whole problem is session-context, not the API: the *interactive* user session
  (usually session 1) is where the real render endpoint lives.

Diagnose first: `query session` / `quser` on the box. You'll see `console  sbkha  1 Active` —
the interactive session is 1.

### Option 1 (reliable): the winmm P/Invoke fallback — no COM, no session token
```powershell
Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class V{
  [DllImport("winmm.dll")] public static extern uint waveOutGetVolume(IntPtr h,out uint v);
  [DllImport("winmm.dll")] public static extern uint waveOutSetVolume(IntPtr h,uint v);
}
'@
$v=0; [V]::waveOutGetVolume([IntPtr]::Zero,[ref]$v)   # read: word pair L<<0 | R<<16
[V]::waveOutSetVolume([IntPtr]::Zero,0)               # zero BOTH channels
[V]::waveOutGetVolume([IntPtr]::Zero,[ref]$v)         # verify == 0x00000000
```
This targets the default wave-out render device directly — works from any session,
no Core Audio COM, no elevation, no scheduled task. `waveOutGetVolume` returning
`raw=0x00000000 left=0 right=0` is ground truth the speakers are muted. Confirmed on
a Windows 11 (26200) box where Core Audio COM and nircmd both failed.

### Option 2 (when winmm isn't enough): force a task into the interactive session
nircmd from a plain SSH shell prints nothing. To land a command in the real audio
session, create the scheduled task with the **user** and **`/it`** (interactive token):
```cmd
schtasks /create /tn svo /tr "cmd /c C:\...\nircmd.exe setsysvolume 0 && C:\...\nircmd.exe mutesysvolume 1 && echo done> C:\...\log" /sc once /st 23:59 /ru sbkha /it /rl highest /f
schtasks /run /tn svo
```
Task `Last Result: 0` + `tasklist` showing `nircmd.exe ... Console 1` means it ran in
the interactive session. Pitfall: a trailing `getsysvolume > file` in the same chain
can hang and hold the log handle (`The process cannot access the file because it is
being used by another process`) — put read-backs in a **separate** later command or
use winmm (Option 1) to verify instead.

### Iron rules for the Core Audio COM route (if you must)
- `Activator.CreateInstance([MMDeviceEnumeratorComObject])` then casting in PS fails:
  use `(IMMDeviceEnumerator)(object)new MMDeviceEnumeratorComObject()` from Add-Type C#.
- Interface IIDs are easy to swap: `IMMDeviceEnumerator = {A95664D2-9614-4F35-A746-DE8DB63617E6}`,
  `IMMDevice = {D666063F-1587-4E43-81F1-B948E807363F}`, `IAudioEndpointVolume = {5CDF2C82-841E-4546-9722-0CF74078229A}`.
- Add `[PreserveSig]`, `[Out, MarshalAs(UnmanagedType.R4)] out float`, `[MarshalAs(UnmanagedType.Bool)]`,
  pass `CLSCTX_ALL = 23` to `Activate` — missing these yields E_INVALIDARG / IDispatch
  param errors even when the IID is right. And it still only works in session 1.
- Bottom line: prefer winmm. It's 4 lines, session-agnostic, and verifiable.

## Stealth cleanup pattern
The remote controller left behind scheduled tasks, nircmd.exe, helper .ps1/.cmd, and
logs. After the box's own log confirms completion, scrub them:
```cmd
schtasks /delete /tn <each> /f
del /Q C:\Users\<u>\<dir>\nircmd.exe *.ps1 *.cmd *.log
```
Leave only the actual service artifact (e.g. `micstream.py` + its logs). Confirm no
stray helper processes: `tasklist | findstr /i nircmd` should be empty.