---
name: model-endpoint-wiring
description: "Wire agents to a self-hosted OpenAI model endpoint."
---

# Self-hosted OpenAI-compatible model endpoint wiring

How to point agents (Hermes, OpenClaw, opencode) at a self-hosted OpenAI-compatible model
server — a `llama-server`/vLLM/LiteLLM instance, or a gateway like Bifrost fronting one —
especially when the server and the target agent live on different machines (Tailscale mesh).

## Golden rules

1. **Serve under a STABLE model alias, not the model's real name.** Backends like llama-server
   expose their GGUF basename as the model id; if every client (Hermes, opencode, kubuntux,
   rabuntu...) requests a hardcoded id like `qwen3.8-27b-aggressive`, then when you swap the
   actual model underneath, launch the server with `--alias <that-same-id>` so ZERO downstream
   config changes are needed. This is why a gemma model runs under a qwen-named alias — it's
   deliberate.
2. **Confirm reachability before touching any agent config**: `curl http://<host>:<port>/v1/models`
   from the TARGET machine. Auth-off gateways accept any/no key.
3. **A gateway's advertised model id is its own namespace** (Bifrost lists `openai/qwen3.8-27b-aggressive`).
   That prefix is the gateway's internal provider name — clients define their OWN provider id and
   send the bare model the server accepts.
4. **Verify a rename is the artifact you think it is** by byte-count, not name: `curl -sIL <HF-resolve-url>`
   and compare `content-length` to the local file. Byte-identical size of a multi-GB GGUF == same file.

## Hermes (custom provider)

Config `~/.hermes/config.yaml` (or `/root/.hermes/config.yaml` for a root gateway):

```yaml
model:
  base_url: http://<server>:<port>/v1
  default: <alias>
  provider: bifrost
  api_mode: chat_completions
custom_providers:
- name: bifrost
  api_key: <key or ${ENV}>
  base_url: http://<server>:<port>/v1
  api_mode: chat_completions
  models:
  - <alias>
```

`model.provider: bifrost` + a `custom_providers` entry named `bifrost` is the working pattern.
Validate the YAML parses (python `yaml.safe_load`). Restart the gateway, then prove with a
one-shot: `hermes chat -q "reply OK"` — if the live home has a broken `~/.hermes/sessions`
symlink that errors on config load, run the one-shot against a throwaway `HERMES_HOME=/tmp/hx`
(copy config + .env, `mkdir /tmp/hx/sessions`) — non-invasive and still uses the real config.

## OpenClaw (custom OpenAI-compatible provider)

For a self-hosted endpoint do NOT use the bundled-plugin flow (plugins bind to hardcoded vendor
hosts). Declare the provider under top-level `models.providers` and set the primary. Full schema
and gotchas live in `references/openclaw-models-providers.md`. Highlights:
- `models.providers.<id>.models` is an array of OBJECTS each requiring `id` + `name` (plain
  strings fail validation: "expected object, received string").
- Apply via `openclaw config patch --file X.patch.json5` (recursive merge, schema-validated);
  back up `openclaw.json` first. Check with `config validate`.
- Verify without restart: `openclaw infer model run --model <provider>/<model> --prompt "ok"`.
  Then `openclaw agents list` (shows resolved model) + `openclaw agent -m "..." --agent main`.

## Remote / root gateway ops (Tailscale nodes)

- Agents often run as ROOT under the **user** systemd instance (`user@0`), NOT a system unit —
  even if `/etc/systemd/system/<name>.service` exists. Confirm from the live process:
  `cat /proc/<pid>/cgroup` → `.../user@0.service/app.slice/<name>.service`. Parent is
  `/lib/systemd/systemd --user`.
- Restart with `XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart <unit>`; a plain
  `systemctl restart <unit>` fails with "Unit not found".
- Root-gateway configs live under `/root/.<tool>/` (e.g. `/root/.openclaw/openclaw.json`, config
  for Hermes at `/root/.hermes/config.yaml` with `HERMES_HOME=/root/.hermes`). Run the CLI as
  root: `sudo -n env HOME=/root XDG_RUNTIME_DIR=/run/user/0 openclaw ...`.
- Reach a lin-hosted gateway from another node over the Tailnet IP (`http://100.x.y.z:<port>/v1`),
  NOT localhost.

## llama.cpp backend notes (YaRN context extension)

- Recent llama.cpp renamed the YaRN factor flag. `--yarn-factor N` is REJECTED ("invalid argument");
  use `--rope-scaling yarn --rope-scale N --yarn-orig-ctx <train_ctx>` where N = target/train.
  E.g. gemma 262144→1,048,576 = factor 4.0. Check your build: `llama-server --help | grep -i yarn`.
- 1M q8_0 KV cache fits a 46GB L40S (~16GB model + ~16GB KV = ~33GB). `n_ctx_seq > n_ctx_train`
  warning in the log is EXPECTED (that's what YaRN is for), not an error.
- Verify the served context really is 1M: `curl /v1/models` and read `meta.n_ctx`.

Worked session detail (Bifrost gateway fronting huihui gemma on a vast L40S, wired into rabuntu
Hermes + OpenClaw over Tailscale): `references/bifrost-gemma-1m-mesh-wiring.md`.
