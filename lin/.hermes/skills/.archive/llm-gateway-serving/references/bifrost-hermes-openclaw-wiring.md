# Bifrost → Hermes → OpenClaw wiring details (mesh)

Exact config shapes + verification for pointing the mesh agents at a gateway-served model. Mesh gateways on rabuntu run as **root under the user@0 systemd instance** (`/root/.hermes`, `/root/.openclaw`). Client-side the endpoint is always `http://100.91.55.113:8080/v1` (Bifrost on lin, reachable over tailnet), model alias `qwen3.8-27b-aggressive`, auth off. All clients request the same alias — that is what makes model swaps drop-in.

## Bifrost (lin) — the gateway

- docker `bifrost`, `--network host`, listens lin:8080 / tailnet 100.91.55.113:8080. `auth_enabled: false` (sends/receives any key).
- Its own openai provider points at the model server via a local forward: `~/bifrost/data/config.json` → `providers.openai.network_config.base_url = http://localhost:18080` — **NO `/v1` suffix in bifrost's own cfg**.
- `GET http://100.91.55.113:8080/v1/models` returns ids prefixed `openai/<alias>` (e.g. `openai/qwen3.8-27b-aggressive`) — that is bifrost's namespace, NOT something you type into OpenClaw/Hermes.
- Test: `curl -s http://localhost:8080/v1/chat/completions -H 'Authorization: Bearer sk-local' -d '{"model":"qwen3.8-27b-aggressive","messages":[{"role":"user","content":"..."}]}'`.

## Hermes (each node) — custom_providers

