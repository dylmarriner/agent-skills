---
name: claude-mem-shared-memory
description: Use when installing or fixing claude-mem shared memory.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [claude-mem, memory, codex, claude-code, hooks, sqlite]
    related_skills: [claude-code, codex, agent-memory-backend]
---

# claude-mem shared memory (Claude Code + Codex)

## When to Use

- Installing or re-wiring claude-mem into Claude Code, Codex, or another harness.
- Memory recorded in one harness is invisible in the other.
- claude-mem hooks stop firing after a plugin or Codex upgrade.
- Choosing or repairing the observer LLM (quota burn, 400s from the provider).

One SQLite corpus at `~/.claude-mem/claude-mem.db`, one worker on port 37700, written and read by every harness that has the plugin/hooks installed. Adding a harness is a wiring job, not a new database.

## Install shape per harness

- **Claude Code**: plugin `claude-mem@thedotmack` (marketplace `thedotmack`), enabled in `~/.claude/settings.json` under `enabledPlugins`. Hooks come from the plugin's `hooks/hooks.json`.
- **Codex**: plugin `claude-mem@claude-mem-local`, a *local* marketplace pointing at the Claude plugin checkout:
  `codex plugin marketplace add claude-mem-local /home/<user>/.claude/plugins/marketplaces/thedotmack`
  then `codex plugin add claude-mem@claude-mem-local`. Hooks come from `hooks/codex-hooks.json`.
- Codex hooks resolve the plugin root dynamically (env `CLAUDE_PLUGIN_ROOT`, then a scan of `~/.claude/plugins/cache/thedotmack/claude-mem/<version>`), so the Codex side keeps working even when its own plugin cache lags a version.

## The two settings that decide whether memory is actually shared

1. `CLAUDE_MEM_SESSION_START_INCLUDE_ALL_SOURCES=true` in `~/.claude-mem/settings.json`.
   Default `false` scopes SessionStart context to the harness that wrote it (`context.ts` appends `&platformSource=<platform>`), so Codex never sees Claude observations and vice versa. This is the single switch that makes memory *shared* rather than per-harness.
2. `sdk_sessions.platform_source` records `claude` or `codex` per session; `observations` inherit it through `memory_session_id`. Verify with:
   `sqlite3 ~/.claude-mem/claude-mem.db "SELECT platform_source,COUNT(*) FROM sdk_sessions GROUP BY 1;"`

## Provider selection (the observer LLM)

`CLAUDE_MEM_PROVIDER` in `~/.claude-mem/settings.json` drives the AI that compresses tool use into observations.

- `openai-compatible` + `CLAUDE_MEM_OPENAI_COMPAT_*` is the documented generic OpenAI-shaped provider.
- **Pitfall**: every HTTP provider hardcodes `temperature: 0.3` (`OpenAICompatProvider.ts`, `OpenRouterProvider.ts`). Current OpenAI reasoning models reject anything but the default (1) with `Unsupported value: 'temperature' does not support 0.3 with this model`. The `openai-compatible` provider has **no** temperature knob; the OpenRouter provider does, via `CLAUDE_MEM_OPENROUTER_EXTRA_BODY`.
- Working config for an arbitrary OpenAI-compatible endpoint whose model pins temperature:
  `CLAUDE_MEM_PROVIDER=openrouter`, `CLAUDE_MEM_OPENROUTER_BASE_URL=<endpoint>/v1`, `CLAUDE_MEM_OPENROUTER_MODEL=<model>`, `CLAUDE_MEM_OPENROUTER_EXTRA_BODY={"temperature": 1}`.
  The OpenRouter client doubles as a plain OpenAI client when the base URL is not `openrouter.ai`: it sends `model` (no `models` array), `stream: false`, and no `usage`/`reasoning` fields. Extra body merges last and can override ordinary fields; it can never set `model`/`messages`/`stream`/`max_tokens`.
