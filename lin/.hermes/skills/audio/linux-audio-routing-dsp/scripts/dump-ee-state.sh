#!/usr/bin/env bash
# dump-ee-state.sh — inspect Easy Effects runtime state
# Usage: dump-ee-state.sh [device_name_substring]
#
# Reports:
#   - whether EE process is running
#   - which sinks have EE filter nodes attached
#   - autoload entries present
#   - presets present
#   - last segfault evidence in dmesg

set -euo pipefail

DEV="${1:-}"

echo "=== Easy Effects process ==="
if pgrep -f easyeffects >/dev/null; then
    ps -o pid,etime,rss,cmd -C easyeffects 2>/dev/null || pgrep -af easyeffects
else
    echo "  (not running)"
fi

echo
echo "=== EE filter nodes in PipeWire ==="
pw-dump 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
for n in d:
    p = n.get('info', {}).get('props', {})
    klass = p.get('media.class', '')
    if 'Filter' in klass:
        print(f'  {klass:30s} id={n.get(\"id\",\"?\"):>4} {p.get(\"node.name\",\"?\")} ({p.get(\"node.description\",\"\")})')
"
echo "  (none if no output above)"

echo
echo "=== Autoload entries ==="
for d in ~/.config/easyeffects/autoload/output ~/.config/easyeffects/autoload/input; do
    if [[ -d "$d" ]]; then
        echo "  $d:"
        ls -1 "$d" 2>/dev/null | sed 's/^/    /' || echo "    (empty)"
    fi
done

echo
echo "=== Preset files ==="
for d in ~/.config/easyeffects/output/presets ~/.config/easyeffects/input/presets; do
    if [[ -d "$d" ]]; then
        echo "  $d:"
        ls -1 "$d" 2>/dev/null | sed 's/^/    /' || echo "    (empty)"
    fi
done

echo
echo "=== Live output config files ==="
ls -1 ~/.config/easyeffects/output/*.json 2>/dev/null | sed 's/^/  /' || echo "  (none)"

echo
echo "=== gsettings ==="
gsettings list-recursively com.github.wwmm.easyeffects 2>/dev/null | grep -E "process-all|exclude-monitor|use-dark" | sed 's/^/  /'

echo
echo "=== Recent segfaults (last 5 min) ==="
if dmesg --since "5 min ago" 2>/dev/null | grep -iE "easyeff.*segfault" | tail -3; then :; else
    echo "  (no dmesg access or none)"
fi

if [[ -n "$DEV" ]]; then
    echo
    echo "=== Matching sinks for '$DEV' ==="
    pw-dump 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
for n in d:
    p = n.get('info', {}).get('props', {})
    name = p.get('node.name','')
    if '$DEV' in name:
        print(f'  {p.get(\"media.class\",\"?\"):25s} {name}')
        print(f'    description: {p.get(\"node.description\",\"\")}')
        print(f'    profile:     {p.get(\"device.profile.name\",\"\")}')
"
fi
