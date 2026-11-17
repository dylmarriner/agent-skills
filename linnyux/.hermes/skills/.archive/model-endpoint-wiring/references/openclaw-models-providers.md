# OpenClaw: declare a custom OpenAI-compatible provider (self-hosted gateway)

Verified against OpenClaw 2026.5.3-1 config schema (auth via `openclaw config schema`).

## The config shape

Add a top-level `models` block (config has none by default). Each provider entry is free-form;
no bundled plugin is needed because the endpoint supplies its own `api` format:

```json5
// provider.patch.json5 — apply with:  openclaw config patch --file provider.patch.json5
{
  models: { providers: { bifrost: {
    baseUrl: "http://100.91.55.113:8080/v1",   // INCLUDE /v1
    apiKey: "<key-or-env>",                    // field required even when the gateway has auth OFF
    auth: "api-key",
    api: "openai-completions",                 // valid: openai-completions / openai-responses / ...
    models: [
      // models is an ARRAY OF OBJECTS, each REQUIRING id + name
      { id: "qwen3.8-27b-aggressive", name: "Friendly", contextWindow: 1048576 }
    ]
  }}}
}

// then point the primary agent at it (same patch file or a second one):
// agents.defaults.model.primary = "bifrost/qwen3.8-27b-aggressive"
// agents.defaults.models["bifrost/qwen3.8-27b-aggressive"] = { alias: "Friendly" }
```

## Schema gotchas

- `models.providers.<id>.models` items are OBJECTS requiring `id` + `name`. Passing plain
  strings fails: `Invalid input: expected object, received string`.
- The full agent model id is `"<providerId>/<modelId>"`. OpenClaw strips the provider prefix
  and POSTs `<modelId>` to `baseUrl` — so `<modelId>` MUST equal the model name the server
  actually accepts (check `curl <baseUrl>/v1/models`).
- A gateway's own advertised id is irrelevant to clients: Bifrost lists `openai/qwen3.8-27b-aggressive`
  (its internal provider namespace). Define YOUR provider id and use the bare served model.
- `openclaw config patch` is a recursive merge; arrays/scalars replace. It auto-writes a `.bak`.
  A `--dry-run` may report UNRELATED pre-existing errors (e.g. `channels.telegram.dmPolicy`
  missing) yet still apply for real — trust `openclaw config validate` afterward.

## Safe edit workflow (never hand-edit the whole JSON)

```bash
cp /root/.openclaw/openclaw.json /root/.openclaw/openclaw.json.bak-$(date +%s)
openclaw config patch --file provider.patch.json5 --dry-run   # schema check
openclaw config patch --file provider.patch.json5
openclaw config validate
python3 -c "import json;d=json.load(open('/root/.openclaw/openclaw.json'));print(d['models'])"
```

## Verify (in increasing strength)

```bash
openclaw infer model run --model bifrost/qwen3.8-27b-aggressive --prompt "reply ok"  # local one-shot
openclaw agents list                       # shows agent -> Model: bifrost/qwen3.8-27b-aggressive
openclaw agent -m "reply ok" --agent main  # real gateway turn on the primary (agent id from list)
```

## Gateway process supervision (the #1 restart trap)

The gateway usually runs under ROOT's **user** systemd, not a system unit:

```bash
cat /proc/<gwpid>/cgroup        # → .../user@0.service/app.slice/openclaw-gateway.service
ps -o ppid= -p <gwpid>          # parent = /lib/systemd/systemd --user
XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart openclaw-gateway   # works
systemctl restart openclaw-gateway                                      # FAILS: Unit not found
```

Config lives at `/root/.openclaw/openclaw.json`; run the CLI as root:
`sudo -n env HOME=/root XDG_RUNTIME_DIR=/run/user/0 openclaw ...`