- The `max_tokens` -> `max_completion_tokens` mismatch is handled automatically by the retry wrapper (`openrouter-token-compatibility.ts`) on a 400 that names the parameter.
- API keys live in `~/.claude-mem/.env` (mode 600), whitelisted names only: `OPENAI_COMPAT_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_*`, `GEMINI_*`. Put them there, not in `settings.json`.
- Disable tier routing when the endpoint has no `haiku`/`sonnet`: `CLAUDE_MEM_TIER_ROUTING_ENABLED=false`, and point every `CLAUDE_MEM_TIER_*_MODEL` at a real model so a stray `$TIER:` alias cannot leak.
- Leaving `CLAUDE_MEM_PROVIDER=claude` spends the user's Claude subscription quota (visible as `rateLimits` in `/api/health`). Switch the provider when the plan matters.

## Self-hosted observer (llama.cpp, no cloud, no quota)

The observer is whatever `CLAUDE_MEM_PROVIDER` names, and the worker makes the request — so a self-hosted endpoint must be reachable from the worker host and sized against the worker host's hardware, not yours.

Serve it with llama.cpp's prebuilt Vulkan build (no compile):

```sh
curl -fsSL -o /tmp/llama.tar.gz \
  https://github.com/ggml-org/llama.cpp/releases/download/<b-build>/llama-<b-build>-bin-ubuntu-vulkan-x64.tar.gz
mkdir -p /opt/llama.cpp && tar xzf /tmp/llama.tar.gz -C /opt/llama.cpp --strip-components=1
/opt/llama.cpp/llama-server --list-devices
```

Then a systemd unit runs `llama-server` on `127.0.0.1:8081` and claude-mem uses the `openai-compatible` provider against it — that provider takes `temperature` and `max_tokens` as sent, so a non-OpenAI model has no parameter problems:

```
CLAUDE_MEM_PROVIDER=openai-compatible
CLAUDE_MEM_OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8081/v1
CLAUDE_MEM_OPENAI_COMPAT_MODEL=<filename>.gguf
CLAUDE_MEM_OPENAI_COMPAT_API_KEY=            # empty: the endpoint is local
```

Flags that matter: `--reasoning off` (a thinking model otherwise answers with a reasoning trace instead of the observation XML), `--jinja`, `-ctk q8_0 -ctv q8_0`, `--parallel 1` with `CLAUDE_MEM_MAX_CONCURRENT_AGENTS=1`, and an explicit `--ctx-size`.

Also match the observer prompt budget to the served window, or the model is handed a transcript it cannot read:

```
CLAUDE_MEM_OBSERVER_CONTEXT_WINDOW=16384
CLAUDE_MEM_OBSERVER_MAX_CONVERSATION_CHARS=24000
CLAUDE_MEM_OBSERVER_MAX_OUTPUT_TOKENS=2048
```

### Size the model against real free VRAM, and measure before wiring

Two traps, both of which cost a full download to discover:

1. **The card reports less than the spec sheet.** `llama-server --list-devices` and `/sys/class/drm/card*/device/mem_info_vram_used` give the truth. A 4 GB RX 470 with an active desktop session (xrdp) reported 4096 MiB total and only ~3 GiB free.
2. **`--fit` keeps a model loaded but not fast.** With a 5 GB model on that card, `--fit` put 3.3 GB in VRAM and the rest on CPU; llama.cpp then chose `n_threads = 4` and generation ran at **2.4 tok/s** — 91 s for a 126-token observation. A model that fits the card *entirely* ran at **12 tok/s**, 10.6 s for the same work.

Benchmark with claude-mem's exact request shape (`model`, `messages`, `temperature: 0.3`, `max_tokens`, `stream: false`) and check the reply contains `<observation>`/`<title>` and no ` thinking` block, before pointing the worker at it.

### The cloud path it replaces is not neutral

A hosted observer on a metered plan fails under claude-mem's own request size: the observer sends ~58 k-token prompts, which trips per-minute token limits and shows up as repeated `Observer failed {kind=rate_limit}` in the worker log while sessions keep retrying. A local endpoint has no TPM ceiling.

