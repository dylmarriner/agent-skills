---
name: vastai-gpu-rental
description: Rent and operate vast.ai GPU instances.
---

# Vast.ai GPU Rental & Provisioning

Rent and operate GPU instances on vast.ai. Covers the vast MCP server (`mcp__vast__*` tools), the REST API fallback, offer pricing, instance lifecycle, and the pitfall minefield that makes naive usage burn money on instances that never boot.

## The vast MCP server

A custom FastMCP server (`server.py`, ~73KB) lives at `~/.hermes/mcp-servers/vastai-mcp/` on both **kubuntux** (origin) and **lin** (copied). It exposes 22 tools: `show_user_info`, `show_instances`, `search_offers`, `search_templates`, `create_instance`, `destroy_instance`, `start/stop/reboot/recycle_instance`, `show_instance`, `logs`, `attach_ssh`, `ssh_execute_command`, `ssh_execute_background_command`, `ssh_check/kill_background_task`, `scp_upload`, `scp_download`, `search_volumes`, `label_instance`, `configure_mcp_rules`.

- Config block in `~/.hermes/config.yaml` under `mcp_servers.vast`, launched via `launch.sh` (sets `VAST_API_KEY`, `SSH_KEY_FILE`/`SSH_KEY_PUBLIC_FILE`, execs venv python on `server.py`). Stdio transport — `mcp.run()` with no args = stdio even though the log line prints "localhost:8000" (that string is cosmetic/hardcoded).
- To wire onto a new machine: copy the server dir (EXCLUDE `venv/` and `.git/`), rebuild venv with `python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt` (deps: fastmcp, mcp, paramiko, httpx), copy the registered SSH key, retarget `launch.sh` paths, add config via `hermes config set 'mcp_servers.vast' '<json>'`. Verify with `hermes tools list | grep vast` and a stdio handshake. Restart Hermes to load the tools.
- The account SSH pubkey registered with vast must match the key you SSH into instances with. The registered key is kubuntux's `~/.ssh/id_rsa`; on lin it's copied to `~/.ssh/vast_id_rsa` (same key material — compare `cut -d' ' -f2 <pubkey>`).

## Pricing reference (live offers, reliable tier)

Query `search_offers` or the REST API directly (the MCP search can 400 on its hardcoded `allocated_storage: 5.0` — see Pitfalls). Representative reliable (rel≥0.95) per-GPU on-demand hourly:

- RTX 4090 (24GB):  ~$0.28–0.36/hr
- L40S (44–48GB):   ~$0.54–0.80/hr
- H100 SXM (80GB):  ~$1.74–2.94/hr
- A100 80GB / RTX 6000 Ada: often 0 reliable offers listed — re-check

Billing is per-hour (not per-second); a job finishing in 25 min still charges 1 hr on most offers. A bare account has ~$3.40 credit by default; the H100 fast route needs a top-up.

## The vast REST API (reliable fallback when MCP search misbehaves)

Header: `Authorization: Bearer <VAST_API_KEY>`. API key for this account: `923f8d54467162fcc48c0d9bc27cf6ff1f531b180dec88c60ef0ef39d624f157`. **Canonical source is the `VAST_API_KEY` in `~/.hermes/config.yaml` (mcp_servers.vast env). Do NOT use `~/vast_api.key` — it holds an old REVOKED key (512e…) that returns `auth_error Invalid user key`.**

- Search offers: `PUT https://console.vast.ai/api/v0/search/asks/` with `{"q":{...filters...},"select_cols":[...]}`. The `q` filters use operators `{"eq":v}`, `{"gte":v}`. `order` is a list `[["dph_total","asc"]]`, `type: "on-demand"`.
- **`select_cols` MUST be explicit named columns — `["*"]` is rejected** (`select_cols.0 must match ^[a-zA-Z0-9_]+$` → 400 Bad Request). This is the ROOT CAUSE of the MCP `search_offers` 400 (its `server.py` hardcodes `select_cols: ['*']`). Always pass a real column list (id, gpu_name, num_gpus, dph_total, geolocation, reliability2, inet_down, disk_space, cpu_ram, ...).
- List instances: `GET https://console.vast.ai/api/v0/instances/` → `{"instances":[...]}`. IMPORTANT: the single-instance endpoint `GET .../instances/<id>/` returns `instances` as a **dict** (not a list), so `[...][0]` raises KeyError — use `d.get('instances',{})` and treat it as a dict.
- **User/account profile: `GET https://console.vast.ai/api/v0/users/current/` takes NO `owner` param.** Adding `?owner=me` (which `/instances*` endpoints accept fine) returns **400 Bad Request**. Call it bare. Returns username, email, `credit` (spendable balance), `id`, `total_spend`.
- Instance status fields: `actual_status` (loading/running/exited), `client_run_time`, `status_msg`, `ports`, `ssh_host`/`ssh_port`, `public_ipaddr`, `jupyter_token`.

