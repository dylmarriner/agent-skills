# Gateway & endpoint triage

Depth for the probe steps: gateway protocol detection, model-ID enumeration, self-healing config cleanup, and failure signatures worth recognising on sight.

## Protocol detection

An OpenAI-shaped gateway will happily answer `/v1/models` and still be useless to an Anthropic-protocol client.

| Response | Meaning |
|---|---|
| `405` on `POST /v1/messages` | no Anthropic route mounted at that path |
| `400` on `POST /anthropic/v1/messages` | Anthropic route EXISTS — use `<base>/anthropic` as the client base URL |
| `400 could not auto resolve a provider` | gateway up, upstream provider(s) unreachable |
| `502 provider_connection_failed`, `dial tcp 127.0.0.1:<port>: connection refused` | gateway's own model servers are down |
| empty `data: []` from `/v1/models` | providers failed to enumerate; aliases cannot resolve |
| `401` from the provider API with no auth header | network path to the provider is fine — the problem is local config |

```bash
for p in /v1/messages /anthropic/v1/messages; do
  printf '%s -> ' "$p"
  curl -sS -m6 -o /dev/null -w '%{http_code}\n' -X POST "http://HOST:PORT$p" \
    -H 'content-type: application/json' -d '{}'
done
```

## Enumerate real model IDs from the stored OAuth token

```python
import json, urllib.request
d = json.load(open('$HOME/.claude/.credentials.json'))
tok = d['claudeAiOauth']['accessToken']
req = urllib.request.Request(
    'https://api.anthropic.com/v1/models?limit=100',
    headers={'Authorization': 'Bearer ' + tok,
             'anthropic-version': '2023-06-01',
             'anthropic-beta': 'oauth-2025-04-20'})
print([m['id'] for m in json.load(urllib.request.urlopen(req, timeout=20))['data']])
```

Use the returned IDs verbatim — an alias prefix or a guessed version suffix will not match. Check `expiresAt` (ms epoch) in the same file to confirm the token is live before blaming credentials.

## Clean a self-healing settings baseline

```bash
HEAL=~/.claude/plugins/data/<plugin>/config/settings_heal
cd "$HEAL"
python3 - <<'EOF'
import json, datetime
h = json.load(open('highwater.json')); h.pop('KEY', None)
json.dump(h, open('highwater.json', 'w'), indent=2)
m = json.load(open('highwater.meta.json'))
m['key_count'] = len(h); m['key_set'] = sorted(h)
json.dump(m, open('highwater.meta.json', 'w'), indent=2)
json.dump({'tombstoned_keys': ['KEY'], 'updated': datetime.datetime.now().isoformat()},
          open('tombstones.json', 'w'), indent=2)
EOF
```

`heal_log.jsonl` records `snapshot` and `restore` actions with their `key_set` — read it to learn whether a heal or a manual edit put a key back. `last_healthy.json` carries the last good `key_count`.

## Failure signatures

- `curl: (7) ... Could not connect to server after 0 ms` — nothing bound; the "firewall" wording is fiction.
- CLI print-mode hang, zero stdout, exit only on `timeout` — client retry loop against a refused endpoint.
- Perfect auth, every request `model not found` — a gateway alias left in place while routing bypassed the gateway.
- A key returns after deletion — snapshot healer, not the CLI.
- Endpoint answers but `/v1/models` is empty — the gateway's providers are down; a base-URL fix alone will not make the CLI work.
