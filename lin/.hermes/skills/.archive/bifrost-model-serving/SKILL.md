---
name: bifrost-model-serving
description: Serve GGUF models behind Bifrost under a stable alias.
---

# Bifrost model serving (vast GPU -> Bifrost gateway -> fleet)

Dylan's fleet routes LLM traffic through the **Bifrost AI gateway** running as docker container `bifrost` (network host) on **lin :8080** (tailnet 100.91.55.113:8080). Bifrost does NOT host models itself — its `openai` provider forwards to a cloud-GPU llama.cpp `llama-server`. This skill is the playbook for serving/swapping the model behind Bifrost without breaking the downstream clients (Hermes, opencode, kubuntux, pi) that all request one fixed model id.

## THE CARDINAL RULE: stable alias indirection

Bifrost's openai provider declares a fixed model id that every downstream client requests (Hermes `qwen27b-mtp@lin`, `bifrost-qwen@kubuntux`, opencode/pi provider `bifrost` -> `qwen3.8-27b-aggressive`). Bifrost forwards that request verbatim to the GPU llama-server.

**Therefore: whatever model you actually run on the GPU, launch llama-server with `--alias qwen3.8-27b-aggressive` (the id the fleet asks for).** Keep the model id stable and swap only the `-m` model file. Then the model can change (Qwen -> Gemma -> anything) with ZERO changes to Bifrost config, Hermes, opencode, or kubuntux. Preserve the api-key flag too (Bifrost's openai provider `value` is sent as the bearer token; llama-server's `--api-key` must match it or authorized calls fail).

Do NOT run llama-server with its bare GGUF basename as the model id — downstream requests for `qwen3.8-27b-aggressive` will 404. If Dylan explicitly wants the id relabeled, that is a coordinated edit across Bifrost config + Hermes + opencode + kubuntux, not a single-file change.

## Architecture / data path

```
vast llama-server :8080   (serves -m <gguf>, --alias <stable-id>, --api-key <key>)
   ^
   |  SSH tunnel (manual process on lin)
lin:18080  ->  vast:8080
   ^
Bifrost (lin :8080) openai provider base_url http://localhost:18080  (NO /v1 suffix)
   ^  clients request model <stable-id>
Hermes / opencode / kubuntux / pi
```

Concrete current wiring (instance, key, tunnel) is in `references/vast-l40s-wiring.md`.

## Verify-first workflow (always check state before assuming)

A prior session may already have the requested model up. Before downloading/swapping anything:
1. **Read the running server command on vast**: `ps aux | grep llama-server` — reveals the actual `-m` file, alias, api-key, and cwd. Do not trust labels or memory about which model is served.
2. **Identify the REAL model from metadata**, not the alias. `curl localhost:<tunnel>/v1/models` returns `meta.n_vocab` which distinguishes families: Gemma vocab = 262144, Qwen = ~151k. The alias is meaningless for identity; vocab + n_params + ftype are not.
3. **Prove the model artifact**, don't assume it: byte-size equality against the HF repo file (see model-identity check below) is a fast, strong identity check without a 16 GB download.
4. **Verify the full chain end-to-end** with a real completion through Bifrost (lin:8080), not just the tunnel: POST /v1/chat/completions, model <stable-id>, expect the model field echoed and real content back.

## Model swap procedure

1. Stop the existing detached server: find pid (`ps aux | grep llama-server`), `kill <pid>`. (It is a bare daemon, ppid 1, NOT systemd/docker — see pitfalls.)
2. Download the new GGUF to `/models/` on vast (llama-server `--hf-repo/--hf-file` auto-downloads on start, or `hf download` / curl from the resolve URL).
3. Start llama-server with Dylan's context flags AND the stable `--alias` + `--api-key`, e.g.:
   `./build/bin/llama-server -m /models/<file>.gguf --host 0.0.0.0 --port 8080 --alias <stable-id> --api-key <key> --ctx-size 262144 --parallel 1 --flash-attn on --jinja --cache-type-k q8_0 --cache-type-v q8_0` (add `-ngl 99` / `--n-gpu-layers 99` for full GPU offload, `--batch-size 2048 --ubatch-size 512`).
4. Health + completion checks as above.

## Model-identity check via HF byte size (cheap, no download)

