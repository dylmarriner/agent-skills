### Hermes Agent API Access Blocked by Tirith Security

When Paperclip spawns a Hermes agent (via `hermes_local` adapter — CEO, CTO, Engineer, etc.), the agent needs to `curl` the Paperclip REST API to fetch its assigned issues, check status, and post results. The tirith security scanner blocks these requests, causing agents to stall.

#### Symptoms

In the Paperclip run transcript, you see:

```
⚠️ DANGEROUS COMMAND: Security scan — [MEDIUM] URL uses raw IP address
⚠️ DANGEROUS COMMAND: Security scan — [HIGH] Plain HTTP URL in execution context
curl -s "http://100.68.0.96:3100/api/companies/.../issues?assigneeAgentId=..."
[o]nce | [s]ession | [d]eny
Choice [o/s/D]: ✗ Denied
```

followed by the agent reporting it couldn't proceed with only a heartbeat summary — no actual work done.

The tirith `last_trigger.json` shows:
```json
{
  "rule_ids": ["raw_ip_url", "plain_http_to_sink"],
  "severity": "HIGH"
}
```

#### Root Cause

Two tirith rules fire:
1. **`raw_ip_url`** (MEDIUM) — `100.68.0.96` or `100.93.75.87` are raw Tailscale IPs, not domain names
2. **`plain_http_to_sink`** (HIGH) — HTTP instead of HTTPS, being piped to or consumed by a program

Since Paperclip agent runs are **unattended** (no human watching the terminal), the approval prompt's default action (`[D]eny`) kicks in every time. The agent never gets past the first curl.

#### Fixes

Pick one of three approaches, ordered by safety:

**Option A: `approvals.mode: smart` (recommended)**

Uses a lightweight LLM to evaluate risk. A simple `curl` to an internal Tailscale API for JSON data gets auto-approved; destructive commands (`rm -rf`, `git reset --hard`) still prompt.

```bash
hermes config set approvals.mode smart
```

Requires a `/reset` (or new session) to take effect. Does NOT require restarting the gateway or Paperclip — only the spawned Hermes agent sessions need it.

**Option B: Register the Tailscale MagicDNS hostname**

Instead of using the raw Tailscale IP, Paperclip could provide the MagicDNS hostname (e.g., `kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net`) in the agent's initial context. This avoids the `raw_ip_url` rule. However, `plain_http_to_sink` may still fire on domain-based HTTP URLs depending on context.

First register the hostname with Paperclip:
```bash
cd /media/kubuntux/DEVELOPMENT1/paperclip
pnpm paperclipai allowed-hostname kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net
```

**Option C: `approvals.mode: off` (least safe)**

Skips all approval prompts entirely — equivalent to running every agent with `--yolo`. Removes the safety net for all terminal commands.

```bash
hermes config set approvals.mode off
```

#### Stale Session Pitfall

Even with tirith unblocked, the agent may still fail if it **resumes a stale Hermes session** that carries old knowledge about the Paperclip API server IP.

When `hermes chat -r <session_id>` is used, the agent keeps all its prior context — including any incorrect API URLs it learned from previous runs (e.g., `100.68.0.96` when the server is now on `100.93.75.87`). The fresh `PAPERCLIP_API_URL` env var injected by Paperclip's adapter gets ignored because the resumed session already "knows" the wrong address.

**Fix:** Start a **fresh** agent run from the board instead of resuming an old session. Paperclip's hermes-local adapter resolves the API URL in this priority (from `dist/server/execute.js`):

1. `config.paperclipApiUrl` — agent config override
2. `process.env.PAPERCLIP_API_URL` — environment variable
3. `http://127.0.0.1:3100/api` — hardcoded fallback

A fresh run with no session to resume gets the correct URL from one of these sources.

#### Verification

After applying a fix, trigger a **new** agent run from Paperclip (not a resumed session). The run transcript should show the curl succeeding and the agent proceeding to fetch issues, work on them, and post results — no more denied commands or wrong-host timeouts.
