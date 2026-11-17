---
name: paperclip-hermes-openclaw-troubleshooting
description: Diagnose and fix Paperclip ↔ Hermes ↔ OpenClaw integration issues involving wrong hostnames, invite/onboarding URLs, and model/provider mismatches.
metadata:
  category: software-development
---

# Paperclip / Hermes / OpenClaw Troubleshooting

Use this skill when a Paperclip/OpenClaw onboarding or Hermes launch works partially but fails because of:
- loopback/localhost being embedded in invite URLs or callback URLs
- Hermes or Paperclip selecting the wrong provider/model (for example `openai-codex` or `hermes/gpt-4o` when you want LiteLLM / Azure)
- `openclaw_gateway` or `hermes_local` adapter detection surfacing the wrong model
- onboarding flows generating URLs that remote agents cannot reach

## Core principle

Do not assume the failure is only a config value. These integrations often have multiple layers:
1. runtime host resolution
2. invite/onboarding document generation
3. adapter model detection
4. gateway execution config
5. private-hostname allowlists
6. local CLI/runtime dependencies
7. Paperclip-side adapter registration/session management

Important: in some workspaces the Hermes implementation itself is not vendored in the Paperclip repo. The local Paperclip code may only import `hermes-paperclip-adapter` from installed packages. In that case, the fix often belongs in the Paperclip integration layer (`server/src/adapters/registry.ts`, heartbeat/session wiring, or onboarding text) rather than in a local Hermes source file.

When a local Hermes run behaves differently from Codex, compare the runtime envelope before comparing the adapter internals:
- Does the run mint a local agent JWT?
- Does the runtime log say it is running without injected `PAPERCLIP_API_KEY`?
- Is the run falling back to a workspace because no prior session/project cwd is available?
- Does the adapter registration include session management for `hermes_local` the same way the Codex path does?
7. Paperclip-side wrapper wiring around external adapter packages

Important lesson: Paperclip may expose an adapter type (for example `hermes_local`) without containing the adapter implementation in-repo. In that case, the fix may live in the Paperclip registry/session/auth wiring, not in a local adapter source tree.

Fix and verify each layer separately.

## Recommended workflow

1. Reproduce the exact failure message.
   - Capture whether the bad value appears in a runtime log, onboarding manifest, adapter selection, or CLI config.
2. Search for the literal value in the repo.
   - Examples: `localhost:3100`, `127.0.0.1:3100`, `hermes/gpt-4o`, `openai-codex`, `azure/gpt-4o`.
3. Identify which layer owns the value.
   - Invite URL generation usually lives in Paperclip server route helpers.
   - Adapter selection usually lives in adapter registry code.
   - Host gating usually lives in hostname/private-host guards.
4. Patch the runtime source of truth, not just a UI label.
   - If a route builds URLs from `requestBaseUrl()`, fix the fallback and forwarded-host handling there.
   - If an adapter reports the wrong model, patch `detectModel()` / `models` in the adapter registry or adapter package.
   - If private-host onboarding blocks a reachable host, add the reachable host to the allow set or config source.
5. Re-check the generated text/JSON and the runtime path.
   - Verify invite/onboarding docs contain the expected public host.
   - Verify the adapter reports the expected model ID.
   - Verify the runtime does not fall back to a hidden default.
6. Only if the app CLI is blocked by missing deps, create an isolated venv and install the missing runtime packages there to verify the path.

## Common fixes that worked in practice

### Host / invite fixes
- `requestBaseUrl(req)` may default to loopback if `Host` / `X-Forwarded-Host` is missing.
- Add a safe fallback to the reachable host only when appropriate for the deployment.
- In private-host middleware, ensure the reachable hostname/IP is allowed in the allow set.
- Remember that onboarding documents may also suggest candidate URLs; update those helper paths too.

