# Worked example: Bifrost (gemma 26B a4b, 1M ctx) wired into rabuntu Hermes + OpenClaw

Session 2026-09-02. Endpoint and topology are Dylan's live mesh — treat values as state, reuse
patterns, re-verify before acting.

## Topology

```
vast L40S (49615348, ssh7.vast.ai): llama-server on :8080 serving huihui gemma-4-26b-a4b
    QAT-abliterated Q4_K, --alias qwen3.8-27b-aggressive, api-key 512e52...
        ^
   lin TCP local-forward: lin:18080 -> vast:8080
        ^
   Bifrost gateway (docker 'bifrost', --network host, lin:8080; tailnet 100.91.55.113:8080;
   auth OFF). openai provider base_url http://localhost:18080 (NO /v1 on THIS one).
        ^ Tailnet
   clients request qwen3.8-27b-aggressive @ http://100.91.55.113:8080/v1
```

The server process runs from `/root/llama.cpp` (NOT `/workspace`, which is empty on this vast
box), started via nohup with stdout to /root/gemma_1m.log; ppid 1 (NOT persistent — dies on
reboot; the lin tunnel is also manual).

## Model identity check (renamed download)

A session had downloaded the model to `/models/gemma-4-26b-a4b-abliterated-Q4_K.gguf` (short
name) and it was already serving. To confirm it was the requested huihui QAT artifact:
`curl -sIL https://huggingface.co/huihui-ai/<repo>/resolve/main/<file>` → content-length
16,796,015,648 == local byte count. Byte-identical multi-GB GGUF => same file. (HF repo API
siblings often omit sizes — use the resolve HEAD.)

## 1M context via YaRN

This llama.cpp build REJECTS `--yarn-factor` ("invalid argument: --yarn-factor"). Correct flags:
`--rope-scaling yarn --rope-scale 4.0 --yarn-orig-ctx 262144` (factor = 1M / 262K = 4.0).
Fits L40S 46GB: ~16.8GB model + ~16GB q8 KV = ~32.7GB used. `n_ctx_seq (1048576) >
n_ctx_train (262144)` in the log is the expected YaRN condition, not an error. Confirm via
`curl /v1/models` → meta.n_ctx = 1048576.

## rabuntu wiring (both agents are ROOT, user@0 systemd)

- Hermes: `/root/.hermes/config.yaml`, gateway = `hermes-gateway.service` (user@0), HERMES_HOME
  /root/.hermes. Added custom_providers `bifrost` (list form; base_url ...:8080/v1, api_mode
  chat_completions, models [qwen3.8-27b-aggressive]) + set top `model:` block to provider bifrost.
  Restart: `XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart hermes-gateway`.
- OpenClaw: `/root/.openclaw/openclaw.json`, gateway = `openclaw-gateway.service` (user@0). Added
  `models.providers.bifrost` (see references/openclaw-models-providers.md) + primary.
- Proved end-to-end: OpenClaw agent turn -> `OPENCLAW_ON_BIFROST`; Hermes one-shot ->
  `HERMES_ON_BIFROST`.

## Pre-existing quirks encountered (NOT caused by this change)

- `/root/.hermes/sessions` is a broken symlink to `/mnt/hermes-profile-nfs/sessions/rabuntu`
  (NFS not mounted). Hermes gateway tolerates it (Errno 17 warnings on resume/kanban); a
  `hermes chat -q` one-shot fails on it — work around with a throwaway `HERMES_HOME=/tmp/hx`.
- OpenClaw `--dry-run` flagged a missing `channels.telegram.dmPolicy` yet `config validate`
  passed after the real patch — dry-run is stricter than validate.