To confirm a local GGUF is the exact artifact Dylan named, compare byte counts. HF serves via xet CDN with a 302 redirect:
`curl -sIL <hf resolve URL>` -> follow redirects -> final `HTTP/2 200 content-length: <bytes>`. If it equals the on-disk file size, it is (to astronomically high confidence) the same file — the prior agent often renames downloads to short local names, so the filename is NOT proof of provenance but the byte count is.

## Two serving modes

**A. Drop-in alias swap (single model).** Launch every model with the same `--alias`; the fleet (Hermes/opencode/OpenClaw across lin/kubuntux/rabuntu) is untouched. Right for "swap the model to X". See the cardinal rule above.

**B. Multi-model, real names (serve two side by side).** One llama-server per model — each on its own vast port, its own lin `ssh -L` tunnel, its own Bifrost provider. Drop the fake alias; each server gets its REAL model id. Clients pick by name, so the fleet config MUST be re-pointed (NOT zero-touch). Real ids in use for the Qwythos family: `qwythos-9b-claude-mythos-5-1m`, `qwythos-27b-v1`. Concrete recipe in `references/multi-model-realnames-wiring.md`.

## Determining context: native vs YaRN (never assume a "1M" model is native 1M)

Read the base HF `config.json` `text_config` before choosing flags:
- `max_position_embeddings` set and NO `rope_scaling` => NATIVE at that size: run `-c <size>`, NO yarn. (Qwythos-9B-Claude-Mythos-5-1M = native 1048576.)
- `rope_scaling: {rope_type: yarn, factor, original_max_position_embeddings}` => NOT native; that size is reached by YaRN over the smaller original, and exceeding the original REQUIRES yarn flags. (Qwythos-27B-v1 = yarn factor 4.0 over original 262144.)
- Confirm live via `/v1/models` `meta.n_ctx == meta.n_ctx_train` (no overflow); llama-server logs `n_ctx_seq (N) > n_ctx_train (M)` when you exceed native unscaled.

## llama.cpp context flags (recent builds, ~build 10759+)

- The YaRN factor flag was RENAMED: `--yarn-factor` is INVALID ("invalid argument"). Use `--rope-scale N`. Pattern for context C over original O (C>O): `-c C --rope-scaling yarn --rope-scale <C/O> --yarn-orig-ctx <O>` (384K over 262K => `--rope-scale 1.5`).
- llama.cpp on vast lives in `/root/llama.cpp` (NOT /workspace). Confirm the arch is supported before pulling a model: `ls src/models/` (qwen35.cpp / qwen35moe.cpp present = Qwen3.5 hybrid OK). The build is today's master — re-pull+rebuild if the instance was re-provisioned.

## Establish the box's PURPOSE before choosing a model class

Before recommending or swapping a model, ask what the serve is actually FOR — the correct model family depends entirely on it, and a wrong-class guess wastes a full download cycle:
- **Vision / document viewing** (reads PDFs, page images, screenshots, invoices) => a **VL** model (Qwen3-VL) with `--mmproj`. This was the 5090 box's real job — Dylan corrected a coding-model guess hard ("it's for viewing documents").
- **Pure coding/agentic text** => a Coder or general text model, NO mmproj (saves the vision-encoder VRAM and improves code quality).
- **OCR extraction to structured text** => a parser (GutenOCR, Infinity-Parser, NuMarkdown) — but those are extractors only, they cannot reason/chat/edit about the doc.

For vision/doc viewing the sub-10B sweet spot is **Qwen3-VL-8B** (DocVQA ~96.1, native 256K ctx) — better doc scores than every Gemma 3 size incl. 27B, and ~6 GB total at Q4 so a huge KV cache fits a 32 GB card. 4B is close on DocVQA but weaker at general reasoning/editing.

## Smaller is NOT always faster (quant + arch reality check)

A "smaller model = faster serve" assumption is wrong when the comparison crosses quant and MoE boundaries:
- **Q8_0 dense 8B decode was SLOWER (~155 tok/s) than the Q4_K_M 30B-A3B MoE it replaced (~274 tok/s)** on the same 5090. Q8 moves 2x the weight bytes/token vs Q4, and the A3B MoE only activates 3.3B params/token. For a doc viewer that is irrelevant (reading images is prefill-bound, and the 8B ingests vision far faster) — but for raw long text streaming the old box was genuinely faster.
- Tradeoff to state explicitly to Dylan: bigger context + faster doc reading + less VRAM vs slower raw text decode. If text decode speed matters, drop the same model to Q4_K_M (approx doubles decode).