### Dev server restart / port cleanup
- Paperclip can appear “down” while an older dev chain is still bound to a different port. Always check live listeners and active HTTP health, not just the last console banner.
- `pnpm dev:stop && pnpm dev:once` can exit with 143/SIGTERM during shutdown and look like a failure even when the restart path is fine. Verify whether the server actually came back before treating it as a real error.
- If a stale instance holds the expected port, kill the specific TCP listener first (for example `fuser -k 3100/tcp 3101/tcp 3102/tcp 13100/tcp`) before relaunching.
- If multiple Paperclip processes are active, use `pgrep -af 'paperclip|dev-runner.ts|tsx src/index.ts|dev-watch.ts'` to identify the live chain, then kill all Paperclip instances and relaunch one clean server.
- After restart, verify the chosen port with `/api/health`; do not assume the same port will be reused, because another live chain may already have claimed a different one.
- If a wrapper process is still running but the HTTP server is gone, treat it as a shutdown/restart artifact, not proof that the service is healthy.

### Model / provider fixes
- If Paperclip launches Hermes with `openai-codex`, do not just change a model label.
- Trace the adapter registry and the model-detection path.
- If the correct runtime is LiteLLM/Azure, make sure the adapter returns the actual model ID the proxy exposes (for example `azure/gpt-4o`).
- If the wrong model is coming from a wrapper adapter, override the wrapper’s detection path too.
- In one real incident, `hermes/gpt-4o` was not present in Paperclip repo code; it came from the external `hermes-paperclip-adapter` path. The practical fix on the Paperclip side was to override `server/src/adapters/registry.ts` so `hermes_local` and `openclaw_gateway` both resolved to `azure/gpt-4o`.
- If a helper package still emits the wrong model, a repo-local override in the adapter registry can be the quickest safe fix while you trace the external package separately.
- A direct Hermes smoke test can succeed even when the Paperclip launcher path is still wrong. Verify both: (1) Hermes CLI with the intended config, and (2) Paperclip invoking the adapter path you actually use in production.
- If the Paperclip runtime still selects the wrong provider, check wrapper-generated config and any adapter package defaults before changing the core app.
- If a resumed workflow gets blocked by the dangerous-command gate, the problem may be the approval policy or command shape rather than the model itself. Prefer a safer fetch path and verify auth separately.
- If Paperclip returns Unauthorized, confirm the run exported the claimed API key and base URL before the request.
- If the user asks to change Hermes to a model like gpt-4o, do not stop at the UI label or docs string. Confirm the runtime adapter registry, model detection, and live launch output all agree on the desired model/provider.
- The displayed adapter name can lag behind the real runtime model. Use detected model values and agent launch logs as the source of truth, not the label in the UI.
- If Hermes still shows a model like `azure/gpt-5.4-mini` after a Paperclip-side registry change, trace the actual `detect-model` response and any adapter config persisted on the agent row; the external `hermes-paperclip-adapter` package may be supplying the effective runtime model even when the UI label is changed.
- A small server-side override can be a valid stopgap: patch `server/src/adapters/registry.ts` so `hermes_local` reports the intended model (for example `openai/gpt-4o` or `gpt-4o`) while you continue tracing the external adapter package separately.
- If the Hermes adapter path still launches as `provider=openai-codex` and strips a prefixed model like `azure/gpt-4o`, normalize the wrapper config in the Paperclip adapter registry itself or in the adapter launcher wrapper. Do not rely only on the UI or on `detectModel === false` gates; provider normalization may need to happen whenever the Hermes adapter config is present, while bare-model prefixing remains conditional.
- In the OpenCode local adapter, preserve the explicit parsed model provider before applying OpenAI-compatible billing inference. A fallback like `inferOpenAiCompatibleBiller(env, null) ?? provider` can incorrectly surface `openai-codex`; prefer `provider ?? inferOpenAiCompatibleBiller(env, null) ?? "unknown"` so billing heuristics do not overwrite the runtime provider.
- For Hermes-like wrapper adapters, apply model/provider normalization at the integration boundary (Paperclip registry or launcher wrapper) instead of assuming the downstream CLI will preserve the exact config shape.

