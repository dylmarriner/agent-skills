---
name: llm-integration-end-to-end-verification
description: End-to-end verification workflow for app-to-proxy LLM integrations where provider selection, model IDs, and public hostnames can diverge from the intended config.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# LLM Integration End-to-End Verification

Use this skill when an app is supposed to route through an OpenAI-compatible proxy or another LLM gateway, but the live runtime does not match the configured model/provider.

## When to use

- A direct proxy test works, but the host app still fails
- The app logs show a different provider than expected
- A friendly model name works in config but fails at runtime
- An invite/onboarding URL or callback URL resolves to loopback or localhost
- The host app needs a public/reachable base URL for another machine

## Workflow

1. Identify the real runtime path the app is using.
2. Verify the proxy health and model list directly.
3. Send a one-shot chat/completions request with the exact model id returned by the proxy.
4. Compare the app’s selected provider/model against the proxy’s actual response.
5. Fix the smallest layer that is wrong:
   - model id mapping
   - provider selection
   - base URL / hostname generation
   - dependency/runtime environment
6. Re-run the live request until the real runtime response succeeds.

## Verification ladder

Use this order:

- health endpoint responds
- model list endpoint returns the expected model id
- one-shot completion succeeds with the exact model id
- host app logs show the intended provider
- app-level request succeeds end to end

## Common pitfalls

- Friendly labels are not always valid model ids
- A proxy may accept any bearer token while still rejecting unknown model names
- The app may silently choose a different provider path than the one configured
- Loopback can appear in generated onboarding or callback URLs even when the invite text looks correct
- A missing runtime dependency can look like an LLM routing problem
- A runtime launcher can override the configured provider/model entirely; if the live log shows a different provider than the config file, trust the log and trace the wrapper or adapter layer before editing config again.
- When a runtime strips a provider prefix from a model name (for example `azure/gpt-4o` -> `gpt-4o`), treat that as evidence of normalization in the launcher path, not proof that the proxy config is wrong.

## Useful heuristics

- Trust the live proxy response over the UI label
- Trust the app log over the intended config if they disagree
- If the runtime provider is wrong, fix provider selection before changing model names
- If the URL is unreachable from the other machine, fix host generation before retrying onboarding

## Done means

A change is complete only when the live request succeeds through the same path the host app actually uses.
