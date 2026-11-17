# Llama-server chat-template reasoning_effort gate + agent-client (Hermes) compatibility

Session: 2026-08-28, serving `Qwen3.8-27B-Aggressive-Q4_K_P.gguf` + FastMTP draft on a vast L40S instance (ID 48994223, ssh proxy ssh8.vast.ai:34222), wired into Hermes as the `qwen27b-mtp` custom provider over an autossh tunnel (`-L 18080:localhost:8080`).

## The silent 500: `reasoning_effort` template gate

Modern reasoning models (Qwen3.x with `--jinja`) bake their chat template into the GGUF. That template hard-raises on unknown `reasoning_effort` values:

```
HTTP 500  Jinja Exception: Unexpected reasoning effort minimal.
Supported types are xhigh (default), medium, and low.
```

**Agent clients ship `reasoning_effort` that the template rejects.** Hermes (and other agent frameworks) send `reasoning_effort: minimal` by default. A raw `curl` chat-completion with no `reasoning_effort` field works fine — which is the trap: you'll debug the transport and conclude the model is fine while the real integration point (the agent's request body) is what 500s. Check the gateway/agent log line `API call failed ... provider=custom base_url=... model=... HTTP 500` — the Jinja `raise_exception` text is the smoking gun.

### Fix: patch the embedded template and pass it via `--chat-template-file`

1. Extract the verbatim template from the GGUF metadata (a one-shot python GGUF-header parser — see below). It stores `tokenizer.chat_template` as a KV string.
2. Edit the offending gate. Original (typical):
   ```
   {%- set resolved_reasoning_effort = reasoning_effort|default('xhigh') %}
   {%- if resolved_reasoning_effort not in ('xhigh', 'medium', 'low') %}
       {{- raise_exception('Unexpected reasoning effort ' ~ reasoning_effort ~ '. Supported types are xhigh (default), medium, and low.') }}
   {%- endif %}
   ```
   Replace the `raise_exception` with a clamp so unknown values map to a supported one instead of raising. Recommended mapping (matches Hermes levels):
   ```
   {%- set resolved_reasoning_effort = reasoning_effort|default('xhigh') %}
   {%- if resolved_reasoning_effort not in ('xhigh', 'medium', 'low') %}
       {%- set resolved_reasoning_effort = 'low' %}
   {%- endif %}
   ```
   (medium→medium, low & minimal→low, anything else incl. high/max/unknown→xhigh. `low`/`minimal` mapping to `low` keeps thinking brief.)
3. Add `--chat-template-file /path/qwen-template.jinja` to the llama-server command line, keep `--jinja`.
4. Restart llama-server (see persistence note below).

### GGUF template extraction (standalone, no gguf-py on the box)

```python
import struct
data = open("/root/models/model.gguf","rb").read()
off = 4; struct.unpack("<I", data[4:8]); off = 8
struct.unpack("<QQ", data[8:24]); off = 24   # n_tensors, n_kv
def rs():
    global off
    l = struct.unpack("<Q", data[off:off+8])[0]; off += 8
    s = data[off:off+l].decode("utf-8"); off += l; return s
def rv(t):
    global off
    if t == 8: return rs()
    if t == 9:
        at = struct.unpack("<I", data[off:off+4])[0]; off += 4
        n  = struct.unpack("<Q", data[off:off+8])[0]; off += 8
        return [rv(at) for _ in range(n)]
    sz = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1}[t]; v = data[off:off+sz]; off += sz; return v
for _ in range(struct.unpack("<I" and 0) if False else 0):...
# iterate n_kv: key=rs(); typ=unpack("<I",data[off:off+4])[0]; off+=4; val=rv(typ)
# when "template" in key: open("/root/qwen-template.jinja","w").write(val)
```

Do NOT hand-write a fresh template — the Qwen3.x template has vision/image_count macros, tool blocks, and reasoning-instruction injection you must preserve exactly. Patch the extracted one in place. Pull it to your local box, edit with a proper editor (shell here-doc quoting escapes `{%- %}` badly), push back with `scp`.

## Single-slot (`--parallel 1`) contention with an agentic client

A llama-server on a single GPU often runs `--parallel 1` (one slot). An agent like Hermes ships ~90K tokens of context (system prompt + memory + skill catalog + tool schemas) on EVERY turn and re-processes the whole thing at ~1400-2000 tok/s prompt phase before generating. Consequences:

