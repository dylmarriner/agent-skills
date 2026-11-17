---
name: harness-plugin-wiring
description: "Wire or unwire a skill/plugin pack into Claude Code, Codex, or Hermes, including bulk-copying a repo's whole skill tree into a profile."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [plugins, marketplaces, skills, claude-code, codex, hermes, wiring]
    related_skills: [claude-code-troubleshooting, antigravity-cli, pi-extension-management]
---

# Harness Plugin & Skill Wiring

Connect a repo of skills/commands/agents/hooks (a "pack") to one or more agent
harnesses so each one actually LOADS it. The deliverable is a verified
per-harness status, not a list of install commands.

## When to Use

- The user points at repos of skills/commands/agents and asks to connect,
  install, or wire them to Claude Code / Codex / Hermes ("make these available
  in X"), or asks to install a repo's ENTIRE skill set into this profile
  ("save all these skills" as skills I can use) — that is the copy route in
  Procedure step 3, Route B.
- Registering a local pack path — no GitHub publish, no per-skill symlinks.
- A pack claims to be installed but the harness does not act as if it knows the
  skills, or you need to audit what a harness actually loads and what it costs
  per session.
- The user asks to REMOVE, silence, or stop a pack ("get rid of the X plugin",
  "turn off the thing that runs on every turn") -- same class, opposite
  direction: Procedure step 4 plus the residue check, no blind file deletion.

## Non-negotiables

1. **Register the source; do not copy it.** Use each harness's native source
   mechanism (marketplaces for Claude Code/Codex, `skills.external_dirs` for
   Hermes). Copying drifts on every upstream update, and N-symlink farms (one
   symlink per skill) are the failure shape — one source registration replaces
   all of them.
2. **A local directory is a first-class marketplace** in both Claude Code and
   Codex. No GitHub push, no clone is needed to wire a repo that already sits
   on disk.
3. **Install success is not load success.** Re-read the harness's *status*
   output before reporting anything as connected.
4. **Measure the always-on token cost before you leave a pack enabled**, and
   headline it with the one-line disable command. A few-hundred-skill pack can
   add tens of thousands of tokens to every session.
5. **Never route around a config write guard.** Hermes refuses agent writes to
   `config.yaml`; use the CLI (`hermes config set`). Back the file up first.
6. **Report every file you add or modify inside the user's repos** (new
   untracked manifests, edited `plugin.json`) — these show up as uncommitted
   changes in their working tree and must not be a surprise.
7. **Removal is not done when the uninstall command exits 0.** Claude Code
   drops the registration only; the marketplace clone, cache snapshot,
   `statusLine`, and marketplace entry survive. Run
   `scripts/plugin-residue-check.sh` and do not report "removed" until it
   prints clean.
8. **Scope the removal to the harness the user named, then report the others.**
   The same pack is usually installed in Claude Code AND Codex; deleting from
   one is not permission to touch the other. Name what is still installed and
   offer.
9. **Enumerate every copy of a shared name before deleting any of it.** One
   pack name routinely exists as a marketplace install, a skills-dir copy, a
   fork clone on disk, and stale records from an older install. List all of
   them (`claude plugin list`, `claude plugin marketplace list`, `codex plugin
   list`, `codex plugin marketplace list`, plus a filename sweep; `git -C <dir>
   remote -v` tells a fork of the same project from an unrelated one) and state
   which copy you are removing AND which you are keeping in the same breath.
   Never act on "the X plugin" while two X's are on the box.
10. **Back up every config file you are about to edit, and undo a wrong pick by
    copying the backup back.** `cp <file> <file>.bak-<tag>` for `settings.json`,
    `installed_plugins.json`, `~/.codex/config.toml`, `~/.codex/hooks.json`
    BEFORE the first edit; restoring the whole file beats re-merging by hand,
    then re-run install/add to re-materialize what a backup cannot hold (see
    `references/plugin-removal-and-restore.md`). A wrong target is then one `cp`
    from undone instead of an archaeology exercise.

## Procedure

