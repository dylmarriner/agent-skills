---
name: pi-extension-management
description: Install, remove, and verify pi coding agent packages.
---

# Pi Extension Management

pi packages come from npm (`npm:<pkg>`) or git (`git:github.com/<owner>/<repo>`), are recorded in
`~/.pi/agent/settings.json` -> `packages[]`, and unpack under `~/.pi/agent/npm/node_modules/` or
`~/.pi/agent/git/`. A package declares its own entrypoints in its `package.json` -> `pi.extensions[]`.

## Procedure

1. Inspect before installing:
   - `pi list` — installed packages and their resolved paths.
   - `npm view <pkg> --json` — `repository`, `time.created`/`time.modified`, version count. No
     repository field + a single `0.x` publish + no maintainer identity is an abandoned or squatted
     duplicate. Look for a scoped variant (`@scope/<name>`) before taking the bare name.
   - Reading installed packages under `node_modules/@earendil-works/**` is explicitly allowed (global
     AGENTS.md); anything else in `node_modules/` needs a reason.
2. Install: `pi install npm:<pkg>` (`-l` for project-local).
3. Verify the load — the `Installed <pkg>` banner only means the tarball landed and settings.json was
   written. Never report success from the banner alone.
4. On a collision, pick the winner by capability + maintenance, then `pi remove` the loser. A package
   that cannot load is not harmless: pi reprints its failure on every startup.

## Verify an extension actually loads

Load failures go to **stderr before any model call**, so this works even when every provider is down:

    pi -p --no-session "x" 2>&1 | grep -i "Failed to load"

A failure drops the extension **whole** — one colliding tool name kills every tool the package registers,
not just the duplicated one.

Positive proof that one specific extension initialised (no model call, no provider needed):

    pi --mode rpc --no-session -ne -e <pkg>/dist/index.ts < /dev/null

RPC mode emits that extension's own `extension_ui_request` messages, e.g.
`{"method":"setStatus","statusKey":"lsp"}`. `-ne` disables discovery while `-e <path>` still loads the
named file, isolating it from the rest of the profile.

## Rules

- **Duplicate tool names across packages are fatal to the later one.** Before installing, grep the
  candidate's declared tool names (`grep -rhoE '"[a-z_]+"' <pkg>/extensions <pkg>/dist`) against what
  `pi list` packages already register. Two packages registering `lsp_diagnostics` means the second never loads.
- **The config filename and schema belong to the package, not to pi.** Read the installed package's
  `README.md` and `docs/*.md` before writing any config. Packages often still read a legacy filename
  "with a warning" and never migrate it — a lingering warning usually means the schema is stale too,
  so rewrite it in the current schema rather than just renaming the file.
- **Separate provider failure from extension failure.** A `Connection error.` on stdout is the model
  endpoint being unreachable; extension load errors print regardless. Confirm which one you are looking at
  before concluding anything about a package.
- Long-lived profiles accumulate unrelated load-error noise. Report pre-existing collisions but do not
  "fix" them unasked — a package that shadows several others may be a deliberate umbrella (e.g. pi-code
  ships web/subagent/todo replacements).

## References and scripts

- `references/lsp-servers.md` — pi-lsp config schema, built-in catalog, probing a language server standalone.
- `scripts/lsp_check.py` — spawns every server in `~/.pi/agent/pi-lsp.json`, initializes it, opens a generated
  sample file, and asserts the push-on-open servers return diagnostics. Run after any LSP config change.
