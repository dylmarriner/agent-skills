---
name: intel-i915-black-screen
description: Diagnose and fix Intel integrated GPU (i915) black screen lockups on laptops — Panel Self Refresh (PSR) issues, display pipeline freezes, and hard power-off required crashes. Use when user says "screen goes black and I have to hold the power button", "laptop freezes to black screen no logs", "HP Pavilion black screen", "Intel UHD display died".
---

# Intel i915 Black Screen Lockup Diagnosis

Diagnosis and fix for Intel integrated GPU black screen lockups where the display goes permanently black and requires a hard power-off. No kernel panic, no OOM, no GPU timeout in logs — the system is still running but the display pipeline is frozen at the kernel level.

## Trigger conditions

Use this skill when the user reports:
- "Screen goes black and I have to hold the power button to turn it off"
- "Laptop freezes to a black screen, nothing works"
- "Black screen but I can still hear audio / SSH works"
- "Computer hard locks, no TTY switch works (Ctrl+Alt+F2 does nothing)"
- "No crash logs, nothing in dmesg or journalctl"
- Specifically on a laptop with Intel integrated graphics (UHD 620/630, Iris, HD Graphics)

## Root cause

**Panel Self Refresh (PSR)** — an Intel i915 power-saving feature. The GPU tells the LCD panel to refresh from its own internal buffer (self-refresh) so the GPU can sleep. On many consumer laptops, the panel never wakes back up from this state. The display hardware locks permanently dead until a full power cycle.

This is NOT a compositor crash, NOT a driver crash, NOT a kernel panic. The GPU driver considers PSR a success. That's why there's no log entry — from the driver's perspective, nothing went wrong.

## Diagnostic pipeline

### 1) Confirm it's Intel integrated graphics

```bash
lspci -nn | grep -iE 'vga|3d|display'
# Look for: Intel Corporation UHD Graphics 620 [8086:5917]
# If you also see a NVIDIA/AMD GPU, check Optimus/PRIME: the display still routes through Intel
```

### 2) Check which GPU driver is loaded

```bash
lsmod | grep i915
# If i915 is loaded and nvidia/nouveau/amdgpu are absent, you're on Intel-only display
```

### 3) Check display server type

```bash
echo "$XDG_SESSION_TYPE"
# X11 (common on KDE) — PSR bug affects both X11 and Wayland
```

### 4) Check i915 PSR status

```bash
cat /sys/module/i915/parameters/enable_psr
# -1 = hardware default (PSR enabled)
#  0 = disabled (the fix)
#  1 = PSR1 only
#  2 = PSR2 (deeper panel self-refresh)

cat /proc/cmdline
# Look for i915.enable_psr=0 — if absent, PSR is still enabled
```

### 5) Check power management states

```bash
cat /sys/power/mem_sleep
# s2idle [deep] — deep is good, but PSR can fire regardless
```

### 6) Check for supporting evidence

```bash
ls -la /var/crash/*.crash 2>/dev/null | grep chrome
# Chrome GPU crash dumps (>200MB) are a red flag — Chrome exercises GPU paths that trigger PSR failure early

# No errors to find — the absence of crash evidence IS the evidence
```

## Fix

### Primary fix — disable PSR

Add `i915.enable_psr=0` to kernel boot parameters:

```bash
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="[^"]*/& i915.enable_psr=0/' /etc/default/grub
sudo update-grub
```

**Reboot required** — no kernel parameter change takes effect until reboot.

After reboot, verify:

```bash
cat /proc/cmdline
# Should contain i915.enable_psr=0

cat /sys/module/i915/parameters/enable_psr
# Should show 0
```

### Additional parameters if PSR disable alone isn't enough