Useful query filters: `{"verified":{"eq":true},"external":{"eq":false},"rentable":{"eq":true},"rented":{"eq":false},"gpu_name":{"eq":"RTX 4090"},"num_gpus":{"gte":1},"reliability2":{"gte":0.95}}`.

## Webui / access pattern

The console URL is the reliable way in and carries auth: `https://cloud.vast.ai/instances/<instance_id>/` (returns 200). Direct host:port webui hits return **401** (token-gated) — the vast console issues the portal cookie. This is normal, not a failure.

- ComfyUI template: Gradio webui on internal 18188, mapped to a host port. Port mappings come back in `ports` (e.g. `8188/tcp` → HostPort).
- Jupyter token is in the instance API as `jupyter_token`.

## Pitfalls (hard-won, all cost real money or time)

1. **vast template images have NO `:latest` tag.** `vastai/wan2gp` and `vastai/comfy` both only ship dated tags (e.g. `vastai/wan2gp:8681e9f-2026-08-21-cuda-12.9`, `vastai/comfy:v0.32.0-cuda-12.9-py312`). Using the bare image name = `:latest` = **"manifest unknown"**, instance hangs in `loading` forever burning $/hr. ALWAYS resolve the explicit dated tag and verify its manifest returns 200 before creating. Check tags: `curl https://hub.docker.com/v2/repositories/<org>/<img>/tags?page_size=25`; verify: `curl -o /dev/null -w "%{http_code}" https://hub.docker.com/v2/repositories/<org>/<img>/tags/<tag>/` (200 = good).
2. **The MCP `create_instance` call times out at 120s (or drops with "Connection closed") but the create still LANDS.** After ANY create timeout/error, immediately `show_instances` / GET the instances list to check for a new instance. Do not blindly re-create (that's how two instances got spun up).
3. **`reliability2` is a FRACTION (0.99), not a percentage.** Filtering `gte: 90` excludes everything. Use `gte: 0.95` for "reliable". Cheapest offers often show ~0.99 — filter on it to avoid junk tier.
4. **The MCP `search_offers` can return 400 "Bad Request"** because the server builds a query with a hardcoded `allocated_storage: 5.0` that conflicts on some requests. Fall back to the REST API directly (reliable). Also its query string is space-separated `key=value` (it does `query.split()`), NOT gpu_name with underscores — use `gpu_name=RTX_4090`.
5. **Some bespoke template images crash their entrypoint in ~1s** (the Wan2GP jupyter image: `client_run_time 1.1`, flips to `exited` seconds after `running`). The official `vastai/comfy` image is far more battle-tested and stays up. If an instance exits immediately after booting, stop it (stop billing), destroy it, and pivot to the ComfyUI image — don't keep paying for a broken container.
6. **SSH proxy banner-exchange timeouts are common** (routing through `184.72.132.0` / `ssh9.vast.ai`), and direct-IP SSH is usually blocked (only the vast proxy routes it). The webui/console still works. Don't block on SSH — use the console URL. Hammering SSH in a background retry loop is fine but the webui is reachable independently.
7. **`start_instance` can return "Required resources are currently unavailable, state change queued"** — the restart is queued and will proceed; poll `actual_status`.
8. **MCP stdio servers are PERSISTENT subprocesses — editing `server.py` does NOT take effect until you kill the running child.** After patching `~/.hermes/mcp-servers/vastai-mcp/server.py`, the `mcp__vast__*` tools keep returning the OLD code until you `kill <pid>` the `venv/bin/python3 -u .../server.py` child (find it via `/proc/[0-9]*/cmdline`, since a plain `ps ... | grep` may be filtered in the Hermes shell). The watchdog (`mcp_stdio_watchdog.py --ppid <hermes>`) respawns it with the new code on the next call. Diagnose "Error getting user info / 400" by curl-ing the API yourself first to confirm whether the MCP server or the API is at fault.
9. **`select_cols: ["*"]` is rejected by `/search/asks/`** (columns must match `^[a-zA-Z0-9_]+$`). The MCP `search_offers` hardcodes `['*']`, so it 400s on every call regardless of query — this is the real root cause behind pitfall 4. Go straight to the REST API with named columns.
10. **Create-in-a-loop footgun: vast returns `"success": true` (SPACE after colon).** `grep -q '"success":true'` silently misses → the loop never breaks → **N instances get created and billed** (a 5-offer loop spun up 5 boxes on a $2.54 balance). Parse the response with JSON (`python3 -c "import sys,json;sys.exit(0 if json.load(sys.stdin).get('success') else 1)"`) to test success, or grep `'"success" *: *true'`. On ANY multi-create, `DELETE .../instances/<id>/` the extras immediately — they bill from creation.
11. **Match the card to the ACTUAL workload before renting; on a low balance default to cheapest-that-fits, not 'best-fit headroom'.** Dylan rents for one of two very different jobs: (a) big-context TEXT agentic work → needs 1M-native text models + a big card + a 1M ctx flag, OR (b) vision/document (PDFs, images) → context is a NON-issue (page ≈ 2K tokens as an image) and an 18 GB VL Q4_K_M runs on a cheap 24 GB 4090 at ~half the $/h of a 5090. Renting a 5090 and sizing ctx for text when the ask is vision wastes money AND invites the "why so expensive / only 130k ctx" pushback — those are signals you sized for the wrong workload. Confirm text-big-context vs vision/document up front; the model type determines the card AND whether context matters.

## Serving a model that has no GGUF (HF discovery) + Blackwell/Ada arch matching

**Model repo is safetensors-only?** Find a GGUF quant of the SAME model via the HF search API (`?search=<model> GGUF`); reliable quants come from mradermacher (full ladder + mmproj), noctrex, Tipur, McG-221. Get REAL file sizes with `?blobs=true` (HEAD `content-length` is absent on the HF redirect). If it's a vision model, grab the `mmproj` too (`--mmproj` is required for image input). Full recipe: `references/qwen3-vl-gguf-serving-and-hf-discovery.md`.

**Match llama.cpp CUDA arch to the GPU — it is NOT one-size-fits-all:**
- Ada (RTX 4090, L40S, RTX A6000): `-DCMAKE_CUDA_ARCHITECTURES=89`
- Blackwell (RTX 5090, GB202, sm_120): `-DCMAKE_CUDA_ARCHITECTURES=120` AND a base image with CUDA **≥ 12.8** (e.g. `nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04`). Building arch 89 on a 5090 fails.
- The CUDA cudnn-devel image is a multi-GB pull — instance sits `loading`/`Pulling fs layer` ~10+ min; **billing starts at creation, not at running**. On a slow host the pull stalls 16+ min on ONE fs layer (status_msg never advances) — destroy and re-create on a fresh host with the leaner `...-devel-ubuntu22.04` (no cudnn) image instead of waiting it out.
- **HF anonymous downloads are throttled PER-connection** (~KB/s) — use `aria2c -x16 -s16 -c` (~68 MB/s aggregate), not a single `curl`. Pivot-host + aria2 + llama.cpp 0.3.0 thin-launcher (`llama-server` is now a ~17 KB launcher over `libllama-server-impl.so` — verify via `src/models/` arch file, not binary size) and VL vision-test detail: `references/qwen3-vl-gguf-serving-and-hf-discovery.md`.

**SSH: `Permission denied (publickey)` while the instance is `loading` is NORMAL** — vast injects the account key only once `actual_status` flips to `running`. Poll status to running before hammering SSH (background a ready-watcher). The vast proxy TCP port being open is not a ready signal.

When the whole point of the instance is to power an agent (Hermes custom provider over an autossh tunnel), two llama-server behaviors masquerade as "the vast instance is broken":

1. **The GGUF chat template hard-500s on the agent's `reasoning_effort`.** Reasoning models (Qwen3.x with `--jinja`) bake a template that `raise_exception`s on any `reasoning_effort` outside `(xhigh, medium, low)`. Hermes sends `minimal` → `HTTP 500 Jinja Exception: Unexpected reasoning effort minimal` on every turn, while a bare curl (no field) works. Fix: extract the embedded template from the GGUF metadata, replace the `raise_exception` with a clamp to `'low'`, and add `--chat-template-file` to the server. Full extract/patch/restart recipe: `references/llama-reasoning-template-and-agent-contention.md`.
2. **Single-slot (`--parallel 1`) contention.** Agent turns ship ~90K tokens of context and re-process it all per turn; concurrent sessions (telegram + cron + CLI) serialize at 210-248s each and the aux title-gen times out — the bot looks dead when it's just queued. Diagnose via direct curl with the failing field (200 = model fine) + `slot print_timing`/`prompt processing progress=` in the server log (climbing = working). Bump `--parallel 2-4` if free VRAM allows (`nvidia-smi`), and restart detached with `setsid nohup bash /root/serve.sh < /dev/null & disown` (bare `nohup &` dies with the SSH session). Persist flag changes in `/root/serve.sh`; edit server.py then kill the stdio child to pick up MCP patches.

### Swapping Hermes's default model to the instance + keeping cron jobs alive

- Set the gateway default: `hermes config set model.default <model>` and `hermes config set model.provider <provider>` (also `model.api_mode chat_completions`). The config file is write-protected — use the `hermes config set` CLI, not a file patch. Restart the gateway: `systemctl --user restart hermes-gateway`; wait for `[Telegram] Connected ... polling` in `~/.hermes/logs/gateway.log`.
- **Changing the global model breaks unpinned cron jobs** — they "fail closed" next run (`Skipped to prevent unintended spend: global inference config drifted ... unpinned`). Pin each inference cron job to the new model: `hermes cron edit <job_id> --provider <provider> --model <model>`. No-agent script jobs (deliver=local, Mode: no-agent) are unaffected.
- **Corrupt `~/.hermes/cron/executions.db` aborts every cron run** with `database disk image is malformed` — even `cron run` fails. The job definitions live in `jobs.json` (often still fine). Fix: move the corrupt db aside, then recreate it with Hermes's exact schema (`executions` table + 2 indexes; source of truth: `~/.hermes/hermes-agent/cron/executions.py` `_initialize_schema`), then `hermes cron run <id>` to confirm the gateway can write.

## Workflow for a fresh GPU job

1. Search offers via REST API (reliable tier, rel≥0.95, matching gpu_name + cuda_max_good vs the image's cuda tag).
2. Pick the template (ComfyUI `vastai/comfy` preferred over bespoke) and RESOLVE the explicit dated image tag; verify manifest 200.
3. `create_instance` with offer_id, image=explicit tag, disk (250–300GB for Wan weights), ssh+jupyter true, template_id, bid_price slightly above asking.
4. On timeout/error, verify creation landed via instances list.
5. Monitor `actual_status` → running; confirm it stays up (not exited in ~1s).
6. Hand over the console URL `https://cloud.vast.ai/instances/<id>/` for the webui; try SSH in parallel but don't block on it.
7. For Wan 2.2 720p: after SSH is up, pull the 14B 720p weights (~60GB) + Wan video custom nodes into ComfyUI.

## References

- `references/wan-comfy-provisioning.md` — full transcript of the Wan 2.2 720p ComfyUI provisioning session: exact image tags, offer IDs, the Wan2GP crash, duplicate-instance bug, and API response shapes.
- `references/llama-reasoning-template-and-agent-contention.md` — fixing the GGUF chat-template `reasoning_effort` gate so agent clients (Hermes) stop 500-ing; single-slot `--parallel 1` contention with agentic clients; detached restart + persistent serve.sh. (Session 2026-08-28, Qwen3.8-27B + FastMTP on L40S.)
- `references/qwen3-vl-gguf-serving-and-hf-discovery.md` — serving a safetensors-only abliterated model (Qwen3-VL-30B-A3B) as GGUF: HF quant-repo search + `?blobs=true` sizes, Blackwell sm_120 / CUDA≥12.8 provisioning vs Ada arch 89, SSH-key-lands-at-running timing. (Session 2026-09-03.)
