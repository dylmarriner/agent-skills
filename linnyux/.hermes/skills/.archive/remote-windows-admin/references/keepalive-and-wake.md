# Keep a remote Windows box always reachable — full working recipe

Proven pattern for a remote-site Windows node (e.g. a Dell laptop on a different
LAN than the controlling host) that keeps dropping off the tailnet because it
sleeps or is left idle. Three layers, all running on the controlling Linux host
plus one run-once config push to the Windows box.

Goal: the moment the Windows node re-appears on the tailnet, auto-push the
never-sleep config, ensure the target service (e.g. a mic-stream server) is
running, and notify. Also captures the MAC for wake-on-LAN.

## Layer 1 — cron watcher (controlling host) `dell_watch.sh`
Runs every minute. Cheap while the node is down; only acts on state *transitions*.
```bash
#!/usr/bin/env bash
DELL_IP="100.104.200.49"
STATE="/home/lin/.dell_watch.state"   # holds last known online/offline
LOG="/home/lin/.dell_watch.log"
log(){ echo "$(date '+%F %T %Z')  $*" >> "$LOG"; }

line=$(tailscale status 2>/dev/null | grep -E "^${DELL_IP}[[:space:]]")
# Online nodes show "idle;"/"active;" and NOT the word "offline".
if [[ "$line" == *"offline"* || -z "$line" ]]; then is_online=0; else is_online=1; fi

last=offline; [[ -f "$STATE" ]] && last=$(cat "$STATE")

if (( is_online )); then
  [[ "$last" != "online" ]] && { log "ONLINE transition"; echo "online" > "$STATE";
    nohup /home/lin/dell_connect.sh >/dev/null 2>&1 & }   # fire connect, return fast
else
  echo "offline" > "$STATE"
  [[ "$last" == "online" ]] && log "OFFLINE transition"
fi
```
cron: `* * * * * /home/lin/dell_watch.sh >> /home/lin/.dell_watch.log 2>&1`

## Layer 2 — connect chain (controlling host) `dell_connect.sh`
Waits for SSH, pushes + runs the config ps1, ensures service up, notifies.
Key parts:
- Wait for SSH with a bounded retry loop (boot can take 30-120s after the node pings).
- `scp` the ps1, then run via `powershell -NoProfile -ExecutionPolicy Bypass -File`.
- Capture the MAC for WOL from a `netinfo.txt` the ps1 writes.
- Kick the target service with base64 `-EncodedCommand` (UTF-16LE), see SKILL.md.
- Verify reachability from the controlling side, then Telegram-notify.

## Layer 3 — config push (Windows box) `dell_always_connect.ps1`
Runs elevated once (via the SSH session, which on this box is High IL so
netsh/powercfg fire without UAC). Contents: powercfg sleep/lid off (see
SKILL.md), `sc.exe config`/`sc.exe failure` for sshd+Tailscale, the SYSTEM
startup watchdog scheduled task, and WOL enable + MAC capture.

### Why the SYSTEM watchdog task (not just the service)
Services can still die on driver churn / reboots / power events. A SYSTEM
`while($true)` loop at startup that checks the listen port every 60s and
`Restart-Service` / `Start-Process` anything dead survives all of it — and
`-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries` stops Windows from
skipping it on a laptop running on battery.

## Telegram notify (controlling host)
```bash
curl -s -m 10 "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  --data-urlencode "chat_id=<CHAT_ID>" --data-urlencode "text=<msg>" >/dev/null
```

## Wake script `dell_wake.sh`
Reads MAC from `/home/lin/.dell_wol/mac` (written by the connect chain), checks
the node isn't already online, then `wakeonlan <MAC>`. **Hard limit:** only works
if the controlling host has L2 reach to the node's subnet — a magic packet cannot
cross the tailnet to a hard-powered-off remote NIC. Say so rather than pretending
it will work.

## Session-specific deploy state (Dell desktop-g188o69)
- Node: `DESKTOP-G188O69`, 100.104.200.49, tailscale relay "syd", remote site.
- SSH user `sbkha`; Windows OpenSSH, session ELEVATED (High IL) so firewall rules
  apply without UAC.
- Watcher/connect/wake scripts live at `/home/lin/dell_watch.sh`,
  `/home/lin/dell_connect.sh`, `/home/lin/dell_wake.sh`; config ps1 at
  `/home/lin/dell_always_connect.ps1`. State/log `~/.dell_watch.*`.
- Keeper task name `DellAlwaysConnect`; WOL MAC landed in
  `C:\Users\sbkha\micstream\netinfo.txt` → `/home/lin/.dell_wol/mac`.