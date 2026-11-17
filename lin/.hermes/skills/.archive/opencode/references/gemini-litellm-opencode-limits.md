# Gemini-LiteLLM Integration Limits with OpenCode

When using a LiteLLM proxy (e.g., for Vertex AI models) with the OpenCode CLI, model discovery is limited by OpenCode's internal hardcoded model catalog.

## The Limitation
OpenCode CLI relies on a dynamic model registry, but it does NOT dynamically discover models from an OpenAI-compatible endpoint (like LiteLLM proxy). Even if the proxy returns a list of available models via `/v1/models`, OpenCode will only allow models it recognizes in its internal catalog.

## Troubleshooting
If `opencode models <provider>` does not list your proxy-provided model, you cannot call it via the CLI binary. 

## The Workaround (Paperclip Adapters)
If you are using the Paperclip fork (`feat/externalize-hermes-adapter`), the adapter plugin architecture bypasses the CLI binary's catalog entirely.
- In the Paperclip Board UI → Adapter Manager → Hermes Adapter, you can manually input the model ID (e.g., `gemini-3.1-flash-lite`).
- The adapter plugin directly communicates with your proxy and will succeed, whereas the OpenCode CLI binary would return a `ProviderModelNotFoundError`.

## Direct Proxy Registration (Advanced)
If you are strictly bound to using the CLI and must force a model, manually adding the model entry to `~/.local/share/opencode/auth.json` or providing it via `opencode.json` provider overrides *may* work, but experience shows that if the model ID is not present in the internal binary catalog, the effect loop `ProviderModelNotFoundError` is the expected result regardless of proxy configuration.
EOF
