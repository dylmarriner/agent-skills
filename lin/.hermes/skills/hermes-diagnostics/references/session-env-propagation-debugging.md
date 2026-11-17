---
name: hermes-session-env-propagation-debugging
description: Diagnose Hermes 401/Unauthorized failures caused by resumed sessions or launchers not inheriting live PAPERCLIP_API_KEY / PAPERCLIP_API_URL environment.
---

# Hermes Session Env Propagation Debugging

Use this when a Hermes run or resumed session can reach Paperclip, but Paperclip replies 401 Unauthorized even though the current shell appears configured.

## Symptoms
- Hermes resumes an old session and starts making API calls.
- The current shell has `PAPERCLIP_API_KEY` and `PAPERCLIP_API_URL`, but the resumed session still gets 401.
- The failure is in Hermes startup/resume/web-server plumbing, not in OpenClaw connectivity.

## Workflow

1. Confirm the live shell environment.
   - Check `PAPERCLIP_API_KEY` and `PAPERCLIP_API_URL` in the current shell.
   - Confirm the claimed key file exists if the workflow uses one.

2. Verify the failing session is actually stale.
   - Note the session ID and whether the error comes from a resumed run.
   - Treat `Session not found` and `Unauthorized` as separate clues.

3. Trace Hermes startup/resume env propagation.
   - Inspect the launcher, session resume path, or web server path that creates the agent process.
   - Look for code that reads `.env`, inherits `os.environ`, or strips env vars on exec.

4. Compare the working and failing paths.
   - A fresh Hermes smoke test may work while a resumed session fails.
   - If so, the bug is usually the resume path, not the model/provider config.

5. Fix the narrowest propagation break.
   - Ensure the exact runtime process that makes the Paperclip request has the live credentials and base URL.
   - Avoid changing Paperclip auth logic unless the request headers are actually wrong.

6. Re-test with a fresh Hermes process.
   - Do not reuse the stale resumed session.
   - Confirm the API call now succeeds with the same shell state.

7. For long-lived gateway processes, refresh runtime configuration right before dispatch.
   - Startup-only loading can be stale after credentials change.
   - Re-read the active Hermes config in the request path so resumed sessions do not keep using old auth state.

## Common pitfalls
- Conflating OpenClaw gateway health with Hermes auth failures.
- Assuming a shell export automatically reaches a resumed child process.
- Fixing Paperclip when the real issue is Hermes not loading the env.
- Reusing a stale session after auth settings changed.
- Missing `PAPERCLIP_AGENT_JWT_SECRET` in the running Paperclip process, which causes heartbeat to skip injected `PAPERCLIP_API_KEY` for all local-JWT-capable adapters.
- Treat `hermes_local` as a special auth path: in Paperclip it uses the same local JWT helper as `codex_local`; if the secret is present, both should mint the same kind of injected auth.
- Looking for a Hermes adapter implementation inside the Paperclip repo when the package is external/vendored elsewhere; in that case, only the Paperclip integration points (heartbeat/session injection, adapter registry, launch env) are available to patch here.
- Missing local-agent JWT secret causes Paperclip to silently drop PAPERCLIP_API_KEY injection for supported adapters; check for the startup warning `local agent jwt secret missing or invalid; running without injected PAPERCLIP_API_KEY`.
- If the startup banner says the secret was found in `.paperclip/.env` but not loaded, the runtime process is missing the secret even if the file is present; fix process/env propagation, not just the file.
- Treat `hermes_local` and `codex_local` as sharing the same local JWT helper path in Paperclip; if one works and the other fails with `/api/agents/me` Unauthorized, compare the runtime envelope rather than assuming a Hermes-only auth stack.
- Session-management wiring matters for Hermes too: if the adapter registry omits `sessionManagement: getAdapterSessionManagement("hermes_local") ?? undefined`, Hermes can fall back to a workspace/session shape that never receives the same launch-time auth envelope as Codex.
- Model detection should reflect the runtime path actually used by Hermes; normalize detected values to the same model/provider shape that the adapter launcher expects so the run does not drift into an unintended fallback or normalization branch.
- If the user asks for a specific Hermes model such as gpt-4o, update the actual adapter/model detection source of truth instead of only changing the UI label; the label alone does not change the runtime model.
- When Hermes logs `provider=openai-codex [modelInference]` or strips `azure/` from a model like `azure/gpt-4o`, suspect the external `hermes-paperclip-adapter` config builder/model inference logic rather than Paperclip auth. Verify whether the adapter package is rewriting provider/model before Paperclip-side fixes.
- If Paperclip-side normalization is needed, apply it before the Hermes adapter package runs so the launcher never receives a shape that triggers Codex inference.
- Use live adapter output, not the displayed adapter name, to confirm the runtime model/provider the Hermes process actually selected.

## Verification
- Current shell and Hermes runtime both show the same Paperclip env values.
- A fresh Hermes run and a resumed Hermes run both authenticate successfully.
- Hermes adapter registration includes session-management wiring and uses a model/provider value that matches the live launch path.
- Paperclip no longer returns 401 for the intended API call.
