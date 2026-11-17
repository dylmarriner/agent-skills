# Serving an abliterated/uncensored GGUF on a vast llama-cpp instance

Session: 2026-08-24, Qwythos-9B abliterated on RTX 5090, instance 48485050.
Full walkthrough of deploying a HuggingFace GGUF through Vast's `vastai/llama-cpp`
template with a big context window, and the gotchas that cost real time.

## Result achieved

- Instance: RTX 5090 (32 GB), California, $0.32/hr. 4 slots, n_ctx_slot=524288 (500K).
- Model: `huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF`
  `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf` (5.78 GB).
- Server: `/opt/llama.cpp/cuda-12.8/llama-server`, `-ngl 99 -fa on -c 524288 --jinja`.
- Throughput: ~184 tok/s generation. Reasoning model spends tokens in the think block
  before the answer — give `max_tokens` a generous budget (2000+).

## Gotchas that mattered

1. **Template `env` overrides are IGNORED on `create_instance`.** The llama-cpp template's
   baked-in `Extra Env` (`LLAMA_MODEL=unsloth/Qwen3.5-35B-A3B-GGUF:UD-Q5_K_XL`,
   `LLAMA_ARGS="--no-mmap --port 18000 -c 0 --jinja"`) wins over whatever env dict you pass.
   The box boots and starts downloading the DEFAULT 35B, not your model. You MUST take
   direct control after boot:
   ```
   supervisorctl stop llama          # stop the template's supervisor job
   pkill -9 -f llama-server          # kill the 35B it was downloading/serving
   pkill -9 -f 35B
   ```
   Then run your own server. This is why checking `ps aux` right after boot matters.

2. **The `hf` CLI is at `/venv/main/bin/hf`, not `huggingface-cli`.** `huggingface-cli` is
   not on PATH and the default python3 has no `huggingface_hub` module. Use the venv one:
   ```
   export HF_HOME=/workspace/.hf_home
   /venv/main/bin/hf download <repo> <file.gguf> --local-dir /workspace/model
   ```
   Download of a 5.78 GB file on ~870 Mbps took ~90s. Run it with `nohup ... &` and poll
   the target dir for the `*.gguf` (it lands in `.cache` first, then the final file).

3. **"unused tensor blk.NN.attn_* / ffn_*" warnings at load are normal** for the hybrid
   Gated-DeltaNet / MTP Qwen3.5 arch — it's the speculative/MTP head that llama.cpp
   ignores. Not an error; generation still works.

4. **External access goes through auth-gated caddy, not a direct port.** The template
   exposes `8000/tcp` → a public HostPort (e.g. 28848), which caddy reverse-proxies to
   llama-server's internal `18000`. The route requires a token:
   - `Authorization: Bearer <jupyter_token>`, OR
   - `Cookie: C.<instance_id>_auth_token=<jupyter_token>`
   The jupyter token comes from `show_instance` / the instance API (`jupyter_token`).

5. **Vast will NOT add a new exposed port to a RUNNING instance.** `PUT .../instances/<id>/`
   with a `ports` payload returns `{"success": true}` but the port map is unchanged on a
   running instance. Don't waste time trying to expose 18000 directly — route through the
   template's existing caddy port with the auth token instead.

6. **SSH proxy port failover:** `ssh5.vast.ai` port1 (15050) timed out on banner exchange;
   port2 (15051) worked. If one proxy port hangs, try the other. Direct-IP SSH
   (137.175.22.196:28899) rejected the key — use the proxy.

## Test-verification pattern (do this before handing over)

1. Local sanity: `curl -s http://localhost:18000/v1/models` inside the box.
2. Real generation, generous budget:
   ```
   curl -s http://localhost:18000/v1/chat/completions -H 'Content-Type: application/json' \
     -d '{"model":"x","messages":[{"role":"user","content":"Reply with exactly: hello"}],"max_tokens":2048,"temperature":0.2}'
   ```
   Confirm `finish_reason: stop` and non-empty `content` (reasoning models put the chain in
   `reasoning_content`; content comes after the think block — with a small budget you'll
   see empty content + `finish: length`, which is expected, not a bug).
3. External reachability: hit `http://<public_ip>:<hostport>/v1/chat/completions` from lin
   with the bearer token.

## Live pricing reference (reliable tier, 2026-08)

- RTX 5090 (32 GB): $0.30–0.39/hr — best price/context/perf for big-context GGUF serving.
- RTX 4090 (24 GB): $0.14–0.48/hr — fits Q4 27B + ~128–192K ctx, or 9B with lots of headroom.
- L40S (48 GB): $0.47–0.60/hr — full 1M ctx with bf16 KV.
- A100/H100: frequently 0 offers listed with the account filters — re-check.
- Billing per-hour, not per-second: a 25-min job still charges 1 hr.
