---
name: paperclip-openclaw-troubleshooting
description: Debug and fix Paperclip ↔ OpenClaw ↔ Hermes onboarding and model-routing issues, especially loopback hostname problems and wrong provider/model fallback.
---

# Paperclip OpenClaw Troubleshooting

Use this skill when Paperclip/OpenClaw/Hermes onboarding or runtime routing behaves incorrectly, especially when:
- invite/onboarding URLs resolve to localhost or loopback instead of a reachable host
- private-hostname guards block a reachable host
- Paperclip keeps advertising the wrong adapter model/provider
- Hermes launches with the wrong provider path instead of the intended LiteLLM/custom path
- you need end-to-end verification after a config or adapter change

## Core idea
These issues are usually caused by more than one layer:
1. request-derived URLs in the server
2. hostname allowlists / private-hostname guards
3. config-file defaults
4. adapter metadata / detected model lists
5. the consumer launcher choosing a different provider than expected

Do not assume one config file is the whole truth.

## Workflow

### 0) Rule out the adapter preflight before everything else
Adapters often run a preflight check before the real agent execution (e.g. `opencode models` to verify the model is available). If the preflight fails, the adapter reports `adapter_failed` and never gets to the actual work. When you see `adapter_failed`, trace the preflight first:

1. **Reproduce directly in the shell** — run the exact commmand the adapter would run (e.g. `opencode models` for the opencode-local adapter). If it fails there too, the issue is the host config, not the adapter code.
2. **Check the temp config** — the adapter copies the user's config to a temp dir and may inject runtime overrides. Inspect the generated file at the temp path mentioned in the error (e.g. `/tmp/paperclip-opencode-config-*/opencode/opencode.json`) before the cleanup runs.
3. **Check env propagation** — adapters often pass a filtered env; if the adapter depends on env vars that are not in the spawned process, they may fail silently.

### 1) Trace the actual source of truth
Inspect the active runtime paths first, not just the visible config:
- Paperclip server config and host defaults
- onboarding/invite route that generates URLs
- private-hostname guard / allowlist logic
- adapter registry and model detection
- Hermes config file and launcher/provider selection
- OpenClaw gateway config when the onboarding flow depends on it

### 1.1) Be careful with OpenClaw/Tailscale gateway changes
When the onboarding flow depends on an OpenClaw gateway exposed through Tailscale:
- do not assume `gateway.bind=tailscale` is valid; in serve mode, validation can require `gateway.bind=loopback`
- prefer changing `gateway.tailscale.mode=serve` together with a loopback bind
- if using `openclaw config set ... --strict-json`, enum/string values must be JSON strings (for example `"serve"`), not bare words
- verify the resulting config file after edits because the config helper may rewrite or compact sections unexpectedly
- confirm with `openclaw gateway status` and `openclaw gateway probe` rather than trusting the edit alone

Good targets:
- `server/src/config.ts`
- `server/src/routes/access.ts`
- `server/src/middleware/private-hostname-guard.ts`
- `server/src/adapters/registry.ts`
- adapter package model metadata
- Hermes user config

### 2) Fix hostname drift end-to-end
If onboarding URLs keep resolving to loopback:
- check `requestBaseUrl()` or equivalent server helper
- check `x-forwarded-host` / `host` handling
- check `bindHost` and `allowedHostnames`
- check whether the server default host is still `127.0.0.1` or `localhost`
- make sure the onboarding text/document generator uses the reachable host

If the environment is private/authenticated:
- ensure the reachable host is in the allowlist
- verify the private-hostname guard accepts the host you want
- verify any fallback host candidates are not forcing localhost

### 3) Fix model/provider drift end-to-end
If Hermes or Paperclip chooses the wrong provider/model:
- inspect adapter `models` metadata
- inspect `detectModel()` if the registry uses model auto-detection
- inspect Hermes config provider/base URL/model fields
- verify the launcher is not hardcoding a different provider path

For LiteLLM/OpenAI-compatible endpoints:
- use the exact model id the proxy advertises
- confirm `/v1/models` and `/v1/chat/completions` accept that model id
- if a proxy exposes prefixed model ids, use that exact id everywhere

### 4) Verify with direct smoke tests
Do not stop at config edits. Verify the live path.

Useful checks:
- read the generated onboarding/invite document and confirm the host is correct
- call the LiteLLM proxy `/health` and `/v1/models`
- send a tiny `/v1/chat/completions` request with the intended model id
- run Hermes with a single-line query and confirm the response comes from the intended provider/model
- confirm the onboarding text no longer mentions localhost unless intentionally allowed as a fallback
- for Paperclip invite reachability checks, use the invite’s `/test-resolution?url=...` endpoint with an http/https URL; do not pass a ws:// URL there, because the endpoint rejects non-HTTP schemes even when the onboarding flow itself expects a ws/wss gateway URL

### 5) Patch carefully and re-check
When making edits:
- update the server host fallback and any guard logic together
- update adapter model metadata and registry detection together
- update both config defaults and generated-document text if needed
- verify the exact strings in the edited files after patching

