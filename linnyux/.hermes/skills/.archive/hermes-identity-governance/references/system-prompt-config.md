# Editing the Hermes system prompt (config.yaml agent.system_prompt)

How to rewrite a Hermes install's per-request system prompt and prove it landed. Companion to the "Where the TUI system prompt actually lives" section in SKILL.md.

## Injection chain (verify against the running version, paths move)

```
config.yaml  agent.system_prompt
  -> hermes_cli.personality.resolve_ephemeral_system_prompt_from_config(cfg)
  -> agent.ephemeral_system_prompt
  -> appended to the assembled system prompt at request time
```

`agent.ephemeral_system_prompt` is appended in `agent/chat_completion_helpers.py` (searchable by name), and the TUI sets it from config in `tui_gateway/methods_slash.py`. It is deliberately NOT part of `agent.system_prompt.build_system_prompt()` — that builder covers identity/guidance/skills/memory/profile tiers only.

Confirm the chain on the target host rather than trusting this note:

```bash
cd ~/.hermes/hermes-agent
grep -rn "ephemeral_system_prompt" --include="*.py" . | grep -iE "config|resolve"
```

## Locate the config actually in use

`~/.hermes` may be a symlink. Resolve it before editing, and confirm which home the live process uses.

```bash
ls -ld ~/.hermes
stat -c "%d:%i %n" ~/.hermes/config.yaml "$(readlink -f ~/.hermes)/config.yaml"   # same inode = same file
tr '\0' '\n' < /proc/<pid>/environ | grep -iE "HOME=|HERMES"                            # live TUI/gateway
```

Find the live processes with `ps aux | grep -iE "hermes|tui"`. A gateway and one or more TSIs can be running at once against the same config.

## Splice the value — do NOT round-trip the whole file

Never `yaml.safe_load` → mutate → `yaml.safe_dump` a live `config.yaml`. It rewrites every line, drops comments, and reorders keys across a multi-KB file, turning a one-key change into an unreviewable diff. Replace only the block:

```python
# patch_prompt.py — replace agent.system_prompt with a literal block scalar
CFG = "/path/to/.hermes/config.yaml"
NEW = open("/tmp/new_system_prompt.txt").read().rstrip("\n")

lines = open(CFG).read().split("\n")
i = next(n for n, l in enumerate(lines) if l.startswith("  system_prompt:"))
j = i + 1
while j < len(lines):                        # block runs while blank or indented >= 4
    l = lines[j]
    if l.strip() == "" or l.startswith("    "):
        j += 1
    else:
        break
block = ["  system_prompt: |"] + ["    " + l for l in NEW.split("\n")]
open(CFG, "w").write("\n".join(lines[:i] + block + lines[j:]))

import yaml
print(len(yaml.safe_load(open(CFG))["agent"]["system_prompt"]))   # must equal len(NEW) + 1
```

A `|` literal block is used instead of re-quoting a folded/single-quoted scalar: no escaping, no line-continuation rules, and plain prose goes in as-is. Always back the file up first (`cp config.yaml config.yaml.bak-prompt-$(date +%Y%m%d-%H%M%S)`).

Prove the diff is bounded to the intended key:

```bash
diff config.yaml.bak-prompt-* config.yaml | grep "^[<>]" | grep -oE "^[<>] *[a-z_]+:" | sort -u
# expect: system_prompt only
```

## Verify end-to-end (the part that actually proves it)

`build_system_prompt()` will report `False` for the text. That is the expected false negative — use the resolver:

```python
# verify_prompt.py — run with the hermes-agent venv python
from hermes_cli.config import load_config, resolve_ephemeral_system_prompt_from_config
ep = resolve_ephemeral_system_prompt_from_config(load_config())
print(len(ep))
print("new:", "<a distinctive phrase from the new prompt>" in ep)
print("old:", "<a distinctive phrase from the old prompt>" in ep)   # want False
```

```bash
runuser -u <user> -- bash -lc "cd /tmp && /path/to/.hermes/hermes-agent/venv/bin/python3 /tmp/verify_prompt.py"
```

Run it as the owning user with a login shell. A bare `runuser -u <user> -- ...` can leave `~` resolving to the caller's home and produce a spurious permission-denied on `<caller-home>/.hermes.md`; `bash -lc` fixes it. If `hermes_cli` is not importable, you are in the wrong interpreter — use the venv python from the install directory, not the system python.

Sizing sanity check, and what is actually eating the window:

```bash
hermes prompt-size            # tier + toolset + skills byte breakdown
hermes prompt-size --json     # same as JSON (sizes only, no prompt text)
```

Note `prompt-size` reports sizes for `system_prompt` (`{chars, bytes}`), never the text. It cannot be used to grep for your prompt string — that is what the resolver check above is for.

## Hot-reload a running TUI

Do not kill the user's session. `/prompt` in the TUI calls `_mirror_prompt`, which re-reads `config.yaml` `agent.system_prompt`, assigns `agent.ephemeral_system_prompt`, and clears `agent._cached_system_prompt`. Config is also read fresh on the next launch; a running gateway re-resolves per run.

## Threat-scanner check

`_scan_for_threats(content, scope="context")` runs on context files (`SOUL.md`, `AGENTS.md`, `.cursorrules`) at load and replaces the whole file on a match. `agent.system_prompt` from `config.yaml` is a different path — but run the probe on the text anyway before installing it anywhere, since it is free and catching a trigger-shaped phrase early beats debugging a silent no-op:

```bash
cd ~/.hermes/hermes-agent
python3 -c "from tools.threat_patterns import scan_for_threats; import sys; print(scan_for_threats(open(sys.argv[1]).read(), scope='context'))" /tmp/new_system_prompt.txt
# must print []
```

Trigger shapes and the work-arounds live in the SKILL.md scanner pitfall.

## Pitfalls

- **Reporting success from a `build_system_prompt()` probe.** It excludes `ephemeral_system_prompt`; a `False` there is not evidence of a failed install. Verify with the resolver.
- **`yaml.safe_dump` on a live config.** Rewrites the whole file, drops comments, reorders keys. Splice the block.
- **Editing `SOUL.md` when the user asked for the system prompt** (or vice versa). Different injection points; check which one the running agent actually reads.
- **Assuming a non-symlinked `~/.hermes`.** Check the inode of both paths and the live process `environ` before rewriting a file that is aliased to another home.
- **Killing a live TUI to reload.** `/prompt` exists for exactly this.
- **`runuser` without a login shell.** Produces bizarre permission errors against the caller's home.
