---
name: openclaw-litellm-troubleshooting
description: Verify and fix OpenClaw routed through LiteLLM by checking proxy health, enumerating exposed model IDs, aligning OpenClaw config to the exact /v1/models identifier, and smoke-testing chat completions.
metadata:
  category: software-development
---

# OpenClaw + LiteLLM Troubleshooting

Use this skill when OpenClaw is pointed at a LiteLLM proxy but requests fail, the wrong model is selected, or the model name is rejected with a 400 error.

## Additional live troubleshooting lessons

- In this environment, the LiteLLM proxy was reachable on `http://localhost:45564`, not the earlier `4000` guess. `GET /health` returned 200 on `45564`, while `4000` refused connections.
- The proxy-exposed model IDs must be used exactly as returned by `GET /v1/models`. Here, `azure/gpt-5.4-mini` and `azure/gpt-4o` worked, while config entries using unprefixed or guessed names were not enough for host-side resolution.
- OpenClaw’s agent defaults can point at the exact LiteLLM model ID even when the provider model registry still needs its own matching entry. If the host app fails to resolve a model, patch both the agent default and the provider model list so they agree on the same ID.
- Telegram group delivery can fail to appear responsive if `requireMention` is enabled. For bot-style group responses, set `channels.telegram.groups.*.requireMention` to `false` unless mention-only behavior is desired.
- OpenClaw config changes may need a service reload before the channel settings or model settings take effect at runtime.
- OpenClaw invite/onboarding URLs can silently fall back to loopback if the server host is missing or mis-bound. In this environment, a reachable LAN host like `100.93.75.87` had to be used consistently in the server host, allowed-hostname set, and onboarding base URL generation.
- If Hermes or another agent framework resumes a prior session and the command gets blocked by approval policy, the issue is often the approval gate rather than the model itself. For controlled smoke tests, either switch approvals off for the session or use the framework’s explicit approval-bypass path.
- Avoid command pipelines that execute freshly fetched content during smoke tests when a command-approval system is active. Prefer a direct GET plus a safe parser path, or temporarily disable approvals for the test session.

When validating a fix, prefer this sequence:
- `GET /health` should return 200
- `GET /v1/models` should show the target model ID
- `POST /v1/chat/completions` should succeed with that exact ID and a tiny prompt such as `reply with exactly: ok`
- the host app should log the same provider/model path the proxy test used
- if a task still fails, check whether an approval gate, loopback host fallback, or missing channel mention setting is blocking it before touching the model config again


- OpenClaw invite/onboarding URLs can silently fall back to loopback if the server host is missing or mis-bound. In this environment, a reachable LAN host like `100.93.75.87` had to be used consistently in the server host, allowed-hostname set, and onboarding base URL generation.
## Additional live troubleshooting lessons

- In this environment, the LiteLLM proxy was reachable on `http://localhost:45564`, not the earlier `4000` guess. `GET /health` returned 200 on `45564`, while `4000` refused connections.
- The proxy-exposed model IDs must be used exactly as returned by `GET /v1/models`. Here, `azure/gpt-5.4-mini` and `azure/gpt-4o` worked, while config entries using unprefixed or guessed names were not enough for host-side resolution.
- OpenClaw’s agent defaults can point at the exact LiteLLM model ID even when the provider model registry still needs its own matching entry. If the host app fails to resolve a model, patch both the agent default and the provider model list so they agree on the same ID.
- Telegram group delivery can fail to appear responsive if `requireMention` is enabled. For bot-style group responses, set `channels.telegram.groups.*.requireMention` to `false` unless mention-only behavior is desired.
- OpenClaw config changes may need a service reload before the channel settings or model settings take effect at runtime.
- OpenClaw invite/onboarding URLs can silently fall back to loopback if the server host is missing or mis-bound. In this environment, a reachable LAN host like `100.93.75.87` had to be used consistently in the server host, allowed-hostname set, and onboarding base URL generation.
- If Hermes or another agent framework resumes a prior session and the command gets blocked by approval policy, the issue is often the approval gate rather than the model itself. For controlled smoke tests, either switch approvals off for the session or use the framework’s explicit approval-bypass path.
- Avoid command pipelines that execute freshly fetched content during smoke tests when a command-approval system is active. Prefer a direct GET plus a safe parser path, or temporarily disable approvals for the test session.

When validating a fix, prefer this sequence:
- `GET /health` should return 200
- `GET /v1/models` should show the target model ID
- `POST /v1/chat/completions` should succeed with that exact ID and a tiny prompt such as `reply with exactly: ok`
- the host app should log the same provider/model path the proxy test used
- if a task still fails, check whether an approval gate, loopback host fallback, or missing channel mention setting is blocking it before touching the model config again

## Checklist

1. Confirm the LiteLLM proxy is reachable.
   - Health check:
     ```bash
     curl -sS -H 'Authorization: Bearer sk-anything' http://localhost:45564/health
     ```

2. Enumerate the models the proxy actually exposes.
   - Model list:
     ```bash
     curl -sS -H 'Authorization: Bearer sk-anything' http://localhost:45564/v1/models
     ```
   - Use the exact `data[].id` value from this response as the OpenClaw model ID.
   - Example lesson: `gpt-5.4-mini` may be exposed as `azure/gpt-5.4-mini`.

3. Update OpenClaw config to match the proxy.
   - Set provider `baseUrl` to the proxy root, e.g. `http://localhost:45564`.
   - Set `apiKey` to the token the proxy accepts, e.g. `sk-anything` if the proxy is configured that way.
   - Set the model `id` to the exact `/v1/models` identifier.
   - If OpenClaw uses a primary/default model field, set it to the provider-prefixed form, e.g. `litellm/<exact-id>`.

4. Smoke-test chat completions directly against LiteLLM.
   - Example:
     ```bash
     curl -sS http://localhost:45564/v1/chat/completions \
       -H 'Authorization: Bearer sk-anything' \
       -H 'Content-Type: application/json' \
       -d '{"model":"azure/gpt-5.4-mini","messages":[{"role":"user","content":"reply with exactly: ok"}],"max_tokens":10}'
     ```
   - A 400 with “Invalid model name” usually means the OpenClaw model ID does not exactly match the proxy-exposed ID.

5. Re-test after changes.
   - If the proxy is healthy but chat completions still fail, re-check `/v1/models` and patch the config again.

## Common pitfalls

- Using a friendly alias instead of the proxy’s exact model ID.
- Pointing OpenClaw at `/v1/chat/completions` instead of the proxy base URL.
- Assuming the model name without verifying `GET /v1/models`.
- Forgetting that different LiteLLM deployments may prefix models differently.

## Verification outcome

The integration is working only when all of these succeed:
- `GET /health` returns 200
- `GET /v1/models` lists the target model
- `POST /v1/chat/completions` succeeds with that exact model ID
- OpenClaw is configured to use the same exact ID