### 0. Read the source repo's shape first

```bash
ls -a <repo>                      # .claude-plugin/ ? .agents/plugins/ ? .codex-plugin/ ? skills/ ? commands/ ? agents/ ?
find <repo> -name SKILL.md -not -path '*/.git/*' | wc -l
cat <repo>/.claude-plugin/marketplace.json <repo>/.claude-plugin/plugin.json 2>/dev/null
```

Three shapes matter: ships a **marketplace manifest** (installable as-is),
ships only a **plugin manifest** (needs a marketplace wrapper), or is a bare
**skills directory** (no plugin metadata — Hermes/Codex skill-dir route).

Before adding a new copy of anything, check the machine-wide hub
`~/.agents/skills`: Codex reads it natively as a skill root and Claude Code
symlinks skill dirs out of it. A pack that belongs there should go there and be
consumed by both, rather than being registered twice.

### 1. Claude Code

```bash
claude plugin marketplace add <abs-path-or-repo>
claude plugin install <plugin>@<marketplace> -s user -y
claude plugin list                                   # STATUS, not the install line
claude plugin details <plugin>@<marketplace>         # component inventory + projected token cost
claude plugin validate <plugin-dir>                  # manifest/frontmatter validation, pre-install
```

`-y` is required for a non-TTY install. Scope is `user|project|local`; use
`user` unless the user keeps per-project packs.

### 2. Codex CLI

```bash
codex plugin marketplace add <abs-path-or-repo>
codex plugin add <plugin>@<marketplace>
codex plugin list                 # installed, enabled + resolved source
codex plugin marketplace list     # configured roots
codex debug prompt-input "hi" > /tmp/pi.json   # what the model actually sees
```

`codex debug prompt-input` is the only honest verification: parse the JSON,
find the `<skills_instructions>` text block, read its **skill roots table**
(`r0`…`rN` = directories) and the enumerated skill list. A new `rN` pointing at
the pack's `skills/` dir means it is wired.

### 3. Hermes

```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.pre-wiring-$(date +%Y%m%d-%H%M%S)
hermes config get skills.external_dirs                    # read current value FIRST
hermes config set skills.external_dirs '["existing-entry", "/abs/path/to/pack/skills"]'
hermes config get skills.external_dirs                    # confirm the merge kept old entries
```

`set` takes a list value as JSON/YAML text and overwrites the whole key, so
re-send every existing entry. Then verify resolution against the pack path (see
Verification), not just the config dump.

**Route B — bulk-copy an official source tree into the profile.** For "install
all the skills in <repo>/<dir>" (e.g. the Hermes repo's own `optional-skills/`
tree, which the profile is *supposed* to hold copies of), `external_dirs` is the
wrong tool — the destination is the profile's own
`~/.hermes/skills/<category>/<name>/`. Do not copy out of a working checkout,
and do not hand-install one by one:

```bash
git -C ~/.hermes/hermes-agent remote -v                    # find the clone; it is routinely stale
git -C ~/.hermes/hermes-agent fetch origin main -q         # never install from its working tree
rm -rf /tmp/optskills && mkdir -p /tmp/optskills
git -C ~/.hermes/hermes-agent archive origin/main optional-skills | tar -x -C /tmp/optskills
scripts/skill-tree-sync.py /tmp/optskills/optional-skills          # dry run: missing / identical / differing
scripts/skill-tree-sync.py /tmp/optskills/optional-skills --apply  # copy ONLY the missing
```

`git archive` materializes the subtree as of `origin/main` without touching the
live install's checkout. Skill dirs are `<root>/<category>/<name>/SKILL.md`, but
nesting is NOT uniform — some skills sit directly under the root, others at
`<category>/<subgroup>/<name>` — so walk recursively and count files at every
level. The source-relative path maps 1:1 onto
`~/.hermes/skills/<same relative path>`.

### 4. Unwire / remove a pack

