---
name: agent-hook-troubleshooting
description: Use when an agent harness hook fails or stops firing.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hooks, codex, claude-code, plugins, diagnostics]
    related_skills: [claude-mem-shared-memory]
---

# Agent harness hook troubleshooting

## When to Use

- A harness reports `Hook failed` / `hook exited with code N`.
- Hooks that used to fire stop firing silently, so tooling behind them stops recording.
- After installing, updating, or removing a plugin that ships lifecycle hooks.

Claude Code and Codex have the same failure classes; only the file layout and the trust gate differ. `scripts/audit_hooks.py` walks every Codex hook source and reports each command's exit code and first stderr line — run it first, before guessing.

## Procedure

### 1. Map the exit code before investigating anything

| code | meaning | usual cause |
|---|---|---|
| 126 | found, cannot execute | a Windows `.exe` shipped to Linux, or a missing exec bit |
| 127 | command not found | a bare command name that is not on the PATH the harness launched with |
| 2 | script error | the hook script's own failure, e.g. `set -u` reading an env var the host never exports |
| 1 | hook ran and declined | usually legitimate; read its stderr before treating it as a defect |

The harness reports only the number, so a wrong map sends you hunting in the wrong place entirely.

### 2. Reproduce under the environment the harness actually launches hooks in

This is the step that finds the bug. A desktop-app or GUI launch carries a minimal `PATH` (`/usr/bin:/bin:/usr/local/bin`) with no `~/.local/bin`, no `~/.bun/bin`, and none of what a shell rc file adds. A hook that resolves fine in your interactive shell can be a 127 there.

Run the hook's exact command string through a shell with that restrained PATH and read the code:

```sh
PATH=/usr/bin:/bin:/usr/local/bin bash -c "<the hook command>" </dev/null; echo "exit=$?"
```

When a harness gives you no identifier for the failing hook, feed each hook a synthetic event payload and record exit codes — `scripts/audit_hooks.py` does this over every discovered source. Prefer that over bisecting by disabling plugins.

### 3. Fix by cause

- **127 from a bare command.** Make the hook self-sufficient instead of relying on inherited PATH:
  `export PATH="$HOME/.local/bin:$PATH"; exec "$HOME/.local/bin/<tool>" <args>`.
  Keep the PATH export as well as the absolute path — it also covers the tool's own child lookups.
- **126 from a `.exe`.** The plugin ships no Linux runtime and cannot be made to work; `chmod +x` does not help a PE binary. Remove it (`codex plugin remove <plugin>@<marketplace>`) and delete its `[hooks.state."<plugin>@<marketplace>:..."]` blocks from `~/.codex/config.toml`, which otherwise linger and re-reference a path that no longer exists.
- **2 from an unset variable.** Give the hook a default: `VAR="${VAR:-<path>}"`. Confirm the variable is genuinely absent rather than misspelled — harnesses export plugin-root style variables inconsistently, and a hook may assume one that only some harnesses provide.

### 4. Fix the whole set, not the first failure

Hooks from multiple sources all run, and the harness surfaces one failure at a time — fixing the visible one usually reveals the next with a different cause. After any fix, re-run `scripts/audit_hooks.py` and require every command to exit 0 before declaring it done.

## Trust gates re-arm whenever hook text changes

Codex runs only hooks whose current hash matches `[hooks.state."<key>"] trusted_hash` in `~/.codex/config.toml`; anything else is skipped silently while other plugins keep working. The gate re-arms on **any** edit to a hook's command text, not just on plugin upgrades — so the fix you just made is itself skipped on the next launch until approved.

Approve by launching the harness TUI in a pty and answering the startup prompt:

```
Hooks need review
N hooks are new or changed.
› 1. Review hooks
  2. Trust all and continue
  3. Continue without trusting (hooks won't run)
```

Send `\x1b[B\r` (down + Enter) for **Trust all and continue**, then verify the stored hashes:

```sh
python3 -c "import tomllib;c=tomllib.load(open('$HOME/.codex/config.toml','rb'));print(sorted(c.get('hooks',{}).get('state',{})))"
```

Non-interactive runs cannot approve a hook. A batch run that looks clean does not mean an interactive session is clean, and vice versa — check both after touching hook text.

## Where hooks come from

Enumerate all of these before concluding a hook is missing; a single event can be served by several plugins at once.

- **Codex, user**: `~/.codex/hooks.json`, and inline `[hooks]` tables in `~/.codex/config.toml`.
- **Codex, project**: `<repo>/.codex/hooks.json` — loaded only when that project is trusted.
- **Codex, plugin-bundled**: `hooks/hooks.json` or `hooks/codex-hooks.json` inside each plugin's cache directory, declared by the plugin manifest.
- **Claude Code**: `hooks` in `~/.claude/settings.json`, plus each enabled plugin's own `hooks/hooks.json`.

## Plugin-bundled hook files live in a versioned cache

A patch to a bundled hook file sits under a per-version cache directory, so the next plugin update drops it and the hook breaks the same way again. Prefer fixing the hook's own inputs (export the missing variable in the command, harden the PATH) over editing files elsewhere, and re-check after any plugin update.

## Verify, do not assume

A hook exiting 0 does not mean it did its job — many hooks are designed to fail soft and return success. Confirm the side effect the hook exists for (a row written, a record created, a file touched) rather than trusting the exit code alone.