| Parameter | Effect | Use when |
|---|---|---|
| `i915.enable_psr=0` | Disable PSR | Primary fix |
| `i915.enable_dc=0` | Disable display C-states (deeper power saving) | Black screen still happens after PSR fix |
| `i915.enable_fbc=0` | Disable Frame Buffer Compression | Screen corruption/flickering alongside black screen |
| `i915.enable_guc=0` | Disable GuC submission | GPU hangs + display lockup combo |
| `processor.max_cstate=1` | Keep CPU in shallow C-state | Crashes correlate with CPU package idle |
| `intel_idle.max_cstate=1` | Same, via intel_idle driver | When above alone doesn't help |

Stack them in GRUB_CMDLINE_LINUX_DEFAULT space-separated.

### Apply all four i915 mitigations at once (nuclear option)

```bash
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="[^"]*/& i915.enable_psr=0 i915.enable_dc=0 i915.enable_fbc=0 i915.enable_guc=0/' /etc/default/grub
sudo update-grub
```

## Known affected models

- **HP Pavilion 15-cs0xxx** — UHD 620, Kaby Lake R
- HP Pavilion 14-ce0xxx — UHD 620
- Dell XPS 13 9370/9380 — UHD 620
- Lenovo ThinkPad X1 Carbon Gen 6 — UHD 620
- Any Kaby Lake / Whiskey Lake / Coffee Lake laptop with Intel integrated PSR support

## Pitfalls

- **No log evidence.** PSR failures leave NOTHING in dmesg, journalctl, or any other log. The GPU driver thinks it did its job. If you're searching for crash evidence and finding none on an Intel integrated laptop, PSR is the top suspect.
- **TTY switching also fails.** This distinguishes PSR from a compositor/DE crash (where Ctrl+Alt+F2 recovers). When the display hardware itself is locked, no software recovery is possible.
- **System continues running.** The laptop is still on, CPU runs, network works, you can SSH in. The crash is display-only. Uptime will show no reboot.
- **Hybrid graphics laptops (Optimus/PRIME)** still drive the display through Intel even when a discrete NVIDIA/AMD GPU is present. Removing the NVIDIA driver does NOT fix PSR.
- **nvidia-smi fails is a trap.** When `nvidia-smi` says "couldn't communicate with NVIDIA driver" on an Optimus laptop, it's a massive distraction. The NVIDIA kernel module may simply be broken (missing headers, build failure) — that's a separate issue from the black screen and often a wild goose chase. Diagnose and fix PSR first, then clean up the NVIDIA driver if the user asks. The display doesn't use the NVIDIA GPU.
- **Chrome crash dumps** in /var/crash are a clue, not the cause. Chrome's GPU acceleration hits GPU paths aggressively and often triggers PSR lockup first, but Chrome itself isn't at fault.
- **Previous power management workarounds** (`processor.max_cstate=1`) are often already present on machines with known issues — they don't fix PSR, they fix a different class of freeze (CPU package C-state hang vs display panel lockup).
- **The fix requires a reboot.** GRUB parameters are read at boot. The user will need to restart the machine before they see any change.
- **Check `journalctl -b -1` before concluding "no logs" — don't skip it.** The crashed boot's journal, when preserved, ends ABRUPTLY mid-write with no `Reached target Power-Off` / `Reached target Sleep` line. That abrupt cut is the hard-freeze/hard-power-off signature and distinguishes a wedge from a clean shutdown or suspend (both log their target). Don't expect -1 to reveal a PSR ROOT CAUSE (there is none) — but the abrupt end confirms the prior session genuinely wedged rather than quietly running or cleanly stopping.
- **A low journal cap fabricates "no logs".** If `SystemMaxUse=` in /etc/systemd/journald.conf is small (e.g. 50M), heavy logging churn (e.g. a service crash-looping at a huge `NRestarts` count) vacuums the crashed boot's record entirely, so `journalctl --list-boots` shows a clean-looking gap and PSR looks like the culprit when the evidence was actually destroyed. Before blaming "no log evidence = PSR", verify the cap would even preserve the incident: raise it (`sed -i 's/^SystemMaxUse=.*/SystemMaxUse=500M/' /etc/systemd/journald.conf` then `systemctl restart systemd-journald`) so the next black screen leaves a record.
