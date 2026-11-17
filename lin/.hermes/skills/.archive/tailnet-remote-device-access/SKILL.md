---
name: tailnet-remote-device-access
description: "Locate a phone on the tailnet whose host is unreachable."
---

# Tailnet Remote Device Access

Reach a phone/device across a Tailscale mesh from a node that is NOT where the device is physically attached. Use when a user says things like "check the phone on the laptop I SSH'd into lin on", "the machine I came from", or "is device X reachable" — and the target host has no inbound SSH/RDP/WinRM.

## When to Use

- User names a device (phone, laptop) that is attached to or accessed via a machine you can reach on the tailnet but can't shell into
- User asks "which machine did I come from" / "the laptop I SSH'd from"
- You need to inspect a phone that is plugged into a remote host you cannot log into

## Workflow

### 1. Identify the source machine (don't guess)

```bash
echo "SSH_CONNECTION=$SSH_CONNECTION SSH_CLIENT=$SSH_CLIENT"   # <src-ip> <src-port> <dst-ip> 22
who                                                          # pts lines show remote FROM
tailscale status | grep <src-ip>                             # src-ip -> hostname + OS
tailscale status --json | python3 -c "..."                   # richer: HostName, OS, Online, LastSeen
```

- `$SSH_CONNECTION` field 1 is the live session's source IP. A `who`/`last` line with a non-`:0` FROM is a remote SSH session.
- `tailscale status` maps the IP to hostname + OS. A node with no `offline, last seen` marker is currently online.

### 2. Probe the host's reachability before assuming you can get in

```bash
for p in 22 3389 5985 445 135; do timeout 3 nc -zvw2 <ip> $p 2>&1; done
```

Windows nodes on a tailnet commonly expose ONLY SMB (445) and RPC (135), with SSH (22), RDP (3389), and WinRM (5985) firewalled off — even between trusted tailnet peers. If only SMB/RPC are open and you have no Windows credentials, treat the host as unreachable for shell access. Anonymous `smbclient -L` will return `NT_STATUS_ACCESS_DENIED`.

### 3. Reach the device itself over the tailnet

If the target is a phone, check whether IT is on the tailnet — phones usually self-register on the mesh and are probe-able independently of the host they're plugged into:

```bash
tailscale status | grep -iE "android|a54|phone|galaxy"      # phones often self-register
timeout 10 tailscale ping --c 3 <hostname>                  # ICMP over tailnet (often via DERP relay)
for p in 5555 5554 5037 8080 22; do nc -zvw2 <ip> $p 2>&1; done   # ADB-over-net is 5555
adb connect <ip>:5555
```

## Key Facts

- **Android phones answer ICMP ping over the tailnet even when exposing NO service ports.** A phone that pings but refuses 5555/5037/5554 has wireless debugging (ADB over network) NOT enabled. To inspect it remotely the user must enable Developer options → Wireless debugging (or `adb tcpip 5555` from a connected PC), then `adb connect <ip>:5555`.
- **You cannot enumerate the USB/MTP state of a phone from a remote node.** The USB device is only visible to the OS it's physically attached to. Check the phone over the mesh, or get credentials/SSH into the host.
- `tailscale ping` answering via `DERP(syd)` with `direct connection not established` = the device is online but relaying (slow, ~500ms+) — still usable for probes.
- `tailscale ssh` to a node without the tailscale sshd gives `Dial(...): unexpected HTTP response: 502 Bad Gateway` — that's the absent port-65535 SSH proxy, not a transient error. Fall back to probing TCP ports.

## Pitfalls

- Don't conclude "device not reachable" from one closed port — probe the full set (5555/5037 for ADB, 22/3389/5985 for host shell).
- Don't assume a Windows tailnet node accepts inbound SSH just because you're on the same tailnet — its firewall rules still apply.
- Reporting a host as unreachable is only valid after checking SMB/RPC AND confirming no credentials/SSH route — if SMB is open but anon-denied, say "reachable via SMB, needs creds" rather than "no access".

## References

- `references/a54-windows-laptop-session.md` — worked example: locating `dylans-a54` on a tailnet where the host laptop (`desktop-g188o69`, Windows) had only SMB/RPC open.

Overlaps with the user-owned `devops/tailscale` skill (SSH troubleshooting, SMB fallback) — this skill focuses specifically on device/phone location and reachability.
