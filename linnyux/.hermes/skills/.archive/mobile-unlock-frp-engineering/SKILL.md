---
name: mobile-unlock-frp-engineering
description: >-
  Research, develop, and test mobile device FRP (Factory Reset Protection) and
  lock-screen bypass tools. Covers Android lock-state detection, Download Mode
  protocol, combination/engineering firmware flashing, ADB extraction under root,
  gatekeeper database manipulation, Qualcomm EDL, MediaTek SP Flash, Samsung Odin,
  and dark-web crawl research for new methods. Use when building unlock tools,
  researching bypass techniques, or integrating exploit modules.
domain: cybersecurity
tags:
  - mobile-security
  - frp-bypass
  - samsung-unlock
  - android-security
  - exploit-development
  - hardware-security
  - qualcomm
  - mediatek
version: 1.0.0
author: agent
---

# Mobile Unlock / FRP Engineering

Build tools to bypass Android Factory Reset Protection (FRP) and device lock screens.

## When to Use

- User asks you to build or improve an unlock/FRP bypass tool
- Researching new bypass methods for a specific device (Samsung, Pixel, Xiaomi, etc.)
- Integrating exploit modules into a larger unlock suite
- Testing a locked device via USB (Download Mode, fastboot, EDL)
- Crawling dark web sources for new bypass techniques

Do NOT use for: general Android development, app security testing, or writing malware.

## Key Concepts

### Lock States

| State | USB Access | ADB | What Works |
|-------|-----------|-----|------------|
| Locked OS (pattern/PIN/password) | Enumeration only | No (unauthorized) | Recovery mode, Download Mode, remote unlock |
| Download Mode (Samsung) | Full (PID 0x685d) | No (bootloader mode) | Odin/Heimdall firmware flash |
| Fastboot (Google/Pixel/OnePlus) | Full | No | `fastboot flashing unlock`, `fastboot boot twrp.img` |
| EDL (Qualcomm) | Full (PID 900E) | No | Firehose programmer via qdl/edl.py |
| Combo/Engineering FW | Full | Yes (root) | Full filesystem access, sqlite3, rm gatekeeper keys |

### Samsung Unlock Pipeline (the proven path)

```
Locked OS → Volume Down + Power → Download Mode → Odin flash combination firmware →
Boot combo FW (ADB root) → Pull gatekeeper.db / delete .key files → Reboot → Unlocked
```

### The combination firmware is the key piece — engineering Samsung builds with adbd running as root.

## Workflow

### Phase 1: Research

Search for:
- Combination firmware for the specific model (`COMBINATION_FA81_S921B*` for S24)
- Known CVEs affecting the device's SoC (Qualcomm, MediaTek, Exynos)
- Community guides on XDA, GSM-forums, Reddit
- Dark web sources (via Tor): Ahmia, Torch, DuckDuckGo onion, known GSM/unlock forums

### Phase 2: Build exploit modules

Create modular exploit managers organized by attack surface:

| Module Directory | Covers |
|-----------------|--------|
| `adb/` | ADB-based exploits: TalkBack, intent manipulation, accounts DB |
| `interface/` | UI-level: dialer codes, accessibility, chrome://flags, Assistant, NFC |
| `system/` | Filesystem: persist partition, framework patch, bootloader+TWRP |
| `hardware/` | Chipset: Qualcomm EDL, MediaTek SP Flash, Odin combo firmware |
| `unlock/` | Full pipeline: lock detection → download mode → combo FW → lock clear |

### Phase 3: Safety rules for subprocess

- **NEVER** use `shell=True` — always use argument lists with `shell=False`
- Set explicit `timeout` on every subprocess call (adbd hangs are common)
- Use `capture_output=True, text=True` and parse stdout in Python (don't pipe through grep)
- Catch `subprocess.TimeoutExpired` separately from `Exception`
- Use `logger.exception()` in exception handlers for full tracebacks

### Phase 4: Integrate into web API

Expose methods as REST endpoints with:
- Health check reporting which modules are available
- Method listing with device model/version compatibility
- AI-assisted method selection based on device specs
- Lock-screen state detection endpoint

## Pitfalls

- **ADB is dead on locked devices** — don't try software methods on a pattern-locked phone with USB debugging off. Hardware path only (Download Mode, recovery, or remote unlock).
- **Combination firmware is Samsung-signed** — you can't build your own. Must source from SamFW, SamMobile, or community uploads.
- **Download Mode kills ADB** — you can't adb while in download mode. The combo firmware boot is what restores ADB.
- **Knox Vault on S24+** stores lock credentials in hardware-isolated processor. Software clear works because combo firmware bypasses Knox at bootloader level, but the physical key data is never directly readable.
- **Tor connections are unreliable** — .onion sites have high churn. The generic crawler running continuously is more effective than one-shot searches. Feed keywords to an existing crawler daemon rather than building a new one each time.
- **Gatekeeper database format** — Android 14+ uses `/data/system_de/0/spgatekeeper.db`. SQLite with hashed credentials. Deleting the file or the corresponding `gatekeeper.*.key` files removes the lock. No need to crack the hash if you just want the phone unlocked.
- **Never expose error messages from exploit modules to HTTP clients** — log server-side, return generic messages.
