---
name: intel-gpu-troubleshooting
description: Diagnose and fix Intel GPU (i915) issues on Linux — black screen lockups from Panel Self Refresh (PSR), backlight problems, GPU hangs on Kaby Lake / UHD Graphics / hybrid graphics laptops. Use when screen goes black and hard power-off is required, or display doesn't wake from idle.
version: 1.0.0
---

# Intel GPU Troubleshooting

Diagnose and fix common Intel integrated GPU (i915) issues on Linux. Covers the well-known Panel Self Refresh (PSR) black-screen lockup that affects HP Pavilion, Dell XPS, and ThinkPad laptops with Kaby Lake/Whiskey Lake/Comet Lake UHD Graphics.

## Trigger Conditions

- Screen goes black during idle/low-power use, requires hard power-off (hold button)
- TTY switching (Ctrl+Alt+F2) also fails — display pipeline frozen at kernel level
- No GPU crashes or kernel panics in dmesg/journalctl — system is still running, just display is dead
- Laptop has Intel integrated graphics (no AMD, no external NVIDIA/AMD display)
- Hybrid graphics laptop (Intel + NVIDIA/AMD) where Intel drives the internal display
- Display works after cold reboot but fails after idle/suspend

## Diagnostic Checks

### Step 1: Identify GPU hardware

```bash
lspci -nn | grep -iE 'vga|3d|display'
```

Look for `Intel Corporation UHD Graphics 6xx [8086:xxxx]` or similar.

### Step 2: Check i915 PSR status

```bash
sudo cat /sys/module/i915/parameters/enable_psr
```

- `-1` = hardware/firmware default (PSR likely enabled on most laptops)
- `1` = PSR forced on
- `0` = PSR disabled (the fix)

### Step 3: Check current kernel boot parameters

```bash
cat /proc/cmdline
```

Look for `i915.enable_psr=0` — if absent, PSR is active.

### Step 4: Verify no other crash evidence

```bash
sudo journalctl -k --no-pager | grep -iE 'oom|hung_task|lockup|panic|fatal' | tail -10
```

If nothing shows up but the user describes black screen + hard power-off, it's almost certainly i915 PSR.

## The Fix: Disable Panel Self Refresh

PSR (Panel Self Refresh) lets the display panel refresh from its own internal buffer while the GPU sleeps. On many Intel Kaby Lake / UHD 620+ laptops, the panel never wakes up after PSR entry, leaving the screen permanently black while the system continues running (you can SSH in, audio plays, etc.).

### Add kernel boot parameter

```bash
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="[^"]*/& i915.enable_psr=0/' /etc/default/grub
sudo update-grub
```

This appends `i915.enable_psr=0` to the existing kernel parameters.

### Verify

```bash
grep 'GRUB_CMDLINE_LINUX_DEFAULT' /etc/default/grub
```

### Requires reboot

The change takes effect on next boot.

## Pitfalls

1. **PSR issue doesn't show in any log** — The panel entering PSR and never waking isn't a crash or error. The i915 driver considers it a successful power transition. No kernel message, no panic, no OOM. The only symptom is "screen went black, hard power-off fixed it."

2. **TTY switching fails during PSR black screen** — The entire display pipeline (CRTC, encoder, eDP panel) is locked in PSR state. The GPU itself doesn't respond to modeset requests. This is different from a display server crash (where TTY switching still works).

3. **Already applied mitigations indicate PSR is the culprit** — If the user already has `processor.max_cstate=1`, `intel_idle.max_cstate=1`, or `nowatchdog` in kernel params from previous power-management fixes, PSR is very likely still enabled and causing the black screen. Those c-state limits reduce CPU idle depth but don't affect GPU PSR.

4. **Only affects internal eDP panel** — External displays (HDMI, DisplayPort) connected to the Intel GPU are not affected by PSR. If only the internal laptop panel goes black while an external monitor stays on, it's PSR.

5. **PSR fix costs negligible power** — Disabling PSR means the panel refreshes from the GPU at all times instead of from its internal buffer. The difference is <0.5W on battery — not noticeable in practice.

