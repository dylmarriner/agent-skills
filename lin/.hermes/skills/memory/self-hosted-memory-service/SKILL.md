---
name: self-hosted-memory-service
description: "Stand up a self-hosted agent memory service (ReMe, mem0)."
version: 1.0.0
author: Hermes Agent
license: MIT
category: memory
platforms: [linux]
tags: [memory, systemd, uv, venv, service-deployment, local-first, reme]
metadata:
  hermes:
    tags: [memory, systemd, uv, venv, service-deployment, local-first, reme]
    related_skills: [agent-memory-backend, tailscale, multi-host-remote-config]
trigger: When the user asks to install a third-party memory engine as a standalone service ("install it as a standalone", "set up ReMe/mem0/agentmemory", "give my agent long-term memory that lives on disk"), or to fix one that installs but will not answer.
---

# Self-Hosted Memory Service

## When to Use

- "install it as a standalone" / "set up <memory engine> as its own service"
- An engine is installed but every command errors, or the service never answers
- The user wants agent long-term memory that lives on disk where they can read
  and edit it
- Wiring that same engine into Hermes as the active memory provider

Not this skill: a memory plugin owned entirely by one agent host with no service,
port, or on-disk store of its own.

Standing up a memory/knowledge engine as its own local service: isolated Python
or Node install, config from the process environment, a user-level systemd unit,
and a verification pass that actually exercises the model-backed path.

Engine-specific depth lives in `references/` — `references/reme.md` covers ReMe
(reme-ai): install, env vars, unit file, workspace layout, `auto_memory` payload
shape, cleanup. Read it before touching ReMe; the umbrella below stays
engine-agnostic.

## Procedure

**1. Recon — it may already be installed, and Hermes may already know about it.**

```bash
hermes memory status 2>/dev/null | head -40   # installed providers + which one is active
python3 -V; sed -n '1,40p' <checkout>/pyproject.toml
```

`hermes memory status` lists every provider plugin Hermes can see, including the
one you are about to install — so the wiring may be half-done already. Read the
project's declared language version before picking an interpreter.

**2. Install isolated, never into the system interpreter.**

```bash
uv venv ~/venvs/<tool> --python <version the project documents>
cd <checkout> && VIRTUAL_ENV=~/venvs/<tool> uv pip install -e ".[<extra>]"
ln -sf ~/venvs/<tool>/bin/<tool> ~/.local/bin/<tool>
```

Editable (`-e`) when the user owns the checkout — their edits then take effect
without reinstalling. The symlink into `~/.local/bin` is what puts the console
script on PATH; `~/venvs/<tool>` matches the per-tool venv convention.

Pin the interpreter. On a box whose default python is newer than the project's
supported band, heavy deps (faiss, vector stores, polars) have no wheels and the
install stalls or dies in a build.

**3. Config comes from the process environment, not from a `.env` file.**

```bash
grep -rn "load_dotenv" <package>/ | head    # decides whether a .env beside the checkout does anything at all
```

Most of these configs use `${VAR}` substitution resolved from `os.environ`, and
many never call `load_dotenv` — a `.env` in the checkout is then inert. The
reliable carrier is the unit's `EnvironmentFile=` (a real file, `chmod 600`).

Lift existing credentials from a machine-local secret store by pipeline so the
key never enters the transcript:

```bash
KEY=$(grep -m1 '^<PROVIDER>_API_KEY=' ~/.hermes/.env | cut -d= -f2- | tr -d '"'"' \r')
[ -n "$KEY" ] || { echo "no key found"; exit 1; }
umask 077; printf '...API_KEY=%s\n' "$KEY" > <checkout>/.env; chmod 600 <checkout>/.env
echo "key_len=${#KEY}"     # confirm presence without printing the value
```

**4. Run it as a `systemd --user` unit.**

```ini
[Unit]
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=<checkout>
EnvironmentFile=<checkout>/.env
ExecStart=/home/<user>/venvs/<tool>/bin/<tool> start workspace_dir=<checkout>/.<tool> service.host=127.0.0.1 service.port=<port>
Restart=on-failure
RestartSec=5
StandardOutput=append:<checkout>/.<tool>/service.log
StandardError=append:<checkout>/.<tool>/service.log

[Install]
WantedBy=default.target
```

