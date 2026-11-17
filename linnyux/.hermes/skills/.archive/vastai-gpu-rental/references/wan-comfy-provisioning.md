# Wan 2.2 720p ComfyUI Provisioning — Session Transcript (2026-08-23)

Real session: rented a GPU on vast.ai for Wan 2.2 14B 720p NSFW video generation with a webui. All concrete IDs/tags/prices captured here.

## Account / wiring facts

- Account: inhumanekiller22@gmail.com, id 371540, can_pay true. Default credit ~$3.42.
- API key: `923f8d54467162fcc48c0d9bc27cf6ff1f531b180dec88c60ef0ef39d624f157`
- Registered SSH pubkey is kubuntux's `~/.ssh/id_rsa`; on lin copied to `~/.ssh/vast_id_rsa` (identical material).
- Vast MCP server dir on both hosts: `~/.hermes/mcp-servers/vastai-mcp/` (server.py, launch.sh, wrapper.py, tests, venv).
- MCP config block: `mcp_servers.vast` → `command: .../launch.sh`, env `VAST_API_KEY` + `SSH_KEY_FILE`/`SSH_KEY_PUBLIC_FILE`, `connect_timeout: 60`.

## Pricing seen (reliable tier rel≥0.95, cheapest first)

- RTX 4090 24GB: $0.276 / $0.294 / $0.298 / $0.303 / $0.322 per hr
- L40S 44GB: $0.535 (Türkiye, rel 0.999, CUDA 13.0) / $0.737 (Finland) / $0.801 (Taiwan)
- H100 SXM 80GB: $1.736 (Washington US, rel 0.999) / $2.516 (NL) / $2.592 (Czechia)
- A100 80GB and RTX 6000 Ada: 0 reliable offers at query time — not always available.

## Cost model for 720p video (Wan/LTX class)

Open video models generate ~5–10s clips, not minutes. A 5–10 min 720p video = 30–120 clips stitched (7200–14400 frames @24fps). Billing is per-hour, not per-second.

- LTX-Video (fast, realtime-ish): ~0.5–1.5 hr compute on a 4090 → ~$0.45–1.50
- Wan 2.2 / HunyuanVideo (best 720p, slow): ~2–6 hr on 4090 → ~$0.60–1.80; or ~3 hr on H100 → ~$7.50

Bottom line: ~$1–3 on a 4090 for quality; ~$5–8 for fast H100. NSFW is not a platform blocker on vast; Wan/Hunyuan/LTX base weights don't hard-censor at inference.

## Images / templates

- Wan2GP template id 531498, image `vastai/wan2gp` — GRADIO webui on internal 17860→7860, Jupyter 8080, Syncthing 8384, portal 1111. **BROKEN: jupyter entrypoint crashes in ~1s (client_run_time 1.1), flips to exited. Pivot away.**
- ComfyUI template id 525591, image `vastai/comfy` — Gradio webui internal 18188 (mapped, host port from `ports` 8188/tcp), Jupyter 8080, portal 1111, Syncthing. **Battle-tested, stays running. Preferred.**
- Tag used: `vastai/comfy:v0.32.0-cuda-12.9-py312` (manifest 200). `vastai/wan2gp:8681e9f-2026-08-21-cuda-12.9` also valid but entrypoint crashes.

## The :latest bug (root cause of the first dead instance)

`vastai/wan2gp` and `vastai/comfy` have NO `:latest` tag — only dated tags. Creating with the bare template image name (`vastai/wan2gp` = `:latest`) gave: `Error response from daemon: manifest for vastai/wan2gp:latest not found: manifest unknown`. Instance hung in `loading` ~11+ min burning $/hr. FIX: resolve explicit dated tag, verify manifest 200 (`curl -o /dev/null -w "%{http_code}" https://hub.docker.com/v2/repositories/<org>/<img>/tags/<tag>/`).

## Duplicate-instance bug

`create_instance` MCP call timed out at 120s ("TimeoutError" / "Connection closed") but the create LANDED server-side. Re-issuing produced TWO instances (48418815 and 48418889). ALWAYS check `show_instances` after a timeout before re-creating.

## Instance lifecycle observed (instance 48420151, final good one)

- Offer 38575006: L40S 44GB, $0.80/hr, rel 0.999, Taiwan, CUDA 12.8. bid_price 1.2.
- Created with template 525591 + image `vastai/comfy:v0.32.0-cuda-12.9-py312`, disk 300GB, ssh+jupyter true.
- Boot: loading → created → running (~3 min). status_msg: `success, running vastai/comfy_v0.32.0-cuda-12.9-py312/jupyter`. Stays running (doesn't exit like Wan2GP).
- Ports (from API): 8188/tcp → HostPort 29071 (ComfyUI webui), 1111→29943 portal, 8080→29670 Jupyter, 8288→29015.
- Webui: `http://118.163.199.123:29071/` → 401 (auth-gated). Working URL: `https://cloud.vast.ai/instances/48420151/` (console carries the portal cookie, returns 200).
- SSH: `ssh9.vast.ai:20150` user root. SSH proxy banner-exchange repeatedly timed out (routes via 184.72.132.0); direct-IP SSH blocked. Webui unaffected — don't block on SSH.

## API response shapes

- `GET .../instances/` → `{"instances": [ ...list... ]}`
- `GET .../instances/<id>/` → `{"instances": { ...DICT... }}` (NOT a list — `[...][0]` raises KeyError)
- Status fields: `actual_status` (loading/running/exited), `client_run_time` (1.1 = crash), `status_msg`, `ports` (dict `"<port>/tcp"` → list of HostPort), `ssh_host`/`ssh_port`, `public_ipaddr`, `jupyter_token`.
- `reliability2` is a fraction 0–1 (0.99 = good). Filter `{"gte": 0.95}`; `gte: 90` returns nothing.
- Offer search: `PUT https://console.vast.ai/api/v0/search/asks/` with `{"q":{filters},"select_cols":[...]}`; operators `{"eq":v}`/`{"gte":v}`; `order:[["dph_total","asc"]]`; `type:"on-demand"`.
- `start_instance` may return "Required resources are currently unavailable, state change queued" — restart proceeds; poll `actual_status`.

## Next steps for this instance (unfinished at session end)

1. Get SSH up (retry loop was running) → pull Wan 2.2 14B 720p weights (~60GB) + Wan video custom nodes into ComfyUI.
2. Confirm 720p resolution + NSFW-capable model card/presets in the webui.
3. Destroy instance when done to stop $0.80/hr billing.
