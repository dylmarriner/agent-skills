---
name: samsung-unlock-reference
description: "Reference doc for the universal unlock suite tooling — heimdail protocol nuance, local suite path, and pipeline ordering for Samsung FRP/unlock operations. Used as a companion to the full samsung-device-unlock skill."
version: 1.0.0
tags: [samsung, unlock, frp, heimdall, reference]
---

# Samsung Unlock — Session Reference

## Heimdall 1.4.2 Nuance (discovered 2026-06-24)

Heimdall 1.4.2 **can** initialize protocol on post-2022 Samsung (confirmed S24 SM-S921B and A54 SM-A546E):
- `Initialising connection...` → `Protocol initialisation successful.`
- But `print-pit` exits code 1 — PIT read fails even though protocol handshake works.
- This means heimdall is not *completely* useless on these devices — flashing may work even if PIT read doesn't.
- Do NOT write off heimdall entirely when protocol init succeeds. Try flash operations separately.

## Universal Unlock Suite

**Path:** `~/Documents/universal-unlock-suite/`

Full-stack Docker-based unlock platform. Components:

### Quick start
```bash
cd ~/Documents/universal-unlock-suite
cp -n .env.example .env
# If port 5000 is taken (e.g. by frigate), change docker-compose port mapping first
docker compose up -d
```

### CLI
```bash
# Detect USB state
python3 -m backend.exploits.android.unlock.samsung_unlock --detect

# Run full pipeline (needs combination firmware)
python3 -m backend.exploits.android.unlock.samsung_unlock --model SM-S921
```

### Key modules
- `backend/exploits/integrated_android.py` — `IntegratedAndroidExploitSuite`: emergency dialer codes, FRP Freedom pipeline, Samsung AT command fallback
- `backend/exploits/android/unlock/samsung_unlock.py` — standalone unlock pipeline: detect state, find combo firmware, flash via heimdall, clear lock data via ADB root
- `backend/exploits/android/samsung_adb_enabler.py` — AT command modem ADB enabler (requires PID 6860, normal boot)
- `backend/exploits/core/frp_device_manager.py` — `DeviceManager` for USB device detection

### Docker port conflicts
When running alongside Synapse Memory (postgres on 5432, redis on 6379) or frigate (port 5000):
- Change `127.0.0.1:5432:5432` to `127.0.0.1:5436:5432` in docker-compose.yml
- Change `127.0.0.1:6379:6379` to `127.0.0.1:6382:6379`
- Change `PORT:-5000` to `PORT:-5001`