## Multi-machine mesh (one corpus, N machines)

One machine hosts the worker; every other machine points at it over Tailscale. There is no sync and no second database: remote clients speak the same HTTP API as local ones.

1. **Host** binds the worker to its Tailscale IP. `CLAUDE_MEM_WORKER_HOST=100.x.y.z` on the host makes the worker listen on that address only (loopback and LAN are not bound), `CLAUDE_MEM_WORKER_AUTOSTART=true`.
2. **Every client** sets the same `CLAUDE_MEM_WORKER_HOST` and `CLAUDE_MEM_WORKER_PORT` and `CLAUDE_MEM_WORKER_AUTOSTART=false` (otherwise each machine spawns its own worker and you get N private corpora that look like one).
3. `CLAUDE_MEM_PUBLIC_URL=http://<host>:<port>` makes viewer links name the shared worker instead of localhost.

Remote access works because the worker's DNS-rebinding guard (`isTrustedWorkerHost` in `http/middleware.ts`) always admits IP-literal `Host` headers — no `CLAUDE_MEM_ALLOWED_ORIGINS` entry is needed for an IP. Hooks and the CLI send no `Origin`, so CORS does not apply either. The only `Origin`-gated endpoints are `DELETE` and Observation TV.

`CLAUDE_MEM_WORKER_HOST` naming an address that is **not** local is the supported client shape: the spawn path fails loudly with `EADDRNOTAVAIL` rather than starting a second worker.

### Prerequisites on every machine

- **Bun.** Both the worker and `scripts/bun-runner.js` are Bun programs; there is no node fallback. `bun-runner.js` exits with "Bun not found" and the hook silently produces no output.
- **Plugin runtime dependencies.** A bare `git clone` of the marketplace repo has no `node_modules`; without `bun install` in `plugin/` every hook dies with `Cannot find module 'zod/v3'`. This is also why the upstream npm installer can fail with `EALLOWSCRIPTS` — install deps with `bun install` directly.

### Project identity across machines

Injection is scoped by project name, and the default name is derived from the cwd. The same repo checked out at different paths on different machines therefore becomes two projects that never see each other. `CLAUDE_MEM_PROJECT_ENVIRONMENTS` fixes this:

```json
[{"name": "Maer-Ken", "patterns": ["Maer-Ken", "**/Maer-Ken"]}]
```

Globs are matched against the full normalized path **and** the basename (`matchesAnyGlob` in `utils/project-filter.ts`), so a bare repo name unifies that checkout everywhere. Set the same array on the host and on every client.

### Availability

Hooks start the worker lazily, so a host that never runs an agent itself would stay down. Install a watchdog on the host:

* `claude-mem-worker-watchdog` — curls `/api/health` on the Tailscale IP and runs `worker-service.cjs start` only when it is not answering.
* `claude-mem-worker.service` — `Type=oneshot`, `RemainAfterExit=yes`, `After=tailscaled.service`, `User=<host user>`.
* `claude-mem-worker.timer` — `OnBootSec=90`, `OnUnitActiveSec=5min`, `Unit=claude-mem-worker.service`.

Do not point a `Type=simple` unit at `worker-service.cjs --daemon`: the daemon flag forks, systemd sees the parent exit, and the unit restart-loops.

### Merging two existing corpora

Copy rows, never the file. Sections are disjoint per project, so import by project and skip any project the target already has. Parent `sdk_sessions` first, remapping the autoincrement `id` for tables that carry `session_db_id`; `observations` and `session_summaries` reference `memory_session_id`, which is already unique and is copied verbatim. After inserting, rebuild both FTS tables (`INSERT INTO observations_fts(observations_fts) VALUES('rebuild')`) — they are content-linked and a plain row copy leaves them empty. Assert `PRAGMA integrity_check` is `ok` and `PRAGMA foreign_key_check` returns no rows, and keep a `claude-mem.db.pre-merge-<timestamp>` copy.

### Reusable installer

