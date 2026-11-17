#!/usr/bin/env bash
# Repeatable per-turn measurement for an agent CLI: wall + user/sys CPU + RSS.
#
#   ./measure_turn.sh 2 pi -p "reply with exactly: OK" --no-session
#   ./measure_turn.sh 2 pi -p "reply with exactly: OK" --no-session -ne -ns --no-mcp
#
# Compare user= between the real config and the all-off floor. Wall swings with
# provider latency and is not evidence on its own.
set -uo pipefail
runs="${1:?usage: measure_turn.sh <runs> <cmd...>}"
shift
for i in $(seq 1 "$runs"); do
  # -k: agents that ignore SIGTERM would hang plain timeout forever
  /usr/bin/time -f "run$i wall=%e user=%U sys=%S cpu=%P maxrss=%MkB" \
    timeout -k 5 400 "$@" >/dev/null
done 2>&1 | grep 'run'
