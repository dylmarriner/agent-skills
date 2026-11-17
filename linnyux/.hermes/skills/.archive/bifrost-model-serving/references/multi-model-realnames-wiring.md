# Multi-model real-name serving: Qwythos-27B + Qwythos-9B on one L40S

Session-specific working recipe for serving TWO GGUF models behind Bifrost under their real names (mode B in SKILL.md). Captured from the 2026-09-02 deployment.

## Models (real ids + native-context facts)

| id served | model | file on vast `/models/` | native ctx | ctx actually served |
|---|---|---|---|---|
| `qwythos-9b-claude-mythos-5-1m` | huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated Q4_K | `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf` (5.78 GB) | 1,048,576 (native; max_position_embeddings 1048576, no rope_scaling) | 196,608 |
| `qwythos-27b-v1` | empero-ai/Qwythos-27B-v1 (GGUF) Q4_K_M | `Qwythos-27B-Q4_K_M.gguf` (17.31 GB) | YaRN 4.0 over original 262144 (rope_scaling present -> NOT native) | 393,216 |

Both are Qwen3.5 hybrid (qwen3_5_text): 64/32 layers, `full_attention_interval: 4`, only the full-attention layers carry KV -> big contexts are cheap.

## VRAM reality (46 GB L40S, instance 49615348)
- 9B @ 1M q8 = ~28 GB (so a 27B CANNOT join at useful ctx while 9B sits at 1M).
- Co-resident verified combo: 9B@192K + 27B@384K q8 = ~41 GB/46 GB (4-5 GB headroom).
- Dense 27B @ 1M q8 alone ~= 50 GB -> does not fit at all; the hybrid is what makes big ctx feasible.

## Two llama-servers on vast (ports 8080 / 8081)

9B (port 8080, real id):
```
./build/bin/llama-server -m /models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf \
  --host 0.0.0.0 --port 8080 --alias qwythos-9b-claude-mythos-5-1m --api-key <KEY> \
  -c 196608 --parallel 1 --batch-size 2048 --ubatch-size 512 -ngl 999 \
  --flash-attn on --jinja --reasoning off --cache-type-k q8_0 --cache-type-v q8_0
```

27B (port 8081, real id, YaRN 384K = 1.5x of 262144 native):
```
./build/bin/llama-server -m /models/Qwythos-27B-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8081 --alias qwythos-27b-v1 --api-key <KEY> \
  -c 393216 --parallel 1 --batch-size 2048 --ubatch-size 512 -ngl 999 \
  --flash-attn on --jinja --reasoning off --cache-type-k q8_0 --cache-type-v q8_0 \
  --rope-scaling yarn --rope-scale 1.5 --yarn-orig-ctx 262144
```
Launch detached on vast: `cd /root/llama.cpp && setsid ./build/bin/llama-server ... > /root/<model>_<ctx>.log 2>&1 </dev/null &`.

## lin tunnels (one per server)
Existing manual tunnel pid mirrors: `ssh -N ... -i ~/.ssh/vast_id_rsa -p 15348 -L 18080:localhost:8080 root@ssh7.vast.ai`. Add the second via the Hermes terminal tool (background=true; shell setsid/nohup is refused): `ssh -N ... -L 18082:localhost:8081 root@ssh7.vast.ai`.

## Bifrost config (`/home/lin/bifrost/data/config.json`)
`providers` map — one entry per tunnel. A second OpenAI-compatible endpoint MUST declare `custom_provider_config.base_provider_type` (else "unsupported provider: <name>"):
```json
"openai":     { "keys": [{"name":"qwythos-9b-l40s","value":"<KEY>","models":["qwythos-9b-claude-mythos-5-1m"]}],
                "network_config": {"base_url":"http://localhost:18080","allow_private_network":true,"default_request_timeout_in_seconds":300} },
"qwythos27b": { "custom_provider_config": {"base_provider_type":"openai"},
                "keys": [{"name":"qwythos-27b-l40s","value":"<KEY>","models":["qwythos-27b-v1"]}],
                "network_config": {"base_url":"http://localhost:18082","allow_private_network":true,"default_request_timeout_in_seconds":300} }
```
base_url has NO `/v1` suffix. After editing, clear stale config_store DB so the old alias/key disappears: `docker cp bifrost:/app/config.db <bak>` && `docker exec bifrost rm -f /app/config.db` && `docker restart bifrost`. `/v1/models` then lists `openai/qwythos-9b-...` + `qwythos27b/qwythos-27b-v1`; clients still send the BARE id.

## Client re-point (old alias -> real ids)
Old fleet alias was `qwen3.8-27b-aggressive`; find every ref with `grep -rln qwen3.8-27b-aggressive`. Edits made:
- lin Hermes `~/.hermes/config.yaml`: `hermes config set model.default qwythos-27b-v1` + `hermes config set model.base_url http://localhost:8080/v1` (file protected vs direct patch); custom_providers models list updated. Verified via isolated `HERMES_HOME=/tmp/...` one-shot.
- lin opencode `~/.config/opencode/opencode.json`: `model` -> `bifrost/qwythos-27b-v1`; bifrost provider models map -> both real ids.
- rabuntu (root) Hermes `/root/.hermes/config.yaml` + OpenClaw `/root/.openclaw/openclaw.json`: ids -> real names; OpenClaw `primary` -> `bifrost/qwythos-27b-v1` (via `openclaw config patch`, validated).
- kubuntux opencode `/home/kubuntux/.config/opencode/opencode.json`: same as lin opencode.
- kubuntux Hermes was Syncthing-synced from lin (auto-updated), but its `localhost:8080` base_url is dead there (Bifrost is on lin) — the synced copy's localhost ref only works on lin.

## Gateway restarts (root user@0 systemd)
rabuntu runs both gateways as ROOT under the root USER systemd instance. Restart as root:
```
sudo -n bash -s <<'EOF'
export HOME=/root XDG_RUNTIME_DIR=/run/user/0
systemctl --user restart hermes-gateway      # /root/.hermes
systemctl --user restart openclaw-gateway    # /root/.openclaw
EOF
```
Running `systemctl --user` as the SSH user hits the wrong instance ("Unit not found").

## Verification
- `curl localhost:<tunnel>/v1/models` on lin confirms each id + `meta.n_ctx`.
- Real completion through Bifrost `POST localhost:8080/v1/chat/completions` with the bare id.
- Client one-shots: isolated `HERMES_HOME` `hermes chat -q`, and `openclaw agent -m '...' --agent main`.