```bash
claude plugin disable <plugin>@<marketplace>              # stops its hooks + always-on cost, install kept (reversible)
claude plugin uninstall <plugin>@<marketplace> --json     # --keep-data keeps plugins/data/<id>/
scripts/plugin-residue-check.sh <plugin>@<marketplace>    # the actual verdict
```

`disable` first when the user only wants the noise gone — it is reversible;
`uninstall` is not.

`uninstall` clears only the registration: the `enabledPlugins` entry and the
`installed_plugins.json` record. It LEAVES, and you clean by hand:

- `statusLine` in `settings.json` (a plugin installs its own there; the now-dead
  script path breaks the status line on every render) and any other
  `settings.json` key the plugin wrote,
- `extraKnownMarketplaces.<marketplace>`,
- the marketplace clone `~/.claude/plugins/marketplaces/<marketplace>/`,
- the install snapshot `~/.claude/plugins/cache/<marketplace>/` (tens of MB),
- the plugin's runtime state dir `~/.claude/<plugin>/`.

Back up `settings.json` and `installed_plugins.json` to timestamped `.bak`s
before editing, keep `settings.json` valid JSON, and end on `claude plugin
list` (zero references) plus the residue check — never on the uninstall line.

**A plugin's hooks are not in `settings.json`.** Claude Code merges every
enabled plugin's own `hooks/hooks.json` at load — `Stop` (end of turn),
`UserPromptSubmit`, `PreToolUse`, `PostToolUse` all come from there — so a
`grep -i stop ~/.claude/settings.json` that returns nothing has proved nothing.
Identify the owner via `claude plugin list` / `enabledPlugins`, and
`grep -rl '"Stop"' ~/.claude/plugins/marketplaces/*/*/hooks/hooks.json`, then
disable or uninstall that plugin: there is nothing to delete from
`settings.json`.

