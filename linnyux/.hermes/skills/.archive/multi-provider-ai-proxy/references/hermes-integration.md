# Hermes Integration for AI Proxy Aggregators

Wire a multi-provider aggregator into Hermes as a custom provider + fallback.

## Hermes config.yaml entries

```yaml
# Under custom_providers — the aggregator appears as a selectable model
custom_providers:
  - name: unlimited-free-ai
    base_url: http://localhost:3099/v1
    api_key: ''                         # aggregator is unauthenticated (local)
    models:
      - unlimited-free-ai

# Under fallback_providers — Hermes auto-routes here when main provider fails
fallback_providers:
  - provider: unlimited-free-ai
    model: unlimited-free-ai
```

## Per-machine deployment pattern

| Machine | Aggregator dir | .env keys |
|---------|---------------|-----------|
| **lin** | `~/Documents/unlimited-free-ai/` | Built-in free + lin's OR/DS/Kilo/NVIDIA |
| **kubuntux** | `/mnt/development1/unlimited-free-ai/` | Built-in free + kubuntux's OR/DS/Kilo/NVIDIA |
| **macuntu** | `/home/macuntu/unlimited-free-ai/` | Built-in free + macuntu's OR/DS/Kilo |

## Usage

```bash
# Direct provider
hermes --provider unlimited-free-ai --model unlimited-free-ai

# Or let fallback auto-route
hermes  # will use unrestricted-free-ai if primary fails
```

## Resetting custom_providers from JSON string to YAML list

The `hermes config set` command stores values as JSON strings, not proper YAML. To fix:

```python
import yaml, json
with open("~/.hermes/config.yaml") as f:
    data = yaml.safe_load(f)
cp = data.get("custom_providers", [])
if isinstance(cp, str):
    cp = json.loads(cp)
data["custom_providers"] = cp
with open("~/.hermes/config.yaml", "w") as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
```

## CIFS/NFS mount optimization

When deploying across machines that share a CIFS mount:

```
# Client mount options (biggest win)
actimeo=60   # 60x fewer metadata queries (was actimeo=1)
vers=3.0     # SMB 3.0

# Samba server options
aio read size = 16384
aio write size = 16384
server signing = disabled
use sendfile = yes
read raw = yes
write raw = yes
```
