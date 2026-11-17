# Worked example — locating an A54 phone on a Windows-host tailnet

Session: user asked to "check the phone on the laptop I used to ssh into lin on."

## What was found

1. **Source machine resolved from the live session env, not guessed:**
   - `SSH_CONNECTION=100.104.200.49 65145 100.91.55.113 22` → source IP 100.104.200.49
   - `who` showed `lin pts/1 2026-08-22 20:02 (100.104.200.49)` — the remote session.
   - `tailscale status | grep 100.104.200.49` → `desktop-g188o69` (Windows, user inhumanekiller22@, active; direct).

2. **Host port probe (Windows laptop):**
   ```
   port 22:   timed out     (no OpenSSH server reachable)
   port 3389: timed out     (no RDP)
   port 5985: timed out     (no WinRM)
   port 445:  succeeded     (SMB open)
   port 135:  succeeded     (RPC open)
   ```
   `smbclient -L //100.104.200.49 -N` → `NT_STATUS_ACCESS_DENIED` (no anonymous shares).
   `tailscale ssh desktop-g188o69` → `Dial(...): unexpected HTTP response: 502 Bad Gateway` (node does not run the tailscale sshd / port-65535 proxy absent).
   → No inbound shell route without Windows credentials. The USB/MTP state of the phone as seen by Windows is NOT visible from lin.

3. **Phone reached directly over the tailnet instead:**
   - `tailscale status | grep a54` → `dylans-a54` (Galaxy A54 5G, android, Online=True, TailscaleIPs 100.100.5.105).
   - `tailscale ping --c 3 dylans-a54` → pongs via `DERP(syd)` ~550ms, `direct connection not established` (online, relaying).
   - Port probe: 5555/5554/5037/8080/22 all `Connection refused` → no ADB-over-network, no SSH. Phone is alive on the mesh but exposes nothing to hook into.

## Outcome / next steps presented to the user
- Phone (A54) is confirmed online and mesh-reachable, but to inspect it you must either:
  1. Enable wireless debugging on the phone (Developer options → Wireless debugging, or `adb tcpip 5555` from a PC), then `adb connect 100.100.5.105:5555` from lin; or
  2. Provide Windows credentials / enable OpenSSH server on `desktop-g188o69` to check the USB device from the host side.

## Reusable commands
```bash
# resolve SSH source
echo "$SSH_CONNECTION"                      # field 1 = source IP
tailscale status | grep <src-ip>
tailscale status --json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(v.get('HostName'), v.get('OS'), v.get('Online'), k) for k,v in d.get('Peer',{}).items() if <cond>]"

# host probe
for p in 22 3389 5985 445 135; do timeout 3 nc -zvw2 <ip> $p 2>&1; done

# phone probe
for p in 5555 5554 5037 8080 22; do timeout 3 nc -zvw2 <ip> $p 2>&1; done
adb connect <ip>:5555
```
