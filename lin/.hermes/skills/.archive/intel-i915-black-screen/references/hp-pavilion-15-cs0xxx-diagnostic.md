# HP Pavilion 15-cs0xxx PSR Black Screen Diagnostic Record

## Hardware

- **Model:** HP Pavilion Laptop 15-cs0xxx
- **BIOS:** "To be filled by O-E-M" (HP placeholder, not updated)
- **CPU:** Kaby Lake R (8th gen)
- **IGP:** Intel UHD Graphics 620 [8086:5917]
- **dGPU:** NVIDIA GeForce MX150 [10de:1d10] — Optimus, display not routed through it
- **OS:** Kubuntu, kernel 7.0.0-28-generic
- **Display server:** X11 (KDE Plasma via SDDM)

## Crash pattern

- Screen goes black suddenly during normal use
- No response to any input (keyboard, mouse, touchpad)
- Ctrl+Alt+F2-F6 — no TTY shown
- Caps Lock key LED does NOT toggle (keyboard controller not responding either, or display too dead to see it)
- Only recovery: hold power button 5-10 seconds for hard power-off, then press again to boot
- No crash logs in dmesg, journalctl, or /var/crash (other than Chrome GPU crash dumps)
- System is still running and accessible via SSH while black

## Log findings

**dmesg errors (boot-time only, not crash related):**
```
ACPI BIOS Error: Attempt to CreateField of length zero (ACPI method \\_SB.WMID)
ACPI Error: AE_AML_BUFFER_LIMIT (HP WMID method — harmless)
usb 1-4: device descriptor read/64, error -32 (USB device on port — unrelated)
CIFS VFS: Error connecting to socket (network mounts not available at boot — unrelated)
```

**Kernel modules loaded:**
```
i915 — Intel GPU
(supplementary: drm_buddy, ttm, drm_display_helper, drm_kms_helper, i2c_algo_bit, video)
nvidia — NOT loaded
nouveau — NOT loaded
```

**i915 PSR status:**
```
/sys/module/i915/parameters/enable_psr = -1 (hardware default — PSR enabled)
```

**Sleep state:**
```
s2idle [deep] — deep sleep available
```

**Boot parameters before fix:**
```
quiet splash mitigations=off processor.max_cstate=1 intel_idle.max_cstate=1 nowatchdog
```
(Previous power management workarounds already applied — did not fix PSR)

**Memory:** 15Gi total, ~10Gi used, 5.8Gi available, 2.7Gi swap used (moderate pressure, not causal)

**Crash dump evidence:**
```
/var/crash/_opt_google_chrome_chrome.1000.crash — 228MB (Chrome GPU crash)
```

## Fix applied

Added `i915.enable_psr=0` to `GRUB_CMDLINE_LINUX_DEFAULT` in `/etc/default/grub`.

Final boot parameters:
```
quiet splash mitigations=off processor.max_cstate=1 intel_idle.max_cstate=1 nowatchdog i915.enable_psr=0
```

Verified with `sudo update-grub`. Reboot required to take effect.

## Notes

- The `processor.max_cstate=1 intel_idle.max_cstate=1` were already present from a prior power management issue. They prevent CPU deep sleep but do NOT prevent PSR — they address a different freeze class (CPU package C-state hang vs display panel lockup).
- NVIDIA driver 580.159.03 is installed but the kernel module fails to load (crash file present: `linux-modules-nvidia-580-7.0.0-28-generic.0.crash`). This is irrelevant to the display problem on Optimus laptops — Intel drives the panel regardless.
- A cron job `/usr/local/bin/nvidia_gpu_metrics.sh` runs every minute and fails silently (nvidia-smi can't communicate). Nice to clean up but not causal.
