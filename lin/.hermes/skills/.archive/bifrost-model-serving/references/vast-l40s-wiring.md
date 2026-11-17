# Concrete wiring snapshot (verified 2026-09-02)

Ground-truth state of the live vast->Bifrost model-serving path, verified by SSH + curl. Re-verify with `ps aux | grep llama-server` on vast before trusting any of this — it changes whenever the model is swapped.

## The box
- vast instance **ID 49615348**, GPU **L40S** (46 GB VRAM), ~$0.62/hr.
- SSH: `root@ssh7.vast.ai` port **15348**, key `~/.ssh/vast_id_rsa` on lin. (`vast` public IP 61.206.39.5 resolves but SSH goes through the vast proxy hostname ssh7.vast.ai.)
- llama.cpp built at **`/root/llama.cpp`** (`build/bin/llama-server`) — vast `/workspace` is EMPTY; Dylan's templates say /workspace, reality is /root.
- Models live in **`/models/`** on vast.

## The tunnel (manual ssh on lin)
`/usr/bin/ssh -N -o StrictHostKeyChecking=no -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=4 -o IdentitiesOnly=yes -o ConnectTimeout=20 -i /home/lin/.ssh/vast_id_rsa -p 15348 -L 18080:localhost:8080 root@ssh7.vast.ai`
=> maps **lin:18080 -> vast:8080**. Verify: `ss -tlnp | grep 18080` shows the ssh LISTEN pid. This is a foreground/manual process — dies with the session; not persistent.

## Bifrost (lin)
- docker container `bifrost`, `--network host`, lin **:8080** / tailnet 100.91.55.113:8080.
- Config `~/bifrost/data/config.json` on lin. openai provider:
  - `base_url: http://localhost:18080` (NO /v1 — llama-server already mounts it)
  - api-key `value` = **512e520844f73fff620d4a7aafbe5592692af3267f21a4b5** (must equal llama-server `--api-key`)
  - models: [`qwen3.8-27b-aggressive`], weight 1.0, timeout 300s
  - auth off; master_key `sk-local` (send `Authorization: Bearer sk-local` if a call asks)
- No auth on lin:8080 needed for /v1 calls.

## Stable alias & api-key (the invariants)
Every swap keeps: `--alias qwen3.8-27b-aggressive --api-key 512e520844f73fff620d4a7aafbe5592692af3267f21a4b5`.
Clients that depend on that id: Hermes `qwen27b-mtp@lin`, `bifrost-qwen@kubuntux`, opencode+pi provider `bifrost`.

## Model currently served (2026-09-02)
`/models/gemma-4-26b-a4b-abliterated-Q4_K.gguf` (16,796,015,648 bytes) = the **huihui-ai/Huihui-gemma-4-26B-A4B-it-qat-q4_0-unquantized-abliterated-GGUF** `...Q4_K.gguf` artifact, renamed short. Provenance proven by byte-size equality with HF content-length (see SKILL.md model-identity check). Real model is Gemma (meta.n_vocab 262144, n_params 25,233,142,046, ftype Q4_K) served under the qwen alias — do NOT report it as Qwen.

Running server command (verify current via ps; this was the live one):
```
cd /root/llama.cpp
./build/bin/llama-server -m /models/gemma-4-26b-a4b-abliterated-Q4_K.gguf \
  --host 0.0.0.0 --port 8080 --alias qwen3.8-27b-aggressive \
  --api-key 512e520844f73fff620d4a7aafbe5592692af3267f21a4b5 \
  --ctx-size 262144 --parallel 1 --batch-size 2048 --ubatch-size 512 \
  --n-gpu-layers 99 --flash-attn on --jinja --reasoning off \
  --cache-type-k q8_0 --cache-type-v q8_0
```
Run detached (ppid 1) — NOT systemd-supervised. Server log was `/root/gemma.log`; build log `/root/build1.log`.

## End-to-end verification commands
```
# model identity via tunnel (bearer = api-key)
curl -s http://localhost:18080/v1/models -H "Authorization: Bearer 512e..." | jq '.data[0].meta'

# real completion through Bifrost (proves the whole path)
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.8-27b-aggressive","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
# expect .model == qwen3.8-27b-aggressive and real content back
```

## Open gap (offer, don't build unprompted)
Server + tunnel are both non-persistent. Making them survive a vast reboot = systemd unit on vast for llama-server + auto-restarting tunnel on lin.
