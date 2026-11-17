# LiteLLM Proxy Debugging and Management

This reference contains notes and commands for troubleshooting LiteLLM proxy issues, which are common when integrating local LLM routing with the Hermes Agent.

## Common Issues & Fixes

- **Two config files — editing the wrong one:** Hermes has both `~/.hermes/config.yaml` (main config, 400+ lines, contains all settings) and `~/.config/hermes/config.yaml` (small, may be CLI-related or legacy). Commands like `hermes config edit` open the main one. The `auto_jailbreak()` function from the godmode skill writes to `~/.hermes/config.yaml`. If you edit `~/.config/hermes/config.yaml`, your changes may have no effect. Always check which file you're modifying.

- **400 Bad Request / "Invalid model name"**:
  - Check `~/.litellm/config.yaml` to ensure the requested model alias (e.g., `gemini-3.1-flash-lite`) maps correctly to the actual provider model string (e.g., `vertex_ai/gemini-3.1-flash-lite-preview`).
  - Restart the proxy service: `systemctl --user restart litellm-vertex.service`.
  
- **400 Bad Request / "No connected db"**:
  - **COUNTERINTUITIVE SIGNAL:** This is actually an API KEY MISMATCH, not a database issue. When the `api_key` passed in the request doesn't match the proxy's `master_key` (`general_settings.master_key` in `litellm-config.yaml`), LiteLLM returns HTTP 400 with `{'error': {'message': 'No connected db.', 'type': 'no_db_connection', 'code': '400'}}`.
  - Every strategy/attempt will fail uniformly with this error — use it as a diagnostic: if ALL requests to the proxy return "No connected db.", the api_key is wrong.
  - Fix: pass the exact value of `general_settings.master_key` from the LiteLLM config file as the api_key. The Hermes config's `model.api_key` may differ from the proxy's expected key.
  - Some clients (OpenClaw with `authHeader: false`) skip auth entirely and will work fine — the error only surfaces when auth IS sent but with the wrong key.
  
- **401 Unauthorized**:
  - The request is missing an API key. Ensure `hermes config` has the correct `api_key` pointing to the LiteLLM `master_key` configured in `litellm-config.yaml`.

- **Model name mismatch (400 error only for some models)**:
  - If `model.default` works but `agent.model` fails with 400, check for provider prefixes. With `model.provider: custom:litellm`, model names must be bare (e.g., `gemini-3.1-flash-lite`, NOT `gemini/gemini-3.1-flash-lite`).
  - If you see `gemini/` prefix in `agent.model` in config.yaml, the Hermes provider is likely set to `openrouter` but routing to a local proxy. Fix: change `model.provider` to `custom:litellm` and drop the prefix.
  - See `references/litellm-model-prefix-insight.md` for the full routing table.

- **"Connected by OpenRouter" but pointing to local LiteLLM**:
  - When `model.provider: openrouter` and `model.base_url: http://localhost:4000/v1`, Hermes thinks it's talking to OpenRouter. Model names with `gemini/` prefix (OpenRouter format) are sent verbatim to the local proxy, which can't match them.
  - Fix: change to `model.provider: custom:litellm` with a `custom_providers.litellm` section matching the same base_url and api_key, and use bare model names.

## Diagnostic Commands
- Check service status: `systemctl --user status litellm-vertex.service`
- Verify model availability: `curl -s http://localhost:4000/v1/models | jq .`
- Check proxy process: `ps aux | grep litellm`
