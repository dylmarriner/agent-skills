# OpenCode Model Discovery Timeout

## When to use

All OpenCode agent runs fail with `opencode models` timed out after 20s. Heartbeat failures flood the server log. The error stack trace points to `ensureOpenCodeModelConfiguredAndAvailable` in the adapter's `models.ts`.

## Root cause

Paperclip's opencode adapter calls `opencode models` before every run (and every heartbeat) to verify the configured model is available. When OpenCode lists models from a custom provider that points to a **non-responsive endpoint**, the whole `opencode models` command hangs until the Paperclip adapter's 20s timeout kills it.

The most common variant: **LiteLLM port mismatch**. The user's `~/.config/opencode/opencode.json` defines a custom provider (named e.g. `vertex`) with a `baseURL` pointing to one port, but LiteLLM is actually running on a different port.

## Diagnosis

1. Confirm the failure in the server log:
   ```
   tail -f ~/.paperclip/instances/default/logs/server.log | grep "opencode models"
   ```
   Expected: `ERROR: heartbeat execution failed` with message `` `opencode models` timed out after 20s. ``

2. Check what port LiteLLM is actually on:
   ```
   pgrep -af litellm | grep -v grep
   ```
   Expected output includes `--port <PORT>` — note the actual port.

3. Check the custom provider endpoint in opencode.json:
   ```
   cat ~/.config/opencode/opencode.json
   ```
   Look for the `provider.<name>.options.baseURL` field.

4. Test connectivity directly with curl:
   ```
   curl -v --connect-timeout 3 http://localhost:<PORT>/v1/models
   ```
   - Connection refused (exit 7) → nothing listening on that port
   - 401/403 → service is up but needs auth — that's fine for `opencode models`
   - Timeout → wrong address entirely

5. Test that `opencode models` runs quickly with the fix applied:
   ```
   time opencode models 2>&1 | grep <provider-name>
   ```
   Should complete in under 3s.

## Fix

Edit `~/.config/opencode/opencode.json` and update the `baseURL` for the custom provider to match the actual LiteLLM port.

```diff
 "options": {
-  "baseURL": "http://localhost:4000/v1",
+  "baseURL": "http://localhost:8899/v1",
   "apiKey": "..."
 }
```

No server restart needed — the adapter reads the user's opencode.json fresh each run.
