---
name: llm-gateway-serving
description: "Serve/swap a GGUF model on a rented GPU to local gateways."
metadata:
  tags: [llm, gguf, llama.cpp, vast, bifrost, hermes, openclaw, model-serving, gpu]
---

# LLM Gateway Serving (rented GPU → local agent mesh)

Serve an abliterated/custom GGUF on a rented GPU and expose it to local agents through a gateway, without reconfiguring any client. This is the pattern Dylan uses repeatedly (qwen27b, gemma-4-26b, qwythos-9b on the vast L40S), so it is a durable class of work.

## Architecture (lin-centric mesh)

```
[model server]  llama.cpp llama-server on vast L40S, listens :8080, api-key set
   │
   │  TCP local-forward: lin:18080 → vast:8080  (ssh -L, key under ~/.ssh)
   ▼
[Bifrost gateway] docker 'bifrost' --network host, lin:8080, tailnet 100.91.55.113:8080
   │  openai provider → base_url http://localhost:18080  (note: NO /v1 in bifrost's own cfg;
   │                                                  clients use http://<host>:8080/v1 WITH /v1)
   ▼
[clients] lin Hermes, kubuntux, rabuntu Hermes + OpenClaw — all request ONE model alias
```

## Golden rule: the stable alias drop-in

Pick one model name (currently `qwen3.8-27b-aggressive`) and keep it as the llama-server `--alias`, the api-key, and the port **unchanged across model swaps**. Every client (Hermes custom_providers, OpenClaw models.providers, Bifrost openai provider models list) points at that alias. To swap the actual model you only change the `-m <file>` and any ctx flags — zero client changes. Verify with a completion through Bifrost before calling it done.

## Workflow

1. **Pick the file.** Read the HF repo (`GET /api/models/<repo>`) for sibling `.gguf`s; huihui repos ship Q4_K/Q5_K/Q6_K/Q8_0/bf16 + a separate mmproj. Default to the Q4_K that the repo README's own example uses. Record the exact byte size via `curl -sIL <resolve-url> | grep -i content-length`.
2. **Determine native context.** Fetch the base model `config.json` and inspect the **nested `text_config`** (multimodal models nest it): key `max_position_embeddings`. If it equals the target (e.g. 1048576 = 1M) run `-c <target>` with **NO rope scaling**. If smaller, extend with YaRN (below). Qwythos/Qwen3.5 hybrids are natively 1M; gemma-4-26b is 262K native → needs YaRN for 1M.
3. **Confirm llama.cpp arch support BEFORE downloading.** The box may be running a llama-server already; check `git -C <llama.cpp> log -1` + `ls src/models/`. Qwen3.5 hybrid needs `qwen35.cpp` present; if missing, git pull + rebuild (recent llama.cpp).
4. **Download** via `curl -sL -o <file>.part <resolve-url>` to `/models` (vast images usually lack huggingface-cli/hf_hub). Rename `.part`→`.gguf` only after size matches the HEAD content-length exactly.
5. **Stop old server, start new** with identical `--host 0.0.0.0 --port 8080 --alias <alias> --api-key <key>` plus `--n-gpu-layers 999 --flash-attn on --jinja --reasoning off --cache-type-k q8_0 --cache-type-v q8_0 -c <target> --parallel 1 --batch-size 2048 --ubatch-size 512`. Log to a fresh file.
6. **Verify**: (a) `/v1/models` meta shows `n_ctx` == `n_ctx_train` == target (through the local forward); (b) a real `/v1/chat/completions` through Bifrost returns a marker string. Optionally confirm model identity by byte-comparing a running `-m` file to the HF content-length.

## Context extension

- **Native**: if `max_position_embeddings >= target`, `-c <target>` alone. Log line `n_ctx_seq (> n_ctx_train)` should NOT appear.
- **YaRN** (when native < target): factor = target/native (262144→1048576 = 4.0). Current llama.cpp renamed the flag: it is **`--rope-scaling yarn --rope-scale 4.0 --yarn-orig-ctx <native>`**, NOT `--yarn-factor` (that arg is rejected as `invalid argument`). The expected `n_ctx_seq > n_ctx_train` warning is fine — that is what YaRN handles.
- Watch VRAM during load (`nvidia-smi`). Size the KV budget, don't hand-wave: KV bytes ≈ full-attention-layers × n_kv_heads × head_dim × 2 × ctx × bytes/elem (q8 = 1 B/elem). Count full-attention layers from the base config `text_config.layer_types` (count `full_attention`) or `full_attention_interval` over `num_hidden_layers`. The Qwythos-9B (32 layers, few full-attn) had a cheap 1M q8 KV (~22GB); the Qwythos-27B (16 of 64 full-attn) at full 1M q8 needs ~34GB KV → ≈50GB total, which does NOT fit a 46GB card even alone. Co-resident rule of thumb on a 46GB L40S: two models fit only if you right-size contexts (27B@384K + 9B@192K ≈ 41GB; both at 1M is impossible). OOM at load = reduce ctx, drop KV quant, or drop a co-resident model.

