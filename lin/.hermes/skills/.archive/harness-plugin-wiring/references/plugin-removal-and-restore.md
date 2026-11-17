# Plugin removal — residue inventory and restore

Depth for unwiring a pack and for undoing a removal that hit the wrong copy.
The verdict procedure is `scripts/plugin-residue-check.sh`; this file says what
is left behind per harness and how to rebuild it.

## What each uninstall command actually clears

| Command | Clears | Leaves |
|---|---|---|
| `claude plugin uninstall <p>@<m> [--keep-data]` | `enabledPlugins` entry, `installed_plugins.json` record | `statusLine` and other plugin-written `settings.json` keys, `extraKnownMarketplaces.<m>`, `plugins/marketplaces/<m>/`, `plugins/cache/<m>/`, `plugins/data/<p>-<m>/`, `~/.claude/<p>/` |
| `codex plugin remove <p>@<m>` | `[plugins."<p>@<m>"]` entry, cache dir contents | `[marketplaces.<m>]` block, `[hooks.state."<p>@<m>:…"]` rows, plugin-written config keys, `~/.codex/<p>/`, `~/.codex/hooks.json` |
| `claude plugin disable <p>@<m>` | nothing (load is suppressed) | everything — this is the reversible option and the right default when the user only wants the noise gone |

Marketplace clones are removed with the harness's own command
(`claude plugin marketplace remove <m>`, `codex plugin marketplace remove <m>`),
not by deleting the directory — the CLI keeps a registry that then disagrees with
the filesystem.

## The hooks file that outlives the plugin

- **Claude Code**: an enabled plugin's hooks come from the plugin's own
  `hooks/hooks.json` merged at load. There is nothing to delete from
  `settings.json`; find the owner with `claude plugin list`, then disable or
  uninstall that plugin.
- **Codex**: installers write a user-level `~/.codex/hooks.json` holding the
  tool's own `Stop` / `SessionStart` / `UserPromptSubmit` / `SubagentStart` /
  `SubagentStop` commands with absolute paths into the plugin's cache. Plugin
  removal never edits it, so the end-of-turn hook keeps firing after a
  "successful" uninstall. Strip those entries and keep unrelated hooks in the
  same file (e.g. another tool's `PreToolUse` matcher) — and keep the file valid
  JSON, since Codex reads it whole.

## Restore a wrongly removed pack

1. Copy the `.bak` files back whole — `settings.json`, `installed_plugins.json`,
   `~/.codex/config.toml`, `~/.codex/hooks.json`. Do not re-merge by hand; the
   backup is the pre-change truth.
2. Re-run the install to re-materialize what a config backup cannot hold:
   `claude plugin install <p>@<m>`, `codex plugin add <p>@<m>` (cache snapshots,
   tens of MB each). A marketplace the CLI registry forgot must be re-added
   first (`claude plugin marketplace add <owner>/<repo>`).
3. Re-provision generated runtime data with the plugin's OWN command — its
   `setup-daemon` / `doctor` / `<feature> --install` entry point — not by copying
   files by hand.
4. Verify against the original numbers: `claude plugin list` / `codex plugin
   list` status row, `grep -c <pack> <each config file>` back to its previous
   count, every path in the unit file existing, and any local endpoint answering
   (`curl -s -o /dev/null -w '%{http_code}' <url>` → 200).

## Generated-data pitfalls

- **The plugin data dir must exist for the plugin to provision into it.**
  Missing, and the installer silently falls back to a legacy path
  (`~/.claude/_backups/<plugin>/`) and rewrites the systemd unit to match.
  `mkdir -p` the plugin data dir first, then provision.
- **A daemon that exits 0 in milliseconds with empty logs is refusing, not
  crashing.** Look in its data dir for a refusal/tombstone marker left by an
  earlier `--uninstall` (e.g. `.daemon-thrash` containing `uninstalled`), delete
  it, restart the unit.
- **A daemon-installed systemd user unit outlives the plugin.** Disable and stop
  it, delete the unit file and its `default.target.wants` symlink, then
  `daemon-reload`; kill the process by pattern too, because a daemon already
  holding deleted files keeps serving until it is signalled.
- **Keep the pre-removal greps.** Recording `grep -c <pack> <file>` for every
  config before editing turns restore verification into a diff instead of a
  guess.