### Session resume / placeholder fixes
- If Hermes logs `Resuming session: from`, treat `from` as a placeholder bug, not a real session id.
- Trace the full resume chain: heartbeat/session selection → adapter launch params → CLI resume flag.
- Sanitize resume ids in both the workflow builder and the adapter launcher; reject empty strings and sentinel placeholders like `from`.
- The safest fallback is to start a fresh session when the resume id is invalid, rather than trying to preserve a malformed value.
- Add a regression test at the exact layer that leaked the bad id so the placeholder cannot reappear silently.
- A live Paperclip health check does not prove the resume path is fixed; verify the resumed agent actually launches without a `Session not found` error.
- If a resumed run keeps failing with `Session not found: from`, the bug is in the session propagation path, not the model or Paperclip server itself.

### Host / startup defaults that mattered in practice
- `requestBaseUrl(req)` can silently prefer loopback if `Host` / `X-Forwarded-Host` are missing or mis-set.
- `HOST` from the environment can still override the nicer fallback. Check live env values before assuming the file defaults are used.
- Paperclip’s startup banner should print the reachable host when bound to `0.0.0.0`; otherwise it can mislead you back to localhost.
- Private-host gating needs the reachable host/IP in the allow set or onboarding callbacks will still fail even if the invite text looks correct.

### Hermes verification
- Hermes CLI can fail early due missing runtime deps like `prompt_toolkit` or `pyyaml`.
- If that happens, install dependencies in a clean venv rather than editing production config blindly.
- Then rerun a minimal non-interactive query to confirm the model path end-to-end.
- A successful smoke test with approvals disabled does not prove the resumed automation path is fixed; verify both the direct CLI smoke test and the resumed workflow.

### Codex-local PATH / binary resolution
- If the adapter says `Command not found in PATH: "codex"`, the blocker is the executable resolution path, not `OPENAI_API_KEY`.
- Paperclip's Codex local environment check resolves the configured `command` (default `codex`) before it looks any further; a missing binary fails the adapter run even when auth is present.
- Fixes that usually work: set `env.PATH` in the adapter config to include the Codex install directory, or override `command` with the full absolute path to the Codex binary.
- Do not assume the interactive shell PATH is the same PATH used by Paperclip's adapter runtime.
- Verify the fix by rerunning the adapter environment check and confirming `Command is executable: codex` (or the overridden command), then confirm the run can spawn `codex app-server` successfully.
- When one adapter path works (for example Codex) and another fails, compare the full launcher env and resume path against the working one instead of assuming the model/provider is the problem.
- A successful Codex path can be the control sample: if Codex authenticates while Hermes/OpenClaw fails at `GET /api/agents/me`, the issue is usually claimed API propagation or session resume state, not Paperclip server reachability.
- Look for fallback workspace messages such as `Using fallback workspace ...` because they often indicate the failing path lost per-session auth or claimed-token context.

### When Codex works but other connectors fail
- Treat a working Codex run as evidence that the platform, host reachability, and at least one adapter path are healthy, not as proof that all connectors share the same auth/session wiring.
- Compare the exact launcher command, env injection, resume/session behavior, and workspace selection between the working Codex path and the failing path.
- If logs show `No project or prior session workspace was available...` and a fallback workspace is used, suspect the run lost session-scoped auth/claims and may be starting from a clean workspace without the credentials the successful connector had.
- In that situation, focus on the failing connector’s env propagation and resume logic before changing Paperclip server auth behavior.

## Verification checklist

Confirm all of the following before declaring success:
- The generated onboarding/invite text uses the reachable host, not localhost
- The private-host allowlist accepts the reachable host
- The adapter registry reports the intended model ID
- Hermes/OpenClaw can execute a live query successfully
- No fallback path still emits the old model/provider name

## Pitfalls

- Test fixtures may still contain localhost strings. Do not confuse those with runtime defaults.
- A working direct CLI test does not prove the Paperclip launcher path is fixed.
- A correct hostname in the invite text does not mean the callback/accept path is using the same base URL.
- A model name change in one adapter does not guarantee another adapter wrapper isn’t overriding it.
- If you patch a fallback host, make sure it is only used where appropriate and does not hide real deployment misconfiguration.