## Pitfalls (learned)

- **`pgrep -f llama-server` matches your own command line** if the shell script string contains "llama-server". Use `pgrep -ax llama-server` (exact process name) for the real server.
- **Starting the server over SSH hangs the channel** until timeout even with `nohup ... &`. Detach fully: `setsid bash -c 'exec ...' </dev/null >/log 2>&1 &`. Don't block on it — poll the log from a fresh SSH.
- **A running server's log file tells you its exact launch flags and cwd** (`readlink /proc/<pid>/cwd`, its stdout target fd). Read those before kill/restart so you replicate flags exactly.
- **Model-file identity**: a prior agent often downloads a huihui artifact then renames it short (e.g. `gemma-4-26b-a4b-abliterated-Q4_K.gguf`). Byte-size equality with the HF content-length is strong evidence it IS that artifact — check before re-downloading 16GB.
- **Server is a detached daemon, not supervised** — dies on vast reboot; the local forward is a manual ssh. Offer to make both persistent (systemd + auto-restarting tunnel) after any swap.
- Restart `llama-server` on the same port the local forward targets (currently vast:8080 → lin:18080).

## Pitfall: "endpoint feels dead" is usually a RUNAWAY CLIENT, not the model

When a user reports the shared serve "hasn't responded in N minutes", DO NOT assume the model/GPU is down. Fresh-prompt probes answer in ~1 s. The real cause is almost always ONE stuck agent session hammering the shared endpoint:

