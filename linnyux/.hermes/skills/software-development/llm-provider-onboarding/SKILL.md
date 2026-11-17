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

2. Find the app's routing grammar.
   - Does it use `slug:model`, `provider:model`, or a dedicated provider selector?
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

5. Route one workload first.
   - Wire a single low-risk workload (often chat) before fanning out to reasoning/coding/vision.
   - Confirm the app accepts the provider string and model id without falling back to default routing.

6. Verify end-to-end.
   - Check provider discovery / model listing.
   - Run one tiny chat or health request.
   - Confirm the model id surfaced in the UI matches the intended route.

## Common pitfalls

- Do not confuse subscription/OAuth auth with an API key.
  If the user already has a CLI login, prefer reusing it instead of making them paste a fresh secret.

- Do not wire the full chat-completions path as the base URL unless the app explicitly wants that.
  Many apps expect a bare OpenAI-compatible base such as `/v1` and append their own paths.

- Do not assume provider names and model names are interchangeable.
  The app may want `deepseek:deepseek-chat`, `openai:gpt-5.4`, or a custom slug that points to an endpoint.

- Do not skip the model-list probe.
  A provider can accept auth but still fail on `/models`, which breaks selection UX and leaves a bad config half-installed.

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
