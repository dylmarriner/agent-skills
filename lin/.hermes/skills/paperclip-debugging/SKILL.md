---
name: paperclip-debugging
description: 'Diagnose and fix Paperclip issues: auth/permission failures, dev server startup, OpenClaw/Hermes integration, resume session placeholder bugs.'
---

# Paperclip Debugging

Comprehensive troubleshooting for Paperclip application issues.

- [Embedded Postgres Library Fixes](references/embedded-postgres.md) — shared library version mismatch (`libicui18n.so.60`)
- [Embedded Postgres Crashed Mid-Run](references/embedded-postgres-crashed.md) — Postgres process dies silently, server still runs, `ECONNREFUSED` on port 54329
- [Hermes Tirith Blocks Paperclip API](references/hermes-tirith-blocks-paperclip-api.md) — Spawned agents can't curl Paperclip API, tirith auto-denies
## When to Use

Triggers:
- Paperclip auth/permission failures (401/403 on company/task endpoints)
- Dev server fails to start, connect, or returns DB errors consistently
- OpenClaw or Hermes integration broken with Paperclip
- Session resume paths fail with placeholder content

## Sub-workflows

### 1. Auth & Permission Path Troubleshooting
See: `references/auth-path-troubleshooting.md`
Use when resumed board/CEO sessions lose context. Absence of bearer token is not unauthenticated.

### 2. Dev Server Startup
See: `references/dev-server-startup.md`
Use when Paperclip local dev server wont start or gets connection-refused.

### 3. OpenClaw + Hermes Integration
See: `references/hermes-openclaw-integration.md`
Use when Hermes fails to connect Paperclip to OpenClaw.

### 4. OpenClaw Core Integration
See: `references/openclaw-troubleshooting.md`
Use when Paperclip to OpenClaw to Hermes onboarding chain fails.

### 5. Session Resume Placeholder Guard
See: `references/resume-session-placeholder-guard.md`
Use when resume-session paths return placeholder/null data.

### 6. Adapter Session Resume Hardening
See: `references/adapter-session-resume-hardening.md`
Harden agent adapter resume flows so malformed, placeholder, or stale session IDs never pass as literal resume IDs.

### 7. OpenCode Adapter SQLite Lock Failure
See: `references/opencode-sqlite-lock-pattern.md`
Use when Paperclip adapter runs fail with `database is locked` and the stderr shows a SQLite/Raw SQL stack trace. Caused by stale OpenCode processes holding write locks on the global `~/.local/share/opencode/opencode.db`.

### 8. Gateway "unexpected property 'paperclip'" Error
See: `references/gateway-paperclip-property-rejection.md`
When an openclaw_gateway run fails with `invalid agent params: at root: unexpected property 'paperclip'` — the fix is embedding context JSON in the message text instead of a top-level param.

### 9. Orphaned OpenCode Agent Cleanup
See: `references/orphaned-agent-cleanup.md`
Use when Paperclip was killed but spawned OpenCode agents survived — typically 10-15+ processes consuming 300-630MB RAM and 20-27% CPU each.
**Automated script**: `bash ~/.paperclip/scripts/cleanup-orphaned-agents.sh` — safely kills only agent CLI processes (opencode run, codex run, claude-code).

### 10. OpenCode Model Discovery Timeout
See: `references/opencode-model-discovery-timeout.md`
Use when all OpenCode agent runs fail with `` `opencode models` timed out after 20s. `` — caused by a custom provider `baseURL` in `~/.config/opencode/opencode.json` pointing to a non-responsive endpoint (typically LiteLLM on the wrong port).

### 11. Embedded Postgres Crashed Mid-Run
See: `references/embedded-postgres-crashed.md`
Use when the Paperclip server is listening but every DB query returns `ECONNREFUSED 127.0.0.1:54329`. Postgres process died silently while the server kept running. Fix: `systemctl --user restart paperclip.service`.

### 12. Hermes Agent API Access Blocked by Tirith Security
See: `references/hermes-tirith-blocks-paperclip-api.md`
Use when a Paperclip-spawned Hermes agent (CEO, CTO, Engineer, etc.) runs but produces only a heartbeat report — the run transcript shows `curl` to the Paperclip API getting denied by tirith security scanner. Fix: set `hermes config set approvals.mode smart` or register a Tailscale MagicDNS hostname.

### 13. Cloud Server Deployment
See: `references/cloud-server-deployment.md`
Use when setting up Paperclip, LiteLLM, and OpenCode on a fresh Ubuntu cloud server. Covers PostgreSQL setup, LiteLLM Docker with Vertex AI service account keys, OpenCode config pointing to LiteLLM, Paperclip config schema validation pitfalls, `bind: tailnet` vs `npm_config_bind`, systemd service, and running-as-root considerations.

### 14. Managed AI Subscription Connections (OpenAI / ChatGPT)
See: `references/ai-connection-subscription.md`
Use when a local subscription connection 422s on Connect, or an environment test rejects it with `ai_connection_incompatible`. Covers the device-auth ordering (`authorizationUrl` + code before Connect) and the project/global `~/.codex/config.toml` keys that make Paperclip refuse a managed connection — a flat text grep, so conflicting lines must be deleted, not commented out.