**Signature** — `serve.log` shows ONE `task N` growing `n_gen`/`n_tokens` (e.g. 141K→143K) with tiny evals at collapsed decode (~50 tok/s over the giant retained context), GPU pegged 100%, and the agent log (`~/.hermes/logs/agent.log`) shows the SAME session id firing `API call #N` every ~2 s (e.g. #142, #143, #144…). That session holds a huge context (often a whole embedded PDF) and re-prefills + decodes it every turn, starving everyone else.

**Root cause often upstream:** an agent tried `read_file` on a scanned PDF (text-extraction-only tool → fails) and fell into an infinite retry loop re-sending its full context.

**Fix:**
1. Kill the gateway/agent hosting the runaway session (`kill <pid>` then `kill -9`; verify old pid gone).
2. Restart it clean (single instance — a redundant spawn will fail `Another gateway instance is already running`, which is fine, the lock holder is the winner).
3. **Restart llama-server too** (`/root/launch8b.sh` or equivalent) — the OLD runaway context stays cached in the llama-server slot after only the gateway restarts, and a fresh request against that polluted 140K+ slot can DEGENERATE into a 67K-token garbage loop. A clean llama-server context is required, not just a clean gateway.
4. Verify: `serve.log` shows no new calls from the old session id after restart; fresh-prompt completion is instant again.

Diagnose with a clean context + downscaled image before concluding the model is bad — a corrupt-GGUF probe and a polluted-slot generation look similar from the client side.

## Verifying a downloaded GGUF is NOT corrupt (bite you on every big download)

A byte-size match with the HF `content-length` is **NOT proof of integrity**. This session an `aria2c` command with TWO URLs and TWO `-o` flags interleaved both downloads' content into one file that ended up the exact right byte size but held garbage weights — the served model emitted gibberish (Korean chars, `blank cylinder`, repeated `#line` noise).

**Diagnose BEFORE trusting a server** — the failure looks like a config/template problem but is almost always corrupt weights:
- Raw probe: `llama-cli -m <model.gguf> -n 50 -p "The capital of France is" --temp 0.2 -ngl 99 --single-turn --no-display-prompt` (text-only, NO `--mmproj`). Sane prose = good weights; gibberish/Korean/`#line` spam = corrupt file. The earlier byte-matching copy failed this; a clean re-download passed.
- With `--mmproj` present and no image, llama-cli can drop into interactive mode and hang (exit 124) — drop `--mmproj` and add `--single-turn` for the probe.
- **Download rule:** one URL + one `-o` per aria2/curl process. Two URLs in one aria2 invocation with two `-o` flags is a corruption footgun even when sizes come out right.

## Model-family choice is governed by the WORKLOAD, then by KV/token

- **Confirm vision vs pure-text use before picking.** A "swap to a pure coder" suggestion is wrong when the job is document viewing — the user corrected this twice ("it's for viewing documents"). A VL model's mmproj+vision tower is wasted VRAM on text-only work, and a text coder can't read images. Ask/confirm the actual use case first. See `references/document-vlm-selection.md` for the vision/doc-reader pick.
- **Context ceiling is KV/token, not weight size.** Qwen3-30B-A3B (GQA, 48 layers × 4 KV × 128) = 96 KB/token fp16 ≈ 48 KB/token at q8. So 131K q8 KV ≈ 6.3 GB sits on top of 18.6 GB of weights (26.3/32 GB total). 500K q8 KV alone ≈ 24 GB — physically impossible on a 32 GB card with a 30B GQA model, regardless of flags. ~500K+ on ONE card needs an MLA / linear-attention arch (Qwen3-Next-80B's Gated DeltaNet), and that model is ~46 GB+ at Q4 → needs dual-GPU or an 80 GB card. For a single 32 GB 5090 the honest VL ceiling is ~256K with a small model (8B) or ~131K with a 30B.
- **Smaller dense at Q8 can be SLOWER to decode than a big MoE at Q4**: 8B dense Q8_0 moved ~8.2 GB/token vs 30B-A3B MoE Q4 moving only its ~3.3B active experts (~2 GB). Doc/image reading is prefill-bound so the 8B wins there; long text streaming is faster on the MoE. State the tradeoff explicitly instead of claiming a blanket speed win.

## Gateway wiring (config details)

Bifrost, Hermes custom_providers, and OpenClaw models.providers each need a specific config shape; the mesh Hermes/OpenClaw gateways run as **root under the user@0 systemd instance** on rabuntu. See `references/bifrost-hermes-openclaw-wiring.md` for exact schemas, test commands, and gotchas.

## Multi-model serving (real names — when you do NOT drop in under one alias)

llama.cpp serves ONE model per llama-server, so two models = two servers (:8080, :8081) + one TCP forward per port (lin:18080→:8080, :18082→:8081) + Bifrost exposing each under its own model. Two caveats that bite when retiring the drop-in alias:

- **Bifrost `providers.<key>` must be a KNOWN provider type** (`openai`, `vllm`, `ollama`, …). An arbitrary key (`openai-27b`) dies at runtime with `unsupported provider: <key>`. For a second openai-compatible backend under a custom key, add `custom_provider_config: { base_provider_type: "openai" }` to that provider block.
- **Bifrost's SQLite config_store holds stale provider state.** After editing `config.json`, a retired model/alias still shows up. The DB is `/app/config.db` (path `./config.db` relative to container workdir `/app` — NOT under the mounted `/app/data`). Clear it (`docker exec bifrost rm /app/config.db`, restart) to reseed cleanly from config.json.
- Real names remove the "zero client change" luxury: you must update Bifrost + every Hermes `custom_providers` (models + `model.default`) + every opencode.json `provider` block (models + top `model`) + OpenClaw `models.providers` (+ `primary`) in one coordinated pass, AFTER the backends+Bifrost are live.

## More pitfalls (learned)

- **Hermes config self-guard**: the file patch/write tools REFUSE to modify the running node's own `~/.hermes/config.yaml` ("Agent cannot modify security-sensitive configuration. Edit directly or use 'hermes config'"). Use the sanctioned `hermes config set model.default <name>` (and `model.base_url`, etc.) for scalar keys. Editing a REMOTE node's config over ssh is unaffected.
- **Synced Hermes configs**: mesh nodes may Syncthing-sync their `/root/.hermes/config.yaml` from the lin master live (kubuntux updated seconds after a lin `hermes config set`). Don't hand-edit a synced copy — edit the master. Corollary: a machine-specific `localhost` base_url inside a synced config silently breaks on every other node (kubuntux had a dead `localhost:8080` Bifrost path).
- **Mixed-sudo restart fails silently**: `sudo -n install … && systemctl --user restart` only wraps the install in sudo — the `systemctl --user` runs as the ssh user (e.g. rabuntu), whose user systemd has no such unit → `Unit not found` / `inactive`. Run the WHOLE remote script as root (`sudo -n bash -s` heredoc + `export HOME=/root XDG_RUNTIME_DIR=/run/user/0`) so `systemctl --user` targets root's user@0 instance.
- **Arch + download + build-layout (Blackwell/0.3.0 era)**: the CUDA arch flag is GPU-specific (Ada `89`, Blackwell/5090 `120` + CUDA≥12.8 image), HF anonymous downloads throttle PER-connection (use `aria2c -x16`, ~68 MB/s, not single `curl`), and current llama.cpp links `llama-server` as a ~17 KB launcher over `libllama-server-impl.so` (judge builds by `src/models/` arch file, not binary size). Full GPU-provision specifics live in the `vastai-gpu-rental` skill's `references/qwen3-vl-gguf-serving-and-hf-discovery.md`. (Overlaps `vastai-gpu-rental` — GPU provisioning detail lives there; this skill keeps the gateway/wiring view.)