**Codex holds its own install of the same pack** (`codex plugin list`;
`[plugins."<id>"]` + `[marketplaces.<mkt>]` and `[hooks.state]` in
`~/.codex/config.toml`). Removing it from Claude Code does not remove it there.
On Codex, `codex plugin remove <plugin>@<marketplace>` clears only the
`[plugins."<id>"]` entry and empties the cache dir; it LEAVES
`[marketplaces.<mkt>]`, the `[hooks.state."<id>:…"]` rows, any config key the
plugin wrote for itself, `~/.codex/<plugin>/` runtime data, and the hand-written
user-level `~/.codex/hooks.json`. That last file is the one that matters for an
"it runs on every turn" complaint: installers write their own `Stop`,
`SessionStart`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop` entries
there, pointing into the plugin's cache path, and no plugin uninstall touches
it. `grep -n '<pack>' ~/.codex/hooks.json` and strip only those entries, keeping
unrelated hooks (a Bash `PreToolUse` from another tool) intact. End on
`codex plugin list` + `codex plugin marketplace list`, not on the remove line.

**A pack that ships a daemon needs the daemon handled too.**
`systemctl --user disable --now <unit>`; delete
`~/.config/systemd/user/<unit>.service` and its `default.target.wants` symlink;
`systemctl --user daemon-reload`; `pkill -f '<daemon-script>'`. A running daemon
keeps serving from files you already deleted until it is killed, and a unit left
behind after its data dir is gone restart-loops.

### 5. Report

One row per consumer with the exact status string, the always-on token cost for
packs that pay it, the files you touched, and the rollback/disable command.

## Manifest requirements

| Harness | Reads | Notes |
|---|---|---|
| Claude Code | `.claude-plugin/marketplace.json` + the plugin's `.claude-plugin/plugin.json` | `commands`/`skills` must be ARRAYS; omit `agents`; never declare the root `hooks/hooks.json` |
| Codex | same `.claude-plugin/marketplace.json` for a local-dir marketplace; `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` for full native metadata (`"skills": "./skills/"`) | auto-discovers a plugin's root `skills/`/`commands/`/`agents/` dirs |
| Hermes | `skills.external_dirs` (absolute or `~` paths) | scans recursively for `SKILL.md`; read-only from the agent's side |

Starter files: `templates/marketplace.json` (one manifest both Claude Code and
Codex accept for a local repo) and `templates/codex-plugin.json`. Schemas and
per-harness command detail: `references/harness-matrix.md`.

## Pitfalls

- **Claude Code: a plugin can install cleanly and still report `✘ failed to
  load`.** Always read `claude plugin list` status text. The two causes seen:
  an invalid manifest key and a duplicate hooks file.
- **`agents` as a string (or array) in a Claude plugin manifest is rejected**
  (`agents: Invalid input` / `agents.0: Invalid input`). Omit the key — a root
  `agents/` dir is auto-discovered — rather than guessing at its shape.
- **Declaring `"hooks": "./hooks/hooks.json"` when that is the plugin's
  standard root hooks file is a hard load failure** (`Duplicate hooks file
  detected`). The manifest's `hooks` field is for ADDITIONAL hook files only.
- **`commands`/`skills` as bare strings** fail the same validation as `agents`;
  use arrays.
- **A repo that ships only a plugin manifest is invisible to both
  `claude plugin` and `codex plugin`.** Author a ~15-line marketplace wrapper
  pointing at the plugin dir instead of symlinking the skills one by one.
- **Claude Code snapshots a local plugin into `~/.claude/plugins/cache/` on
  install**, so editing the source repo afterwards changes nothing — uninstall +
  reinstall (or `update`) to pick the change up.
- **Codex snapshots the plugin too** (`Installed plugin root:
  ~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`), so a manifest you fix
  *after* installing is not the one Codex runs — `codex plugin remove
  <plugin>@<marketplace>` then `add` again, and confirm with `codex plugin list` +
  `debug prompt-input` instead of assuming the edit landed.
- **Codex caps its inline enumerated skill list** at tens of skills; a
  registered skill root with 0 enumerated skills is normal, not a failed wiring.
  Judge by the roots table.
- **Duplicate skill names**: Hermes resolves the local `~/.hermes/skills` before
  `external_dirs`, so a name that exists in both is SHADOWED — check the resolved
  path before telling the user a skill is newly available.
- **Never blind-overwrite a skill copy that already exists with different
  bytes, and never report "all updated" from a copy loop.** Staleness direction
  varies per skill: the published copy can be NEWER than repo `main` (extra
  guidance sections, extra `references/`) while a sibling in the same run is
  older. Classify missing / identical / differing, copy only the missing, and
  report the differing list for the user to decide. Force-sync one deliberately
  with `hermes skills repair-official <name> --restore -y`, which backs the
  current copy up first.
- **Verify a skill install on the filesystem, never by scraping `hermes skills
  list`.** That table has no `--json` and truncates its name column (~15 chars),
  so a grep for a long skill name returns a FALSE NEGATIVE and reads as a failed
  install. Use the set difference of `SKILL.md` relative paths between the
  source tree and `~/.hermes/skills` (expected: zero missing). `hermes skills
  inspect <name>` resolves against the remote/official catalog, so it does not
  prove the local copy was picked up either. Freshly copied skills show
  `Source: local / Trust: local` while catalog-known ones show `official`; both
  load enabled, and the prompt snapshot regenerates at the next session start,
  so there is no re-index step to run.
- **An installed-but-unconfigured skill is not a working skill.** Optional
  skills that need API keys or a CLI present land enabled and only fail at
  runtime; name the affected ones in the report and point at
  `hermes skills config`.
- **Verifying Hermes skill roots needs the Hermes venv interpreter**
  (`$HERMES_HOME/hermes-agent/venv/bin/python` with `sys.path` including the
  `hermes-agent` dir and `HERMES_HOME` exported). A bare system `python3` fails
  to import the config layer (missing third-party deps).
- **Do not leave a huge pack silently enabled.** Claude Code reports projected
  always-on cost; re-report it every time and hand over
  `claude plugin disable <plugin>@<marketplace>`.
- **`claude plugin uninstall` defaults to `-s user`.** A plugin enabled at
  project or local scope keeps loading its hooks and skills after a user-scope
  uninstall — read the plugin's `Scope:` in `claude plugin list` and pass
  `-s project` / `-s local` when the complaint is per-project.
- **`--prune` needs `-y` when stdin or stdout is not a TTY, and cannot be
  combined with `--json`.** `--json` alone is the non-interactive form and
  prints one quotable line (`{"outcome":"ok",...}`) instead of prose worth
  re-reading.
- **A removal command exiting 0 means one record is gone, nothing more.** Count
  the pack's references in every config file before and after (`grep -c <pack>
  <file>`) and treat a non-zero count as unfinished work — the leftovers are
  exactly the hooks and entries the user wanted stopped.
- **When the user says "keep that one" mid-removal, restore first and re-scope
  second.** Copy the `.bak`s back, re-install to re-materialize the caches, then
  confirm the target — do not keep deleting forward on the old interpretation,
  and do not leave the half-removed state in place while asking.
- **A plugin's generated runtime data dir is not restorable from a config
  backup.** `~/.claude/plugins/data/<plugin>-<marketplace>/` and
  `~/.codex/<plugin>/` hold generated scripts, dashboards and state files; only
  the plugin's own install/doctor command regenerates them, and it needs the
  directory to exist first or it silently provisions to a legacy fallback path.

## Verification

Per harness, the status line that proves wiring (run all, quote the output):

```bash
claude plugin list | grep -A3 '❯ <plugin>@'                     # ✔ enabled
claude plugin details <plugin>@<marketplace> | grep 'Always-on:'
codex plugin list | grep '<plugin>@'
codex plugin marketplace list | grep '<marketplace>'
hermes config get skills.external_dirs                          # entry present
scripts/plugin-residue-check.sh <plugin>@<marketplace>           # 'clean:' after a removal
```

Hermes resolution check (path must be inside the pack, not `~/.hermes/skills`):

```bash
PY="$HERMES_HOME/hermes-agent/venv/bin/python"
cd "$HERMES_HOME/hermes-agent" && HERMES_HOME="$HERMES_HOME" "$PY" -c "
import sys; sys.path.insert(0, '$HERMES_HOME/hermes-agent')
from agent.skill_utils import get_all_skills_dirs
print([str(d) for d in get_all_skills_dirs()])
from tools.skill_manager_tool import _find_skill
print(_find_skill('<skill-name>'))"
```

Codex enumeration check (count skills per root; confirm the pack's root exists):

```bash
python3 - <<'PY'
import json, re, collections
s = "\n".join(c["text"] for m in json.load(open('/tmp/pi.json'))
              for c in m.get("content", []) if c.get("type") == "input_text")
