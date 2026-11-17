---
name: hermes-custom-providers
description: "Add OpenAI-compatible API providers not built into Hermes (Mistral, Groq, Together, etc.)"
version: 1.0.0
---

# Hermes Custom Providers

How to add an OpenAI-compatible provider (Mistral, Groq, Together AI, Fireworks, etc.) that isn't in the built-in list.

## 🔴 Known Pitfall: Flat `providers` section doesn't work

Setting `providers.<name>.api_key` via `hermes config set` looks right but DOES NOT register the provider. Hermes will reply with "Unknown provider '<name>'".

The `providers` section is for built-in providers only — Hermes has an internal registry of known providers (deepseek, openrouter, google, etc.). Custom ones go under `custom_providers`.

## Correct Setup

### 1. Add entry under `custom_providers` in config.yaml

```yaml
custom_providers:
- name: mistral
  api_key: <your-api-key>
  base_url: https://api.mistral.ai/v1
  api_mode: chat_completions
  models:
    - mistral-small-latest
    - mistral-medium-3.5
    - mistral-large-latest
    # ... full model list
```

The `api_mode` must be `chat_completions` for OpenAI-compatible chat APIs.

### 2. Reference it as `custom:<name>`

```
hermes config set model.provider custom:mistral
hermes --provider custom:mistral chat
```

The `custom:` prefix is required — it tells Hermes to look in `custom_providers` rather than the built-in registry.

### 3. Populate model caches

Hermes caches model lists at startup. For custom providers, the init-time discovery may not populate the caches correctly. Run:

```python
import json, time, requests
resp = requests.get('<provider-base-url>/models', headers={'Authorization': 'Bearer <key>'})
models = sorted(set(m['id'] for m in resp.json()['data']))
entry = {'fp': 'custom:direct', 'at': time.time(), 'models': models}

for cache_path in ['~/.hermes/provider_models_cache.json', '~/.hermes/models_dev_cache.json']:
    with open(os.path.expanduser(cache_path)) as f:
        cache = json.load(f)
    cache['custom:<name>'] = entry
    with open(os.path.expanduser(cache_path), 'w') as f:
        json.dump(cache, f, indent=2)
```

### 4. Verify with a test query

```bash
# FLAG ORDER MATTERS — --provider and --model must come AFTER the subcommand:
hermes chat -q "Say exactly: working" --provider custom:<name> --model <model>

# This does NOT work (ignores the custom provider, uses default model instead):
hermes --provider custom:<name> --model <model> chat -q "..."
```

### API key prefix gotcha

Some providers (Venice, etc.) require the full key string INCLUDING any prefix as the Bearer token. For example, a key like `VENICE_ADMIN_KEY_aogCxFWODj5...` must be stored in `api_key` exactly as-is — the `VENICE_ADMIN_KEY_` prefix is part of the token, not a label to strip. If the API returns "Authentication failed", try the full string including the prefix.

## Remote GPU Backends (RunPod / Cloud)

See `references/remote-gpu-backend.md` for the full pattern:

1. Create RunPod GPU pod with SSH access only
2. Install Ollama, import GGUF model
3. Set up a local proxy on the pod if the model uses Qwen thinking mode
4. SSH tunnel the inference port to localhost
5. Configure as a `custom_providers` YAML entry (NOT via `hermes config set` — that writes JSON strings that break YAML parsing)

### Key differences from standard API providers

| Concern | Standard API | Remote GPU pod |
|---------|-------------|----------------|
| API key | Required | `not-needed` |
| Base URL | Remote HTTPS | `http://localhost:<tunnel-port>` |
| Connection | Direct | SSH tunnel (reconnects needed) |
| Server | Their infra runs it | You manage Ollama/llama.cpp/vLLM |
| Thinking models | Native support | May need proxy to handle `<think>` tags |
