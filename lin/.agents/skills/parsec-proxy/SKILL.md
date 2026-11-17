---
name: parsec-proxy
description: Check (and revive) the parsec proxy this Codex session routes through
---
<!-- parsec-managed-skill: written by `parsec setup codex`; removed by `parsec disable codex`. -->

Run: `curl -s http://127.0.0.1:8082/health`

- If it answers with service "parsec-proxy": report it healthy (include the version) and remind the user this Codex session routes through it.
- If it does not answer: run `~/.parsec/bin/parsec up || parsec up`, wait 2 seconds, and re-check. Report what happened. Already-running sessions reconnect on their next request; nothing needs restarting.