Add an entry under top-level `custom_providers:` (list form) and point the top `model:` block at it. Proven shape (mirror on every machine; rabuntu's is `/root/.hermes/config.yaml`):

```yaml
model:
  base_url: http://100.91.55.113:8080/v1   # WITH /v1 for the client
  default: qwen3.8-27b-aggressive
  provider: bifrost
  api_mode: chat_completions

custom_providers:
- name: bifrost
  api_key: <key>          # auth off at bifrost; any non-empty value
  base_url: http://100.91.55.113:8080/v1
  api_mode: chat_completions
  models:
  - qwen3.8-27b-aggressive
```

`model.provider` = the custom_providers `name`; the custom_providers entry supplies base_url + api_key. Do NOT `yaml.dump()` the whole file to edit (reorders everything) — targeted patch / heredoc insert.

Restart the running gateway as root user instance:
```bash
sudo -n env HOME=/root XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart hermes-gateway
```

### Verify Hermes→model without touching the live gateway

A one-shot against the live config may fail if the gateway's sessions dir is a **broken symlink to an unmounted NFS target** (`/root/.hermes/sessions → /mnt/hermes-profile-nfs/...` → `FileExistsError` on mkdir). Reusable workaround — copy the real config + `.env` into a throwaway HERMES_HOME with a real `sessions/` dir, run the one-shot there:
```bash
rm -rf /tmp/hx && mkdir -p /tmp/hx/sessions
cp /root/.hermes/config.yaml /tmp/hx/config.yaml && cp /root/.hermes/.env /tmp/hx/.env 2>/dev/null
HERMES_HOME=/tmp/hx /usr/local/bin/hermes chat -q "Reply with exactly: OK" --quiet
rm -rf /tmp/hx
```

## OpenClaw (rabuntu) — custom OpenAI-compatible provider

Config path is top-level `models.providers.<providerId>` (NOT agents.defaults.models — that only lists model ids + aliases). Apply with the validated patch CLI, never hand-edit blindly:
```bash
openclaw config patch --file ./patch.json5 --dry-run   # then without --dry-run
openclaw config validate
```
Patch JSON5 (provider id is arbitrary; use a fresh name to avoid clobbering the bundled `openai` plugin and its modelPrefix gating):
```json5
{
  models: { providers: { bifrost: {
    baseUrl: "http://100.91.55.113:8080/v1",
    apiKey: "<key>",
    auth: "api-key",
    api: "openai-completions",
    models: [ { id: "qwen3.8-27b-aggressive", name: "Bifrost 1M", contextWindow: 1048576 } ]
  }}},
  agents: { defaults: {
    model: { primary: "bifrost/qwen3.8-27b-aggressive" },
    models: { "bifrost/qwen3.8-27b-aggressive": { alias: "Bifrost 1M" } }
  }}
}
```
- `models` under a provider is an **array of objects requiring `id` and `name`** — plain strings are rejected by schema validation.
- `contextWindow` optional; set it to the served ctx.
- Model reference format is `<providerId>/<id>`; OpenClaw strips the provider prefix and sends `<id>` to the endpoint.
- Full config schema: `openclaw config schema` (authoritative for the `models.providers` shape).

Restart + verify:
```bash
sudo -n env HOME=/root XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart openclaw-gateway
openclaw agents list                       # expect: Agent main → Model: bifrost/qwen3.8-27b-aggressive
```
### Test BEFORE flipping primary (don't strand a live gateway)
```bash
openclaw infer model run --model bifrost/qwen3.8-27b-aggressive --prompt "Reply with exactly: OK"
# → provider: bifrost, model: qwen3.8-27b-aggressive, output OK   (uses --local by default; no gateway needed)
```
A full gateway turn needs a bound agent: `openclaw agent -m "..." --agent main` (use the real id from `openclaw agents list`; `--agent default` fails with `Unknown agent id`).

### OpenClaw gotchas
- `systemctl restart openclaw-gateway` as a SYSTEM unit says `Unit not found` — it is a **user@0** unit (`systemctl --user ...`, XDG_RUNTIME_DIR=/run/user/0). Find the unit from `cat /proc/<gwpid>/cgroup`.
- `openclaw config patch` real run may succeed where `--dry-run` reports unrelated pre-existing validation noise (e.g. telegram dmPolicy); trust `openclaw config validate` after the real patch.
- Bundled provider plugins (`openai`, `qwen`, `deepseek`, `litellm`…) bind endpoints by host via `providerEndpoints`; a `models.providers.<id>` override with explicit `baseUrl` + `api` + `models` bypasses that for arbitrary OpenAI-compatible servers.
- `pgrep -f` pollution: match on exact name (`pgrep -ax`) when your command string itself contains the target text.

## Multi-model / real names (two co-resident backends)

llama.cpp serves ONE model per llama-server → two servers, one TCP forward each (lin:18080→vast:8080, lin:18082→vast:8081). Give each llama-server its real `--alias`. Right-size contexts to the GPU (SKILL.md KV formula; 27B@384K + 9B@192K ≈ 41GB on the 46GB L40S — both at 1M won't fit).

Bifrost dual-provider `~/bifrost/data/config.json` — the second openai-compatible backend MUST use a known provider key or a custom key with `base_provider_type`:
```jsonc
"providers": {
  "openai": {                                   // first backend (existing type key)
    "keys": [{ "name": "qwythos-9b-l40s", "value": "<key>",
               "models": ["qwythos-9b-claude-mythos-5-1m"], "weight": 1.0 }],
    "network_config": { "base_url": "http://localhost:18080",
                        "allow_private_network": true, "default_request_timeout_in_seconds": 300 }
  },
  "qwythos27b": {                               // custom name → declare the base type
    "custom_provider_config": { "base_provider_type": "openai" },
    "keys": [{ "name": "qwythos-27b-l40s", "value": "<key>",
               "models": ["qwythos-27b-v1"], "weight": 1.0 }],
    "network_config": { "base_url": "http://localhost:18082", "allow_private_network": true,
                        "default_request_timeout_in_seconds": 300 }
  }
}
```
- Omitting `custom_provider_config` on a non-standard key → runtime `unsupported provider: <key>` (the map key is read as the provider TYPE).
- `/v1/models` returns provider-prefixed ids (`openai/qwythos-9b-…`, `qwythos27b/qwythos-27b-v1`), but clients send the BARE model name and Bifrost routes it. Verify both bare names with a completion each before touching clients.

Config_store stale-state fix:
- Bifrost persists provider keys/models in `/app/config.db` — the container workdir is `/app` and `config_store.config.path` is `./config.db`, so it is NOT under the mounted `/app/data` dir. Editing config.json alone leaves retired models (e.g. an old alias) still listed.
- Clear and reseed: `docker cp bifrost:/app/config.db <backup> && docker exec bifrost rm /app/config.db && docker restart bifrost`. Then `/v1/models` shows exactly config.json's models.

Coordinated rename (retiring the drop-in alias) — order matters, else agents hit 503:
1. Restart both vast servers with real `--alias`es; verify each port's `/v1/models`.
2. Add the second tunnel; restart Bifrost; verify `/v1/models` shows both new names and no stale ones (clear config.db if not).
3. THEN update clients to real names — lin/kubuntux/rabuntu Hermes `custom_providers` (`models:` + top `model.default`), their opencode.json `provider.bifrost` (`models:` + top `model`), rabuntu OpenClaw `models.providers.<id>.models` + `agents.defaults.model.primary`. Restart each rabuntu gateway as root (`sudo -n bash -s` + HOME/XDG_RUNTIME_DIR, user@0).

Machine note: mesh Hermes configs are Syncthing-synced from the lin master, so editing lin's config (via `hermes config set`) auto-propagates to e.g. kubuntux — edit the master, not the synced copy.