## Validating a swapped model BEFORE trusting it (this session's hard lesson)

Byte-size equality with the HF content-length is a STRONG provenance check **only if the download itself was clean** — it can be fooled by a corrupt/interleaved transfer (below). After any model swap, prove the weights actually generate coherent text:
- A model emitting **gibberish** (mixed non-English glyphs + repeated noise like "#line#line...blankcylinder") = corrupt weights or wrong arch, NOT a chat-template/config bug. Diagnose it.
- Validate weights standalone, bypassing the server and any template: `./build/bin/llama-cli -m <model> -n 40 -p "The capital of France is" --single-turn -ngl 99` and read the raw completion. A multimodal model with NO image and no `--single-turn` **hangs in interactive mode** (exit 124, repeated `> ` prompts) — pass `--single-turn` and text-only.
- Then prove the vision path with a real base64 PNG through the full Bifrost chain, not just a text completion.

## Download hygiene: one aria2 process per file

A single `aria2c` invocation with TWO `-o` flags and two URLs **interleaves the two downloads and corrupts both** — the model file landed under the mmproj filename and, worse, the "model" that resulted matched the expected HF byte size exactly yet generated pure gibberish when loaded. Byte size said clean; the weights were not.
- Launch **one aria2 per file**: separate `aria2c -x16 -s16 ... -o <name> <url>` per artifact.
- After a download that went through a multi-URL/`-o` command, do NOT trust the byte-size identity check — re-download clean or validate generation coherence before building a server on it.

## Beware component / FP8 repos that are NOT standalone servable models