`claude-mem-shared-setup.sh --role host|client [--host <ip>] [--port <port>] [--check]` does all of the above idempotently: bun bootstrap, shallow marketplace clone, `bun install`, settings merge, Claude plugin enablement, Codex marketplace/plugin install, local-worker warning, and (host role) credential write from `OPENROUTER_API_KEY`. Install it at `~/.local/bin/claude-mem-shared-setup` on clients and `/usr/local/bin/claude-mem-shared-setup` on the host.

## Codex hook trust: the upgrade trap

Codex skips non-managed hooks whose current hash is not in `[hooks.state."<key>"] trusted_hash` in `~/.codex/config.toml`. Re-adding or upgrading the plugin changes `hooks/codex-hooks.json`, so the stored hashes stop matching and **every claude-mem hook silently stops running** — no error, hooks just never fire while the MCP server still starts.

Symptom: `codex exec` prints `hook: SessionStart` etc. for *other* plugins, but `sdk_sessions` gains no `platform_source='codex'` row.

Fix: open the Codex TUI in a pty, answer the startup prompt:

```
Hooks need review
5 hooks are new or changed.
› 1. Review hooks
  2. Trust all and continue
  3. Continue without trusting (hooks won't run)
```

Send `\x1b[B\r` (down + Enter) to pick **Trust all and continue**. Codex writes the five correct hashes; verify with:

```sh
python3 -c "import tomllib;c=tomllib.load(open('$HOME/.codex/config.toml','rb'));print([k for k in c.get('hooks',{}).get('state',{}) if 'claude-mem' in k])"
```

Do this after every claude-mem version bump. `codex exec` cannot approve hooks; `--dangerously-bypass-hook-trust` bypasses for one run instead of trusting.

## Cold-start the worker

Start it with the plugin's own launcher:

```sh
P=$HOME/.claude/plugins/cache/thedotmack/claude-mem/<version>
node "$P/scripts/bun-runner.js" "$P/scripts/worker-service.cjs" start   # stop | restart
curl -s http://127.0.0.1:37700/api/health
```

Health reports `ai.provider` and `ai.authMethod`; an empty `rateLimits` object means no subscription provider is in use. A stale chroma lock (`data dir already owned by PID <dead>`) clears once the worker is restarted cleanly.

## Verify end to end without touching a real project

Feed the hook CLIs a synthetic payload; they read JSON on stdin.

```sh
P=$HOME/.claude/plugins/cache/thedotmack/claude-mem/<version>
cd /tmp/probe
echo '{"hook_event_name":"SessionStart","session_id":"probe-1","cwd":"/tmp/probe","source":"startup"}' \
  | CLAUDE_MEM_CODEX_HOOK=1 node "$P/scripts/bun-runner.js" "$P/scripts/worker-service.cjs" hook codex context
echo '{"hook_event_name":"UserPromptSubmit","session_id":"probe-1","cwd":"/tmp/probe","prompt":"..."}' \
  | CLAUDE_MEM_CODEX_HOOK=1 node "$P/scripts/bun-runner.js" "$P/scripts/worker-service.cjs" hook codex session-init
echo '{"hook_event_name":"PostToolUse","session_id":"probe-1","cwd":"/tmp/probe","tool_name":"Bash","tool_input":{"command":"npm test"},"tool_response":{"output":"..."}}' \
  | CLAUDE_MEM_CODEX_HOOK=1 node "$P/scripts/bun-runner.js" "$P/scripts/worker-service.cjs" hook codex observation
```

For the Claude side use `hook claude-code context` (with `CLAUDE_PLUGIN_ROOT` set to `$P`). Poll `observations.generated_by_model` for the configured model, then delete the probe rows so project memory stays clean. A tool call with a trivial response legitimately yields `obsCount=0` — the observer is allowed to answer with no observation.

## Never trust the exit code alone

A hook can return `{"continue":true}` while the observer request fails; the truth is in `~/.claude-mem/logs/claude-mem-<date>.log` (`Observer failed {provider=...}`).
