#!/usr/bin/env bash
# Residue check after removing/unwiring a Claude Code pack.
# Usage: plugin-residue-check.sh <plugin>@<marketplace> [claude-root]
# Exit 0 = clean; non-zero = count of surviving artefacts (each printed).
#
# Run this AFTER `claude plugin uninstall <id>`: the uninstaller's exit 0 only
# means the registration was dropped -- marketplace clone, cache snapshot,
# statusLine and marketplace entry survive it.
set -uo pipefail

id="${1:?usage: plugin-residue-check.sh <plugin>@<marketplace> [claude-root]}"
plugin="${id%@*}"
mkt="${id#*@}"
root="${2:-$HOME/.claude}"
hits=0

residue() { printf 'RESIDUE: %s\n' "$1"; hits=$((hits + 1)); }

# Directories the uninstaller does not touch: marketplace clone, install
# snapshot, --keep-data dir, plugin runtime state dir (e.g. ~/.claude/<plugin>).
for p in "plugins/marketplaces/$mkt" "plugins/cache/$mkt" "plugins/data/$id" "$plugin"; do
  [ -e "$root/$p" ] && residue "$root/$p"
done

for f in "$root/settings.json" "$root/plugins/installed_plugins.json"; do
  [ -f "$f" ] || continue
  if grep -q -- "$mkt\|$plugin" "$f"; then
    residue "$f: $(grep -n -- "$mkt\|$plugin" "$f" | head -5 | tr '\n' ' ')"
  fi
done

if command -v python3 >/dev/null 2>&1 && [ -f "$root/settings.json" ]; then
  python3 -c "import json;json.load(open('$root/settings.json'))" \
    || residue "$root/settings.json (invalid JSON -- hand edit broke it)"
fi

[ "$hits" -eq 0 ] && echo "clean: no $id residue under $root"
exit "$hits"
