# Remote / Cross-Site Samsung FRP Unlock

Situation: the phone is physically at a different site than the machine running the unlock tool.

## Core rule
The unlock tool talks to the phone over USB on the host that runs it — it cannot reach a phone through the network. Get the tool onto the phone's host (or the phone onto the tool's host). There is no network/USB-bridge path.

## Ground truth: USB, not Tailscale ping
- A download-mode phone drops off the tailnet, BUT Tailscale node presence is unreliable (multiple A54s, stale/offline states, wrong device in hand).
- NEVER use `tailscale ping` / `tailscale status` to confirm or deny physical device state.
- Confirm presence ONLY via `lsusb` (04e8:685d) and `sudo dmesg | grep -i usb` hotplug events since boot.
- (Dylan explicitly corrected this: "look at usb not ping".)

## Getting a shell on a remote Windows host (no password)
The Dell in question: `desktop-g188o69` (Windows, tailnet 100.104.200.49) — inbound only SMB(445)/RPC(135), no SSH/RDP/WinRM, no creds. Only open path is Tailscale SSH:
1. On the host, elevated PowerShell: `tailscale set --ssh` (older versions: `tailscale up --ssh`).
2. From lin: `tailscale ssh desktop-g188o69 "<cmd>"`.
3. Validate with a command that returns output. A silent/empty response (rc=0 with nothing back) means SSH is NOT actually enabled yet. "Tailscale up" (VPN running) ≠ SSH server enabled — they are separate switches.

## Once shelled in (Windows)
- Install Python + pyusb + libusb; bind the 04e8:685d device with Zadig so pyusb can claim it.
- Run the exynos `protocol.py --frp-lock` (data-safe settings reset) or `--frp-wipe` (factory reset) against the phone in download mode.

## Tooling note (lin)
`/tmp/usb_env` is wiped on reboot. Rebuild before use:
```bash
cd ~/Documents/universal-unlock-suite
python3 -m venv /tmp/usb_env
/tmp/usb_env/bin/pip install pyusb
sudo /tmp/usb_env/bin/python3 backend/exploits/exynos/protocol.py --detect
```
Flags present: `--detect --pit --frp-lock --frp-wipe --reboot --verbose`.
