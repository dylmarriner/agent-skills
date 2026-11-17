# Concrete wiring snapshot — RTX 5090 / Qwen3-VL-8B-abliterated (verified 2026-09-03)

Ground-truth state of the replacement vast->Bifrost model-serving path. Re-verify with `ps aux | grep llama-server` on vast before trusting it.

## The box
- vast instance **ID 49649160**, GPU **RTX 5090** (32 GB, Blackwell sm_120), ~$0.35/hr.
- AU host (public 203.132.81.113). Connection through the vast proxy (port from instance detail); key `~/.ssh/vast_id_rsa` on lin. Instance label `qwen3-vl-30b-ablit` (stale label; the model is now the 8B — see below).
- Image: `nvidia/cuda:12.8.0-devel-ubuntu22.04` (devel, NOT cudnn-devel).
- llama.cpp built at `/root/llama.cpp` (master, commit 0f3a71b) with `-DCMAKE_CUDA_ARCHITECTURES=120` (Blackwell).
- **Model (current, swapped 2026-09-03):** `/root/models/Huihui-Qwen3-VL-8B-Instruct-abliterated.Q8_0.gguf` (8,709,520,384 B) + `...mmproj-Q8_0.gguf` (752,290,176 B), from `mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF`. Q8_0 = ~FP8-grade near-lossless; deployed at **262144 ctx q8 KV**.
- WHY the 8B swap: this box is a **document viewer** (vision/doc reading), not a coding-text serve. The prior 30B-A3B Q4 ran 131K ctx and ate 26 GB/32 GB with ~6 GB headroom, so bigger context was physically impossible (GQA KV ~48 KiB/token @q8). The 8B Q8_0 frees ~13 GB VRAM and doubles native ctx to 262K while keeping the VL vision tower. Tradeoff: Q8 dense 8B decode (~155 tok/s) is SLOWER than the Q4 MoE 30B it replaced (~274 tok/s) for raw text — irrelevant for doc viewing (prefill-bound), matters for text dumps (drop to Q4_K_M to ~double decode).

## The tunnel (lin)
`ssh -N -o ... -i /home/lin/.ssh/vast_id_rsa -p <vast-proxy-port> -L 18083:localhost:8080 root@<vast-proxy-host>`
=> maps **lin:18083 -> vast:8080**. Started as a Hermes-tracked background (silent, long-lived) process.

## Bifrost (lin)
- docker `bifrost`, --network host, lin :8080 / tailnet 100.91.55.113:8080.
- Provider `qwen3vl` in `~/bifrost/data/config.json`:
  - `custom_provider_config: {base_provider_type: openai}`
  - keys: name `qwen3vl-5090`, value `512e520844f73fff620d4a7aafbe5592692af3267f21a4b5`, models [`qwen3-vl-30b-a3b-ablit`]
  - network_config.base_url `http://localhost:18083` (NO /v1), allow_private_network true, timeout 300
- The model ID in Bifrost/Hermes/opencode/OpenClaw is STILL `qwen3-vl-30b-a3b-ablit` (alias) — the 8B server advertises that same alias, so a model swap needs ZERO client changes. Do not relabel the alias to `qwen3-vl-8b-ablit` unless doing a coordinated fleet re-point.
- Dead `openai`/`qwythos27b` providers (old L40S backends) show `list_models_failed` connection-refused on :18080/:18082 — expected while the L40S is off.

## llama-server launch (detached, /root/launch8b.sh; auto-start via /root/onstart.sh)
```
cd /root/llama.cpp
setsid ./build/bin/llama-server -m /root/models/Huihui-Qwen3-VL-8B-Instruct-abliterated.Q8_0.gguf \
  --mmproj /root/models/Huihui-Qwen3-VL-8B-Instruct-abliterated.mmproj-Q8_0.gguf \
  --host 0.0.0.0 --port 8080 --alias qwen3-vl-30b-a3b-ablit \
  --api-key 512e520844f73fff620d4a7aafbe5592692af3267f21a4b5 \
  --ctx-size 262144 --parallel 1 --batch-size 2048 --ubatch-size 512 \
  --n-gpu-layers 99 --flash-attn on --jinja \
  --cache-type-k q8_0 --cache-type-v q8_0 </dev/null >/root/serve.log 2>&1 &
```
Loads ~30.3 GB / 32.6 GB VRAM (weights 8.7 + mmproj + q8 KV @ 262144). Native train ctx 262144; n_ctx_slot 262144.

## Verified end-to-end (after the swap)
- Model advertises alias `qwen3-vl-30b-a3b-ablit`; clean decode ~155 tok/s.
- Vision proven through the FULL Bifrost chain (lin:8080 -> 18083 -> vast): a 900x300 generated invoice PNG (base64 data URI) -> correctly read "INVOICE #4821, Total: $127.50 NZD, line items". Do NOT trust a text-only completion to prove the mmproj/vision path.

## Fleet re-point (off dead qwythos-27b-v1) — unchanged by the 8B swap
- lin + kubuntux Hermes (Syncthing-synced; editing lin master auto-propagates) -> model.default qwen3-vl-30b-a3b-ablit via `hermes config set model.default ...`.
- lin opencode.json: top `model: bifrost/qwen3-vl-30b-a3b-ablit` + id in the `bifrost` provider models map (baseURL http://localhost:8080/v1).
- rabuntu root Hermes + OpenClaw + kubuntux opencode/OpenClaw: point at tailnet http://100.91.55.113:8080/v1 (NOT localhost — Bifrost is on lin).
- Gateways that run as root under user@0 (hermes-gateway, openclaw-gateway) restart as root with HOME=/root XDG_RUNTIME_DIR=/run/user/0.

## Standing gap (partially closed 2026-09-03)
Server now auto-starts on vast boot via `/root/onstart.sh` (sleep 5, then `/root/launch8b.sh`). The lin SSH tunnel (:18083) is still a manual/tracked foreground ssh — not systemd-supervised. The 30B GGUF + mmproj were deleted after the 8B verified (freed 19 GB); old launch_vl.sh / provision_vl.sh removed.