blk = re.search(r"<skills_instructions>(.*?)</skills_instructions>", s, re.S).group(1)
roots = dict(re.findall(r"`(r\d+)` = `([^`]+)`", blk))
print(roots)
print(collections.Counter(re.findall(r"\(file: (r\d+)/", blk)))
PY
```

## Support files

- `references/harness-matrix.md` — per-harness command sets, manifest schemas,
  output interpretation, and how to add a fourth harness.
- `references/plugin-removal-and-restore.md` — what each uninstall command
  clears vs leaves, the Codex `hooks.json` that outlives the plugin, generated
  data dirs, and the step-by-step restore of a wrongly removed pack.
- `templates/marketplace.json` — copy-and-modify local marketplace manifest.
- `templates/codex-plugin.json` — Codex-native plugin manifest.
- `scripts/plugin-residue-check.sh` — re-runnable post-removal verdict: every
  surviving artefact of an uninstalled pack (clones, cache, data dir, JSON
  references, broken `settings.json`), exit code = residue count.
- `scripts/skill-tree-sync.py` — re-runnable verdict for a bulk skill-tree
  install into `~/.hermes/skills`: per-skill missing / identical / differing,
  frontmatter validation, `--apply` to copy the missing, `--force-differing` to
  replace with a timestamped backup. `--self-test` proves the classifier.
