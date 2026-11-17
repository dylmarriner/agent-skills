---
name: openclaw-maintenance
description: Routine maintenance and configuration repair for OpenClaw.
---

# OpenClaw Maintenance

## Overview
OpenClaw services (Gateway, daemons, and state storage) require periodic maintenance to resolve legacy state, configuration drift, and service health issues.

## Repair Workflow

When OpenClaw reports invalid configuration or service failures:

1.  **Stop Service:** Always stop the service before repair.
    `systemctl --user stop openclaw-gateway.service`
2.  **Diagnostics:** Check the status and deep diagnostics.
    `openclaw gateway status --deep`
3.  **Repair:** Run the doctor to fix common issues (legacy state migrations, pairing stores, config drift).
    `openclaw doctor --fix`
4.  **Restart & Verify:** After repair, ensure the service is clean and restart.
    `systemctl --user start openclaw-gateway.service`
    `openclaw doctor` (verify clean)

## Common Pitfalls

- **Stalled Gateway:** If `openclaw doctor` fails to enter maintenance, the gateway service might still be holding resources. Stop it manually via `systemctl`.
- **Config Pollution:** `openclaw.json` can accumulate legacy keys. If a setting seems ignored, validate the config file via `openclaw config validate`.
- **Secret Leaks:** `openclaw.json` must NOT contain plaintext secrets (like API tokens). If the doctor warns of plaintext secrets, migrate them to `SecretRefs` immediately using `openclaw secrets apply`.
- **Skill Precedence:** Collisions between bundled plugins and `~/.agents/skills/` are common. When reinstalling plugins, verify that `~/.agents/skills/` overrides are still desired.

## Verification
- Always run `openclaw status` after any maintenance.
- Verify channel health (Telegram, WhatsApp) to ensure connectivity wasn't dropped during restart.