A repo named `...-FP8` shipping a SINGLE `model.safetensors` with no `config.json`, no tokenizer files, no mmproj is often NOT a runnable model — it can be a drop-in weight component for another model (e.g. huihui's `Huihui-Qwen3-VL-8B-Instruct-abliterated-FP8` is a text_encoder override for `ideogram-4-fp8`). llama-server loads GGUF only and cannot use it at all.
- Before committing to a model a user links, verify the repo is a complete, servable artifact: list siblings (`curl -s https://huggingface.co/api/models/<repo>`) and confirm a `.gguf` exists (plus `config.json`/tokenizer if it were safetensors). If only a bare safetensors is present, find the servable GGUF of the same weights lineage (mradermacher carries the huihui-ai abliterated GGUFs) and deploy that instead.

## VRAM budgeting for big context (Qwen3.5 hybrid vs dense)

Read `text_config.layer_types` + `full_attention_interval` + `head_dim`/`num_key_value_heads`. The hybrid arch (linear_attention layers + full_attention every `interval`) keeps KV tiny — only full-attention layers carry KV. KV bytes/token ~= full_attn_layers x kv_heads x head_dim x 2 (x 1 byte @ q8). A classic dense 27B (16 full-attn layers, head_dim 256, kv_heads 4) at 1M q8 is ~34 GB of KV ALONE -> does not fit a 46 GB L40S even by itself; a hybrid 9B @ 1M is ~28 GB total. When co-serving two models, budget empirically with nvidia-smi after each load; a verified combo (9B@192K + 27B@384K q8) sits at ~41 GB/46 GB. Confirm both llama-servers actually bound their ports before trusting `/v1/models` (logs say "listening", but a raced `ss` can miss it).

## Standing up a FRESH vast box (not a drop-in swap on the existing one)

When Dylan wants a NEW model on a NEW instance (vs swapping `-m` behind an existing server), the bring-up has distinct traps:

**vast API (as of 2026-09):** the vast MCP tools' payloads are STALE and 400. Drive the API directly via curl with the key from `~/.hermes/config.yaml` (VAST_API_KEY under the vast MCP block) — `~/vast_api.key` can be a revoked/stale key (`auth_error`).
- search: `PUT /api/v0/search/asks/` body `{"q":{<filters as {"field":{"eq":val}}>,"type":"on-demand","order":[["dph_total","asc"]],"limit":N},"select_cols":[<EXPLICIT columns>]}` — select_cols must be NAMED columns, never `["*"]`.
- create: `PUT /api/v0/asks/<offer_id>/` body `{"client_id":"me","image":<img>,"disk":N,"runtype":"ssh","label":...,"env":{}}` (runtype picks ssh/jupyter).
- **Create ONE instance at a time; parse the response with python json.** The reply is `"success": true` (WITH a space) — a shell `grep '"success":true'` silently MISSES it and a loop keeps firing, creating MULTIPLE billable instances. On any `new_contract`, STOP and destroy the rest immediately. (Real incident: a naive loop spun up 5 x $0.32/hr instances before the bug was caught.)
- **Offers churn fast** — a just-searched offer often returns `no_such_ask` on create (already sold). Re-search and create in one tight flow; skip any id that fails twice.
- **Image choice**: build llama.cpp with the lean `nvidia/cuda:<12.8+>-devel-ubuntu22.04` image — cudnn-devel is huge (many layers) and stall-prone. A host stuck on the SAME "Pulling fs layer" for >~10 min is stalled — destroy and recreate on a DIFFERENT host rather than wait.

**Blackwell (RTX 5090) is sm_120, not Ada sm_89.** Build llama.cpp with `-DCMAKE_CUDA_ARCHITECTURES=120` and a CUDA >=12.8 image. The old Ada `=89` provisioning will not compile on a 5090.

**llama.cpp 0.3.0 (master ~Sep 2026) changed layout:** `build/bin/llama-server` is a small ~17 KB launcher over `libllama-server-impl.so` + `libggml-cuda.so` (the ~62 MB CUDA kernels). A tiny llama-server binary is NORMAL, not a failed build. Verify arch support with `grep -rl <arch> src/models/` (e.g. `qwen3vlmoe.cpp` = Qwen3-VL MoE OK) and `git -C /root/llama.cpp log -1`.

**HF anonymous downloads throttle to ~KB/s per IP** (a single curl crawls ~0.7 MB/s or worse). Use `aria2c -x16 -s16 -c -o <name> <hf-resolve-url>` — 16 parallel connections aggregate ~68 MB/s. Don't burn time on single-stream curl; hf-mirror is often 0 B/s off-region.

**Vision model bring-up (Qwen3-VL / --mmproj):**
- Qwen3-VL-30B-A3B: 48 layers, 4 kv_heads, head_dim 128, native 262144 ctx -> q8 KV ~48 KiB/token. On 32 GB: Q4_K_M(~17.3 GB)+mmproj+KV@131072 ~= 26 GB loaded (fits); full 256K OOMs with vision overhead.
- Launch with `--mmproj <file>` for vision. PROVE vision with a real base64 PNG (a text-only completion does NOT exercise the mmproj/vision path).

## Bifrost dual-provider gotchas (multi-model mode)

- Bifrost `providers.<name>` key IS the provider type, from a fixed enum. You CANNOT add a second endpoint named e.g. `openai-27b` — runtime logs `failed to prepare provider ... unsupported provider: openai-27b` and drops it. To add a second OpenAI-compatible endpoint under ANY name, put `"custom_provider_config": { "base_provider_type": "openai" }` on that provider (schema: https://www.getbifrost.ai/schema, `$defs/custom_provider_config`).
- `config_store` SQLite (`./config.db` in the container at `/app/config.db`) PERSISTS old provider/key rows. After editing config.json a stale model can linger in `/v1/models`. Clear it: `docker cp bifrost:/app/config.db <backup>` then `docker exec bifrost rm -f /app/config.db` then `docker restart bifrost` — it reseeds cleanly from config.json. (Config file itself is the host mount `/home/lin/bifrost/data/config.json -> /app/data/config.json`; DB is NOT under that mount.)
- `/v1/models` lists models prefixed by provider (`openai/qwythos-9b-...`, `qwythos27b/qwythos-27b-v1`), but a request for the BARE model id routes to the owning provider — clients send bare names.
- Each model needs its own tunnel (mirror lin:18080->vast:8080 as lin:18082->vast:8081) and one Bifrost provider per tunnel. Start the extra tunnel with `terminal(background=true)` — shell-level `setsid`/`nohup` wrappers are refused by the terminal tool — and keep it as a tracked long-lived process.

## Fleet re-point when real names replace the alias

Clients requesting the old alias must move to the new id. Find every reference with `grep -rln <old-id>`. Places:
- **Hermes** (`config.yaml`): `custom_providers[].models` + top `model:{default,provider,base_url}`. On the machine where Hermes itself runs the file is PROTECTED against direct `patch` — use the sanctioned `hermes config set model.default <id>` / `hermes config set model.base_url <url>` via terminal, then prove routing with an isolated home: `mkdir -p /tmp/hx/sessions && cp config.yaml+env /tmp/hx && HERMES_HOME=/tmp/hx hermes chat -q '...'` (avoids touching the live profile).
- **opencode** (per machine `~/.config/opencode/opencode.json`): top-level `model` ("<provider>/<id>") + that provider's `models` map.
- **OpenClaw** (root `/root/.openclaw/openclaw.json`): `models.providers.<name>.models[]` ids + `agents.defaults.model.primary` = `"<provider>/<id>"` + alias entries under `agents.defaults.models`. Edit via `openclaw config patch --file <patch.json5> --dry-run` first (schema-validated) then `openclaw config validate`.
- **Cross-machine Hermes configs may be Syncthing-synced from a master** — an edit on lin propagates automatically. But a `localhost` base_url in a synced copy is only valid on the machine that actually runs Bifrost; kubuntux's synced copy pointed `qwen27b-mtp` at a dead `localhost:8080`. Verify with `ss -tlnp`/`curl localhost:<port>` before trusting any provider's base_url on a given host.
- **Gateway restarts**: services that run as root under the root USER systemd instance (`user@0`, e.g. `hermes-gateway`, `openclaw-gateway`) must be restarted AS ROOT: `sudo -n bash -s` with `export HOME=/root XDG_RUNTIME_DIR=/run/user/0` then `systemctl --user restart <unit>`. Running `systemctl --user` as the SSH user hits the wrong user instance ("Unit not found").

## Client-side wiring: route family, and what a dead port looks like

When a downstream client is (or should be) talking to Bifrost, two things decide success — which
*route family* the client speaks, and whether the port it names is actually bound.

**Route families live at different paths on the same port.** Probe before wiring:

| Probe | Meaning |
|---|---|
| `POST /v1/chat/completions`, `GET /v1/models` → 200 | OpenAI-compatible family |
| `POST /v1/messages` → **405 Method Not Allowed** | that prefix has no Anthropic family — the client needs the `/anthropic` prefix |
| `POST /anthropic/v1/messages` → 400 with "could not auto resolve a provider" | route EXISTS, no provider can serve the requested model (gateway up, provider down) |
| `GET /v1/models` → 200 with an **empty** list | every provider is failing upstream — check the llama-server ports the providers point at (`localhost:18080`, `:18083`, …) with `ss -ltn` before touching the client |

Anthropic-protocol clients (Claude Code and anything else speaking `POST /v1/messages`) must be
pointed at the Anthropic-shaped prefix (`http://<host>:<port>/anthropic`), not the bare host — Claude
Code appends `/v1/messages` itself. A 405 there is a route-family mismatch, not a broken client.

**A client pointed at a port nothing binds reports it as a firewall.** Claude Code's wording names a
firewall/network policy; the actual cause was `ANTHROPIC_BASE_URL` in `~/.claude/settings.json` aimed
at a gateway port with no listener. Prove the port first — `ss -ltn | grep <port>` and
`curl -sS -m 5 -o /dev/null -w '%{http_code}' <base-url>` — and read the gateway's own config/env for
the port it really serves on, rather than trusting the override. A silent multi-minute run with no
output is the same connection failure, not a hang.

When the gateway has no working provider and the client carries its own valid credentials (e.g. a
Claude Max/Team OAuth login in `~/.claude/.credentials.json`), the working fallback is to remove the
gateway override entirely so the client goes direct; verify with
`claude -p "say ok" --output-format json` → `is_error: false`, and take model ids from the vendor API
rather than the gateway's alias namespace.

**A plugin that "heals" client settings will undo that edit.** Token-optimizer-style plugins snapshot
`settings.json` and restore absent keys on SessionStart/UserPromptSubmit, so a removed `env` block
returns on the next session. Fix it at the baseline: rewrite the snapshot
(`plugins/data/<plugin>/config/settings_heal/highwater.json` + `highwater.meta.json`) to drop the key,
then write `tombstones.json` → `{"tombstoned_keys": ["env"]}` so the heal cannot restore it. Confirm by
running one live session and re-reading `settings.json`: the key must still be absent.

## Pitfalls

- **Server is not persistent.** Started as a detached daemon (ppid 1), it dies on a vast instance reboot and nothing restarts it. The lin SSH tunnel is also a manual foreground ssh process. Neither is systemd-supervised. If Dylan wants set-and-forget, add a systemd unit on vast for llama-server AND an auto-restarting tunnel on lin — this is the standing gap.
- **The llama.cpp build lives in `/root/llama.cpp` on vast, NOT `/workspace`** (vast `/workspace` is empty/unused on this box). The running server's cwd is `/root/llama.cpp`. Dylan's command templates say `/workspace/llama.cpp` — adjust to reality.
- **Bifrost config** lives at `~/bifrost/data/config.json` on lin. openai provider: `base_url http://localhost:18080` with NO `/v1` suffix (llama-server already mounts /v1). api-key `value` in config == llama-server `--api-key`.
- llama-server returns its alias in `/v1/models` `data[].id` — don't confuse model id with model family; identify by meta.

## "It's been N minutes with no response" — dead backend vs runaway client loop

When Dylan reports the serve is unresponsive for many minutes, FIRST distinguish a dead model from a **runaway agent loop saturating the shared endpoint**. They look identical from the client and the fix is totally different.

Diagnostic sequence:
1. **Is the backend actually busy?** `nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader` on vast. 0% = nothing is decoding. Then POST a fresh tiny completion to the tunnel; if it answers in ~1s, **the model is fine** — the stall is upstream.
2. **Check the serve log for a ballooning context across calls.** `tail /root/serve.log` on vast: if `n_tokens` climbs every request (131K -> 141K -> 143K...) and stays high with `f_keep = 1.0`, ONE client is holding a giant context alive and re-prefilling it each turn (~40s prefill at 140K, then ~50 tok/s decode). That saturates the single-slot server so every other client crawls.
3. **Identify the spinning session in the agent's own log** (`~/.hermes/logs/agent.log`, or the synced copy under `/mnt/storage/.../logs/agent.log` on kubuntux). Look for the SAME session id emitting `API call #N: ... in=<140000+>` every few seconds with an identical tiny tool result each time (e.g. `tool terminal completed (1.4s, 46 chars)`). That repeated-call signature = an agent stuck in an infinite tool-error loop, not a slow model.

Typical trigger: an agent task hit an unhandleable input and retries forever instead of giving up — e.g. a PDF task where the agent called `read_file` on a `.pdf` (Hermes `read_file` does NOT read PDFs), failed, and looped re-sending its whole embedded-PDF context every ~5s.

Fix: kill the gateway hosting that session (it is a bare detached python `-m hermes_cli.main gateway run`, ppid 1), then relaunch it clean (single instance; the old gateway.lock/state may still name the dead pid — the new process wins the lock and the stale state is harmless). Verify: **zero** `API call` lines for that session id AFTER the restart timestamp, and the endpoint answers instantly again. The running agent session itself is lost but sessions persist in the DB.

Related durable fact: to actually read a PDF through an agent, route it via the **docling / markitdown MCP** servers (both configured) — never expect `read_file` to open `.pdf`.

## Related

- `runpod-model-deploy` — generic GGUF deploy on cloud GPUs wired DIRECTLY to Hermes as a custom provider (no gateway). Bifrost path (this skill) inserts a gateway alias indirection instead.
- References: `references/vast-l40s-wiring.md` (single-model alias wiring), `references/multi-model-realnames-wiring.md` (two-model real-name co-serving + fleet re-point recipe), and `references/vast-5090-qwen3-vl-wiring.md` (RTX 5090 / Qwen3-VL fresh-box + Bifrost provider + fleet re-point, verified 2026-09-03).
- Memory note "Bifrost AI gateway" holds the live fleet state.