## Common pitfalls
- Always check the adapter preflight before digging deeper. `adapter_failed` means the adapter's test/diagnostic step failed, not the actual agent execution. Run the preflight command directly in the user's shell to isolate the issue.
- When modifying the Paperclip OpenCode adapter (`packages/adapters/opencode-local/src/server/runtime-config.ts`), env vars needed by the runtime config injection code must be available in `process.env` when Paperclip runs. The `env` object passed to `prepareOpenCodeRuntimeConfig()` is built from `buildPaperclipEnv()` (Paperclip-internal vars only) — it does NOT include system env vars. Always add a `process.env` fallback when reading env vars from the `env` parameter.
- **pnpm strips environment variables for reproducibility.** If you set `export FOO=bar` before `pnpm paperclipai run`, the spawned Paperclip process will not have `FOO`. Two reliable workarounds: (a) pass the var inline before pnpm: `FOO=bar pnpm paperclipai run`, or (b) use `exec` in the startup command: `export FOO=bar; exec node ... run`. Verify with `cat /proc/$PID/environ | tr '\\0' '\\n' | grep FOO`.
- After editing adapter TypeScript source, rebuild with `pnpm build` from the adapter package directory. When Paperclip runs via `tsx` (TypeScript execution), source changes are picked up on restart without rebuilding `dist/`. When Paperclip runs the compiled `dist/` (npx/npm package), rebuild is required.
- A generated onboarding/invite document can still embed stale localhost text even when config looks correct.
- `x-forwarded-host` and `Host` headers can override the apparent host.
- A private-hostname guard may accept loopback but reject the reachable host if the allowlist is stale.
- An adapter registry can advertise a model that the proxy does not actually accept.
- A launcher may be configured correctly but invoked through a different provider path by another tool.
- A Paperclip invite can be valid one moment and then 404 if the invite ID is stale/rotated; always re-check the current invite endpoint before assuming the API is broken.
- Paperclip’s `test-resolution` endpoint may intentionally reject `ws://` / `wss://` URLs even though the final onboarding join expects a WebSocket gateway URL; use the exact scheme the endpoint requests.
- A join request can fail even when the invite is served correctly if the OpenClaw gateway token is a placeholder or too short; verify the token length and the live gateway service status before retrying.
- Paperclip's OpenCode adapter (`packages/adapters/opencode-local/src/server/runtime-config.ts`) copies the user's `~/.config/opencode/` to a temp dir and runs `opencode models` as a preflight check. If the user's opencode config has stale/unknown keys (e.g. `mcpServers` instead of `mcp`), OpenCode rejects it with "Configuration is invalid" and the adapter logs `adapter_failed`. When debugging OpenCode adapter failures, run `opencode models` directly in the user's shell to rule out config schema issues before looking deeper.
- On this machine, `openclaw doctor --generate-gateway-token --yes` is the quickest way to replace a placeholder gateway token with a real full token.
- The Paperclip `test-resolution` endpoint only accepts `http://` or `https://` URLs, even when the final join uses a `ws://`/`wss://` gateway URL.
- Invite IDs can rotate or expire between checks; always re-fetch the current invite endpoint before assuming the API is broken.
- `openclaw status` may report the systemd gateway service as stopped even when the local listener and `openclaw gateway probe` are healthy; trust the probe and `/health` check over the service wrapper alone.
- Paperclip can serve the UI shell at the root origin while the agent API still needs an explicit `/api` base URL; if `/api/agents/me` returns `Agent authentication required` despite a claimed key file existing, confirm the runtime is pointing at the actual API origin (for example `http://127.0.0.1:3100/api`) rather than the UI root.
- In that situation, updating the Paperclip instance config is often the real fix; a working gateway and a present claimed key file do not prove the API base is correct.
- If `GET /api/health` is healthy but `/api/agents/me` still 401s, test the live process with the bearer token directly and remember that a config/code change does not matter until the running Paperclip server is restarted and rechecked against the same endpoint.
- Some failures look like Hermes/env problems but are actually Paperclip auth-path issues; distinguish launch-time env propagation from server-side bearer-token recognition before changing the wrong layer.
- Patch/lint helpers can fail in this environment due unrelated tool resolution issues; always verify by reading the file contents directly if needed.

## Verification checklist
Before calling the task done, confirm all of these where relevant:
- the generated invite/onboarding URL uses the reachable host
- the private-hostname guard accepts that host
- the server default host is not forcing loopback
- the adapter advertises the correct model id
- Hermes config points at the intended base URL and model id
- the current invite ID is valid and serves onboarding.txt
- `test-resolution` is called with the correct URL scheme and returns a meaningful result
- the OpenClaw gateway token is a real full token, not a placeholder
- the gateway service is actually running when Paperclip tries to join
- a live test returns the expected response

## Example end state
- Paperclip onboarding uses a reachable host instead of localhost
- Hermes uses the intended model through the LiteLLM/OpenAI-compatible path
- the live test returns the expected one-word response
