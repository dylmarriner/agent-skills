# Assessing a remote tailnet node that is offline

Worked from the desktop-g188o69 (Dell, Windows, 100.104.200.49) session: user asked
to start a service / asked "how long was it on", but the node was already offline.

## Don't guess uptime — bracket the drop from tailnet metadata

When the box is down you cannot read its live uptime. Give the user a precise,
evidence-backed answer instead of inventing a number. Two sources:

```bash
# 1. Authoritative drop timing (UTC timestamps, convert to local):
tailscale status --json | python3 -c "import json,sys; d=json.load(sys.stdin); \
print([{ 'HostName':p.get('HostName'), 'Online':p.get('Online'), \
'LastSeen':p.get('LastSeen'), 'LastWrite':p.get('LastWrite')} \
for p in d.get('Peer',{}).values() if '<hostname>' in p.get('HostName','')])"

# 2. Human line (cross-check): 
tailscale status | grep -i '<hostname>'
#   -> "idle; offline, last seen 5m ago, tx ..."
```

Field meanings per peer:
- `LastSeen` — last time the control plane saw it reachable.
- `LastWrite` — last time it sent a packet / updated (best "when it last talked" anchor).
- `Online: false` + a "last seen Xm ago" that's independent of when you checked =
  the node sleeps/drops between uses, NOT a crash. Treat "it was online earlier"
  with suspicion as a boot anchor.

## The one legitimate boot bookend

The only evidence-backed "when it was last rebooted" anchor is a reboot / boot you
personally performed via a session. If you never captured a boot timestamp, and no
`systeminfo` / `LastBootUpTime` was ever read, say so — don't reconstruct one.

Real uptime is only readable live:
```bash
ssh <user>@<ip> "powershell -NoProfile -Command \"(Get-Date)-(Get-CimInstance Win32_OperatingSystem).LastBootUpTime\""
```
Returns a TimeSpan (seconds since boot). There is no remote way to get it from an
offline node.

## Standard probe set to confirm a node is truly down

```bash
curl -s -m 5 -o /dev/null -w "direct: HTTP %{http_code}\n" http://<ip>:<app-port>/   # any app port
ping -c 3 -W 2 <ip>                              # direct
tailscale ping --timeout=3s <hostname>           # over mesh
for p in 22 445 3389 5985; do nc -zvw3 <ip> $p 2>&1; done
# SSH timeout (rc=255) + direct ping 100% loss + no tailscale reply = box is off/asleep
```
Correlate all of them before saying "offline" — one closed port or one failed ping is
not enough.

## Pitfall: the 8123 phone-home http.server has no durable log

`python3 -m http.server 8123` used for Dell phone-home (`irm .../report?m=`) writes
requests only to its own stdout pipe — nothing is persisted to disk. You cannot
reconstruct a check-in *history* from disk afterward. `process(action='log')` works
only while that server process is live. For a durable trail, run a server that appends
to a log file internally; do not rely on the stdlib server's ephemeral stdout for
provenance after the fact.