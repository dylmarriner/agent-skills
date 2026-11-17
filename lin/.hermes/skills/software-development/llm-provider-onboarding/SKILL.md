---
name: llm-provider-onboarding
description: Configure and verify new LLM providers in an app or agent stack, including API-key providers, OpenAI-compatible endpoints, and subscription/OAuth or CLI-auth reuse flows.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [llm, provider, auth, routing, onboarding, api-keys, oauth, openai-compatible]
    related_skills: [authentication-setup, api-integration-builder, codex, hermes-agent]
---

# LLM Provider Onboarding

Use this skill when a user wants to connect a new model provider to an app, especially when the provider is one of:
- a direct API-key provider (DeepSeek, OpenAI, Anthropic, etc.)
- an OpenAI-compatible endpoint (`/v1` base URL, `/models`, `/chat/completions`)
- a subscription/OAuth provider that can be imported from an existing CLI login
- a local runtime or CLI-backed provider that reuses a separate auth/session store

This skill focuses on the class of work, not a single product. The goal is to configure the provider cleanly, route the right workloads to it, and verify the result with the app's own model-discovery or health probe.

## Core workflow

1. Identify the provider class.
   - Native cloud API with its own auth scheme.
   - OpenAI-compatible endpoint with a configurable base URL.
   - CLI/subscription auth reuse path.
   - Local runtime with its own process and model registry.

2. Identify every target application and the requested scope before editing. A provider setup can target multiple apps (for example Hermes and OpenClaw); configure each app's native schema rather than treating one app's JSON as the whole task. Inspect each app's accepted provider identifiers and credential sources before assigning a key. Match issuer/format and schema; similar-looking prefixes are not interchangeable. If a credential is missing or unsupported, configure the parts that can be safely completed and state the precise remaining requirement—do not silently stop after setup for only one target.
   - Does it split chat/reasoning/coding workloads?
   - Does it support a "managed" default plus custom BYO providers?

3. Determine the auth source.
   - API key in a secret store or auth profile.
   - OAuth token or subscription login.
   - Imported CLI auth file (for example `~/.codex/auth.json`).
   - No auth for local runtimes.

4. Set the endpoint correctly.
   - Prefer the documented API base URL, not a full request path, unless the app requires it.
   - For OpenAI-compatible providers, verify the base ends in `/v1` or equivalent and that `/models` is available.
   - If the app probes model lists, make sure the endpoint answers that probe before wiring the UI.

5. Configure the requested target(s) and model.
   - Preserve existing defaults unless the user explicitly asks to switch them; when asked to add/use a model, set the named model in every requested app.
   - Store credentials in each app's supported secret/env mechanism with restrictive permissions; never echo them or place them in shell history when avoidable.
   - If the user supplies an actual key in chat, complete the requested setup when feasible, then recommend rotation because the key is exposed. Do not claim it was rotated.

6. Verify each app independently: validate config, inspect model listing/routing, then make a tiny live completion only when appropriate and report whether live auth was actually tested.
   - Check provider discovery / model listing.
   - Run one tiny chat or health request.
   - Confirm the model id surfaced in the UI matches the intended route.

## Remote and self-hosted endpoints

1. Establish the private path before configuring the client. For a remote GPU host, bind the inference server to remote loopback and forward it through SSH to local loopback; do not expose the model port publicly just to make the client connect.
2. Add the endpoint as a named route when the app supports it, and preserve the existing default provider unless the user explicitly asks to switch defaults.
3. Reuse a protected credential source (`key_env`, keychain/secret store, or the app's supported `key_cmd`) rather than embedding the key in config, shell history, or output.
4. Verify authenticated model discovery and one tiny completion through the final client route. Skip full-context benchmarks unless requested because they consume substantial GPU time.

## Common pitfalls

- Do not confuse subscription/OAuth auth with an API key.
  If the user already has a CLI login, prefer reusing it instead of making them paste a fresh secret.

- Do not wire the full chat-completions path as the base URL unless the app explicitly wants that.
  Many apps expect a bare OpenAI-compatible base such as `/v1` and append their own paths.

- Do not assume provider names and model names are interchangeable.
  The app may want `deepseek:deepseek-chat`, `openai:gpt-5.4`, or a custom slug that points to an endpoint.

- Do not skip the model-list probe.
  A provider can accept auth but still fail on `/models`, which breaks selection UX and leaves a bad config half-installed.

- Do not infer credential compatibility from an `sk-` prefix or assume a key for one router is valid as another router's hosted-account key. Check the target's provider allowlist, environment-variable names, and implementation before configuring it; incompatible keys must not be placed in `.env`, tested against unrelated endpoints, or echoed in output.
- Treat any API key pasted into chat or another exposed channel as compromised: do not repeat it in output, prefer protected storage, and recommend rotation after completing the requested setup when the user supplied it for that setup. Never claim rotation unless verified.
- Do not force users into the wrong auth path.
  Some apps can import another product's login/session file; when that exists, it is the right path for subscription users.

## Verification checklist

- The provider appears in the app's settings or config store.
- The model dropdown or model probe returns at least one model.
- The chosen workload resolves to the intended provider and model.
- Auth survives a restart or config reload.
- If the app supports both cloud and local backends, the new provider does not break the default managed path.

## Reference material

- `references/provider-onboarding-patterns.md` — condensed notes and examples for DeepSeek, OpenAI-compatible endpoints, and CLI-auth reuse.
