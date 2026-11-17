---
name: parsec-key
description: Show or set the parsec API key used for savings reporting
---
<!-- parsec-managed-skill: written by `parsec setup codex`; removed by `parsec disable codex`. -->

Manage the parsec dashboard key.

- No value given: run `~/.parsec/bin/parsec key show || parsec key show`.
- Asked to clear: run `~/.parsec/bin/parsec key clear || parsec key clear`.
- Given a value starting with `psc_`: run `~/.parsec/bin/parsec key set <value> || parsec key set <value>`.

Show the command output. Never echo a full key back to the user — `key show` masks it; keep it masked.
