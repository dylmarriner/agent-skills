# Venice AI Custom Provider Setup

Venice (api.venice.ai) provides access to 89+ models including deepseek, qwen, claude, gemini, grok, kimi, and uncensored models.

## Hermes Config

```yaml
custom_providers:
- name: venice
  api_key: "VENICE_ADMIN_KEY_<full-token-including-prefix>"
  base_url: https://api.venice.ai/api/v1
  api_mode: chat_completions
  models:
    - deepseek-v4-flash
    - deepseek-v4-pro
    - qwen3-235b-a22b-thinking-2507
    - venice-uncensored-1-2
    - venice-uncensored-role-play
    - e2ee-qwen3-6-35b-a3b-uncensored-p
    - e2ee-venice-uncensored-24b-p
    - kimi-k2-6
    - claude-opus-4-8
    - gemini-3-5-flash
    - grok-4-20
```

## Usage

```bash
hermes chat --provider custom:venice --model deepseek-v4-flash
hermes chat --provider custom:venice --model venice-uncensored-1-2
hermes chat --provider custom:venice --model qwen3-235b-a22b-thinking-2507
```

## Key Format

The full `VENICE_ADMIN_KEY_...` string IS the token — do not strip the prefix. Store it exactly as-is in `api_key`.

## Model Cache

After adding, populate the model cache so Hermes recognizes all 89 models immediately:

```python
import json, time, os, urllib.request

req = urllib.request.Request(
    'https://api.venice.ai/api/v1/models',
    headers={'Authorization': 'Bearer <full-key>'}
)
data = json.loads(urllib.request.urlopen(req).read())
models = sorted(set(m['id'] for m in data['data']))
entry = {'fp': 'custom:direct', 'at': time.time(), 'models': models}

for cache_rel in ['provider_models_cache.json', 'models_dev_cache.json']:
    cache_path = os.path.expanduser(f'~/.hermes/{cache_rel}')
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    cache['custom:venice'] = entry
    json.dump(cache, open(cache_path, 'w'), indent=2)
```

## OpenClaw Integration

Venice has a bundled plugin in OpenClaw. See `openclaw-provider-setup` skill for setup steps.
