# ReMe (reme-ai) — standalone service and Hermes provider

Local-first, file-native memory: durable state is plain Markdown with frontmatter
and wikilinks under a workspace directory; indexes under `metadata/` are
rebuildable. Python >= 3.11. Observed on `reme-ai` 0.4.x.

## Install (standalone)

```bash
uv venv ~/venvs/reme --python 3.11
cd <ReMe checkout> && VIRTUAL_ENV=~/venvs/reme uv pip install -e ".[core]"
ln -sf ~/venvs/reme/bin/reme ~/.local/bin/reme
mkdir -p <checkout>/.reme          # workspace + log dir must exist before the unit starts
```

- Pin 3.11/3.12 with `--python`. On a box whose default python is newer,
  `faiss-cpu`, `zvec` and `polars` have no wheels and the install stalls or dies.
- `[core]` is the documented extra (agentscope wrapper + Studio assets). The base
  package ships no frontend, so `reme-ai[core]`/`[web]` is what makes
  `http://127.0.0.1:2333/` return 200.
- Editable is enough from a checkout. The full source build
  (`pip install -e reme_studio -e ".[core]"` plus `npm ci && npm run build:static`)
  is only for editing Studio itself; the PyPI `reme_studio` asset serves the UI.

## Env / LLM config

`reme/config/default.yaml` substitutes these from the process environment, and
nothing in the package calls `load_dotenv` — a `.env` in the checkout does nothing
by itself.

```ini
LLM_BACKEND=openai
LLM_MODEL_NAME=deepseek-chat
LLM_API_KEY=<key>
LLM_BASE_URL=https://api.deepseek.com/v1
```

Reuse an existing Hermes key without printing it:

```bash
KEY=$(grep -m1 '^DEEPSEEK_API_KEY=' ~/.hermes/.env | cut -d= -f2- | tr -d '"'"' \r')
BASE=$(grep -m1 '^DEEPSEEK_BASE_URL=' ~/.hermes/.env | cut -d= -f2- | tr -d '"'"' \r')
[ -n "$KEY" ] || { echo "NO KEY FOUND"; exit 1; }
umask 077
printf 'LLM_BACKEND=openai\nLLM_MODEL_NAME=deepseek-chat\nLLM_API_KEY=%s\nLLM_BASE_URL=%s\n' \
  "$KEY" "${BASE:-https://api.deepseek.com/v1}" > <checkout>/.env
chmod 600 <checkout>/.env; echo "key_len=${#KEY}"
```

Only `auto_memory`, `auto_resource`, `auto_dream`, `chat` and proactive refresh
need an LLM; file ops, BM25 search and wikilink traversal run without one.

**max_tokens ceiling:** `components.as_llm.default.parameters.max_tokens` defaults
to 65536, above most providers' output cap (DeepSeek: 8192). Override on the start
line: `components.as_llm.default.parameters.max_tokens=8192`.

## systemd --user unit

`WorkingDirectory` matters because the default workspace is `./.reme`.

```ini
[Unit]
Description=ReMe local-first memory service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=<checkout>
EnvironmentFile=<checkout>/.env
ExecStart=/home/<user>/venvs/reme/bin/reme start workspace_dir=<checkout>/.reme service.host=127.0.0.1 service.port=2333 components.as_llm.default.parameters.max_tokens=8192
Restart=on-failure
RestartSec=5
StandardOutput=append:<checkout>/.reme/service.log
StandardError=append:<checkout>/.reme/service.log

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload && systemctl --user enable --now reme
loginctl enable-linger <user>
systemctl --user show reme -p ExecStart --value   # confirm the overrides survived
```

`reme start` takes positional `key=value` overrides, not flags
(`reme start service.port=8181 workspace_dir=/tmp/reme-demo`).

## Verify before handing over

```bash
curl -s http://127.0.0.1:2333/version -H 'Content-Type: application/json' -d '{}'  # {"version":"...","success":true}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:2333/                    # Studio UI, expect 200
reme health_check
reme write path=digest/wiki/smoke name=Smoke description=smoke content="# Smoke

body"
reme search query="smoke" limit=3        # must return the file with a score (~0.8+)
reme read path=digest/wiki/smoke.md start_line=1 end_line=20
```

The LLM path — the only proof the credential works:

```bash
reme auto_memory \
  messages='[{"role":"user","name":"<Name>","content":"..."},{"role":"assistant","name":"<Agent>","content":"..."}]' \
  session_id=smoke memory_hint="<what to look for>"
```

**Every message dict needs `name`.** ReMe validates the array with AgentScope's
`Msg`, so a `{role, content}` pair is rejected with
`ValidationError: 1 validation error for Msg / name Field required` and no note is
written. Success prints `Created daily/<date>/<slug>.md` and writes
`session/dialog/<session_id>.jsonl`.

## Workspace layout

```text
<workspace>/
├── session/dialog/<session_id>.jsonl   # raw filtered conversations
├── daily/<date>.md                     # auto day-index (<!-- notes:auto --> block)
├── daily/<date>/<slug>.md              # distilled daily cards
├── digest/{personal,procedure,wiki}/   # long-term nodes
├── resource/                           # external material, watched
├── metadata/                           # rebuildable indexes/graphs
└── mem_session/                        # agent-wrapper sessions, not user memory
```

`.reme/` is gitignored in the ReMe checkout, so keeping the workspace at
`<checkout>/.reme` does not pollute the source tree.

Useful jobs beyond the basics: `status`, `reindex [scope=all]`, `daily_list`,
`daily_reindex date=<d>`, `traverse path=<p> depth=<n>`, `graph_snapshot`,
`list_tags`, `node_search`, `frontmatter_read|update|delete`, `move`, `delete`,
`chat query="..."`. `reme help` prints the live job list with argument shapes.

## Cleanup after smoke tests

- `reme delete path=digest/wiki/smoke` can answer `Error: not found` for a path
  that exists; `rm` the file instead — the index watcher drops it and `search`
  stops returning it within seconds.
- A direct `rm` leaves a stale bullet in the day-index: rebuild with
  `reme daily_reindex date=<YYYY-MM-DD>` (prints `0 note(s)` when clean).
- Never hand over a workspace with smoke-test nodes in it.

## Hermes provider wiring (optional)

```bash
hermes memory setup                    # pick reme -> http (endpoint) or embedded (workspace)
hermes config set memory.provider reme
hermes memory status                   # shows installed providers and the active one
```

- HTTP mode needs no ReMe SDK in Hermes' python — only the running endpoint (a
  second service on another port, e.g. 3456, keeps it separate from the
  standalone 2333 instance).
- Embedded mode needs `reme-ai[core]` in *Hermes'* python, not the standalone venv;
  it creates the application on a dedicated event-loop thread (no port, no second
  process).
- The plugin is `kind: exclusive`: switching to it turns the current provider
  (honcho, agentmemory) off. Read `hermes memory status` before and after.
- Provider config lives at `$HERMES_HOME/reme/config.json`; `${HERMES_HOME}/reme.json`
  is a legacy fallback for omitted fields.
- Keep the action HTTP service on loopback — it has no authentication of its own.