- Per-turn latency ballooned to **210-248s** (`API call #1 ... in=93381 out=40 latency=210.0s`).
- Any second concurrent session serializes behind it. Telegram + cron + CLI all hammering one slot → the bot looks dead ("telegram not replying") when it is merely queued.
- The auxiliary title-generation call shares the same slot → "Request timed out" / "connection error" loops in the agent log.
- `--parallel 1` + `kv_unified=false` means each slot owns full KV; the free-VRAM check (`nvidia-smi`) is the ceiling for how many slots you can add. Bumping `--parallel 2-4` lets telegram + title-gen + cron run concurrently instead of serializing.

### Diagnosis (distinguish hurt-unresponsive from dead)
1. `curl` the model directly with the agent's exact failing field (`reasoning_effort=minimal`) — if 200, the model is fine, the problem is elsewhere.
2. Check the instance: `ps -o pid,etime,pcpu -p $(pgrep -f llama-server)` (high steady CPU = working) and tail the server log for `slot print_timing` / `prompt processing n_tokens=... progress=` — climbing progress = it IS answering, just slowly.
3. Mirror the agent log `API call #N ... latency=` and `Turn ended` timestamps against gateway `content_delivered=True` to confirm the reply landed.

## Making a single-slot, big-context server ACTUALLY fast for an agent client

Key facts that cost real time once you try to "fix" reply latency on a 262K-context L40S:

1. **`--parallel N` SPLITS the total `--ctx-size`, it does not multiply it.** With `--ctx-size 262144 --parallel 2`, each slot gets `n_ctx_slot = 131072` (total is still 262144, just partitioned). The server log line `load_model: initializing, n_slots = 2, n_ctx_slot = 131072` tells you the per-slot number directly. Do NOT "free up room for a second slot" by lowering `--ctx-size` below what the agent needs — the user explicitly rejected dropping the 262K budget (their whole reason for this instance is big context).

2. **The right lever to fit more slots without dropping context is KV-cache quantization.** `--cache-type-k q8_0 --cache-type-v q8_0` roughly halves KV footprint. On the 27B + FastMTP build this took VRAM from ~36GB used (9.4GB free) down to ~30.8GB used (14.6GB free) — enough headroom for `--parallel 2` at a full 2x131072 => 262144 total. Quantized KV on an L40S with flash-attn costs negligible quality on chat workloads.

3. **`--cache-idle-slots` is the actual reply-speed win.** It saves an idle slot's KV to the prompt cache and reuses it when the next request shares the prefix. Because an agent session re-sends the same *growing* history every turn, turn 2+ skips re-prefilling what turn 1 already computed. Measured effect on a growing 9-message conversation: every turn stayed **flat ~1.4-1.7s** (down from 210s) — no per-turn prefill cost. Verify on the server log (`--cache-idle-slots` is consumed by llama-server; the `--help` for this build did not list `--cache-reuse`, which is a different/older flag — use `--cache-idle-slots`).

4. **A `--spec-draft-model /*.gguf` (e.g. FastMTP, ~862MB) is a spec-decoder draft model, NOT a second full model.** It proposes tokens so the 27B can accept/reject in parallel (the MTP speedup — `draft acceptance`, `mean len` in the log). The user will ask "why are 2 models loaded" — the answer is: one real model (17GB) + a ~1GB accelerator. Don't strip it "to save VRAM"; it's what makes 37-83 tok/s possible for ~1GB.

5. **Bump `--batch-size`/`--ubatch-size`** (e.g. 2048->4096, 512->2048) for faster prompt-phase throughput on top of cache reuse.

## Persistence & restart on a vast instance

The instance's supervisor runs `/root/serve.sh` once via vast's `/.launch` (PID 1). To make any llama-server flag change survive:
1. Edit `/root/serve.sh` (add the `--chat-template-file` etc.).
2. `pkill -f llama.cpp/build/bin/llama-server`.
3. Relaunch detached: `setsid nohup bash /root/serve.sh > /root/serve.out 2>&1 < /dev/null & disown`.
   (A bare `nohup ... &` inside one SSH invocation dies with the session — `setsid` + `< /dev/null` + `disown` is what survives.)

## Provider wiring + subprocess restart reminder

- Hermes provider in `~/.hermes/config.yaml` under `providers:` (e.g. `qwen27b-mtp`, `base_url: http://localhost:18080/v1`, `api_key: <server --api-key>`). The key MUST match the llama-server `--api-key`.
- The vast MCP stdio server is a persistent subprocess — patch `server.py`, then kill the `venv/bin/python3 -u .../server.py` child (via `/proc/[0-9]*/cmdline`; plain `ps|grep` may be filtered in the Hermes shell); the watchdog respawns it with new code on next call.
- Full gateway model-swap + cron-pinning workflow is in the SKILL.md body (see below).