```bash
mkdir -p <checkout>/.<tool>                 # log + workspace dirs must exist before first start
systemctl --user daemon-reload && systemctl --user enable --now <tool>
loginctl enable-linger <user>               # keeps it alive with no login session
```

Absolute path in `ExecStart` — a user unit gets a minimal PATH. `WorkingDirectory`
is load-bearing whenever the tool's default store path is relative.

**5. Verify the whole loop, not just the port.**

```bash
curl -s http://127.0.0.1:<port>/version -H 'Content-Type: application/json' -d '{}'
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:<port>/        # web UI, expect 200
<tool> health_check
# write -> index -> retrieve -> read
<tool> write path=... name=... description=... content="..."
<tool> search query="..." limit=3          # must return the file with a score
<tool> read  path=... start_line=1 end_line=20
```

Then exercise the one job that needs the credential (distillation, summarising,
agent chat). File ops and lexical search pass with no API key at all, so a green
health check says nothing about the model wiring — a real extract/consolidate call
is the only proof.

If embeddings are enabled, lexical hits prove nothing either: write a temporary
node and query it with a paraphrase that shares **no** keywords with the text. A
zero-hit result means the store is running BM25 only. Details and the score
breakdown to read: `references/embeddings.md`.

**6. Clean up your test artifacts before handing over.**

A memory store is the user's data: delete smoke-test nodes, rebuild any generated
index that still lists them, and confirm `search` no longer returns them. Never
deliver a workspace seeded with test memories.

**7. Handoff.**

`##` heading, then the daily-use commands, then a compact fact block (venv path,
CLI path, workspace, unit name, port, log path), then the gotchas that will bite
them, then at most two one-line offers. No narration of the recon. Disclose every
package you installed on the host and every file you created outside the install
root — you touched a machine, and silence about it reads as sloppy.

## Pitfalls

- **A CLI whose subcommands are HTTP jobs against its own daemon fails with a
  connection error when the daemon is down** (`httpx.ConnectError: All connection
  attempts failed` even for `--version` and `help`). That error means "service not
  running", never "install broken". Start the service before judging anything.
- **`.env` beside the checkout is inert unless the package loads dotenv.** Grep
  for `load_dotenv` first; otherwise put the vars in `EnvironmentFile=` or export
  them before starting the process.
- **Never paste an API key into the conversation or a command line that lands in
  `ps`/shell history.** Extract into a variable, write the file `0600`, print only
  the length.
- **Hand-written payloads fail validation when a required field is missing.**
  Engines built on a schema library reject partial dicts; the `ValidationError`
  names the field — add it and resend instead of concluding the engine is broken.
- **Default token caps are sized for big-context models and exceed most
  providers' output limits.** Override on the start line (these CLIs accept
  positional `a.b.c=value` config overrides) rather than editing packaged yaml.
- **A memory-provider plugin is usually `kind: exclusive`** — pointing Hermes at
  it turns the current provider off. Read `hermes memory status` before and after.
- **Do not edit a packaged `config.yaml` when the CLI takes overrides.** Positional
  overrides survive upgrades and keep the unit self-documenting.
- **The store is machine-local state.** Decrypting, migrating, or copying a store
  only works on the host that owns the key material; verify there.
- **Changing the embedding model or its dimension invalidates every stored vector.**
  The vector cache is keyed to the old width, so stop the service, delete the
  embedding-store directory under `metadata/` (rebuildable by design), start it and
  reindex — otherwise recall silently mixes two vector spaces. Same wipe whenever
  the provider's model reaches end of life and you swap ids.
- **A provider's `/models` list is a catalog, not your entitlements.** Status codes
  to read literally: 402 out-of-balance, 404 listed-but-not-entitled for the account,
  410 model end-of-life. Probe the exact id with a real request before wiring it, and
  take the embedding width the API returns rather than the one in the docs.
- **Do not treat a low-score hit on the generated day-index as a failure.** The
  day-index note is indexed like any other file and shows up as a weak extra result;
  judge recall by whether the *right* node is first.

## References

- `references/reme.md` — ReMe (reme-ai): install, LLM env vars, systemd unit,
  workspace layout, `auto_memory` message shape, cleanup, Hermes provider wiring.
- `references/embeddings.md` — turning on vector recall: the three config
  touchpoints, provider probing, wiping the vector cache on a model/dimension
  change, and the paraphrase query that actually proves semantic search works.
