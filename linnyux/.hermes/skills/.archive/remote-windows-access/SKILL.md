---
name: remote-windows-access
description: Use when you need a shell on a remote Windows node.
---
# Remote Windows Access (from Linux over Tailscale)

## When to use
- You need a shell on a remote Windows node (laptop/desktop on the tailnet) and cannot get into it.
- User says the target is Windows, or `tailscale status` shows OS `windows`.
- A USB device is plugged into a remote Windows box and you must run host-side tooling on it (e.g. Samsung download-mode unlock) — the tool must run ON that machine, USB cannot cross the network.

## Core fact: Tailscale SSH is NOT supported on Windows
Running `tailscale set --ssh` / `tailscale up --ssh` on a Windows node returns:
```
The Tailscale SSH server is not supported on windows
```
and `tailscale ssh <win-node>` hangs or returns rc=0 with no output. Do not waste time on `tailscale ssh` for Windows nodes. Fall back to the built-in Windows OpenSSH server.

## Step 1 — Confirm reachability (baseline probe)
Before debugging sshd, verify the node is reachable at all:
```bash
tailscale status | grep <node>          # must show "active", not offline
nc -zvw3 <ip> 445                       # SMB is the canary on Windows
nc -zvw3 <ip> 22                        # sshd
nc -zvw3 <ip> 3389 5985 5986            # RDP / WinRM fallbacks
```
If 445 succeeds but 22 times out, routing is fine — the problem is sshd/firewall on the box, not the network. If 445 also fails, fix tailnet reachability first.

## Step 2 — Enable OpenSSH on the remote box (user-at-keyboard one-shot)
When the agent has no route in, the user runs a one-shot setup on the box (admin PowerShell). Key facts:
- **Admin key location:** `C:\ProgramData\ssh\administrators_authorized_keys` — NOT the user `~/.ssh/authorized_keys`. Then fix ACLs:
  `icacls <file> /inheritance:r /grant "SYSTEM:F" /grant "Administrators:F"`
- Install/start/firewall:
  ```
  Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
  Start-Service sshd
  Set-Service sshd -StartupType Automatic
  New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -Profile Any
  Restart-Service sshd
  Get-NetTCPConnection -LocalPort 22 -State Listen   # must show a 22 row
  ```

## Step 3 — Delivery: bypass the execution-policy trap
- Right-click **"Run with PowerShell" on a downloaded `.ps1` is silently blocked** (nothing runs, no error). Execution policy refuses it.
- `irm <url> | iex` bypasses policy but requires clean command entry — fragile with an error-prone user.
- **Zero-typing path = a `.cmd` wrapper.** Serve a `.cmd` containing:
  ```
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://<lin-tailnet-ip>:8123/setup.ps1 | iex"
  ```
  `.cmd` is NOT policy-blocked. User right-clicks the downloaded file → Run as administrator. No typing.
- Serve the files from lin: `python3 -m http.server 8123 --bind 0.0.0.0` in the dir holding them. Note: binding may collide with an orphaned server on the same port — `fuser -k <port>/tcp` then restart on a fresh port if it 404s from a stale root.

## Step 4 — Phone-home verification (don't trust pasted output)
Have the remote script GET a URL on the lin HTTP server so you can confirm execution yourself:
```
irm "http://<lin-tailnet-ip>:8123/report?m=<status-token>"
```
The 404 hits still land in the server request log. `process(action='log')` the background server and grep for the `m=` report hits. This is far more reliable than asking the user to paste output (which they often mangle or skip).

## Pitfalls
- **Relaying commands to a non-technical/error-prone user is fragile**: pasted error text gets re-entered as commands, dashes get mangled (`Get=Service` → `=`), filenames typo'd (`sshsetupup.ps1`). Minimize typing to a single paste; prefer download-and-click (Run as administrator).
- **Admin key must be in administrators_authorized_keys** — putting it in a user `.ssh/authorized_keys` won't grant admin access.
- **Confirm sshd from the agent side** with `nc -zvw3 <ip> 22` before trying `ssh <user>@<ip>` — a "connected" but silent result usually means the service isn't actually accepting.
- **USB devices don't cross the network.** If a phone/tool needs to run on the machine the device is plugged into (Samsung download mode, MTP enumeration), the tooling must be installed and run on THAT machine — you cannot drive a remote USB device from lin.

## Related diagnostic
Samsung Download Mode tailnet tell: a phone in download mode has no network stack, so it drops off the tailnet and stops answering `tailscale ping`. If the target phone is still present on the tailnet, it is booted normally — not in download mode. Tailnet presence is the reliable remote way to confirm a phone is (or isn't) in download mode.
