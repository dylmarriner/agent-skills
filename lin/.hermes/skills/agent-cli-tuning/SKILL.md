---
name: agent-cli-tuning
description: Speed up or fix a lagging local agent CLI (pi, openclaude).
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [coding-agents, performance, profiling, context-window]
    related_skills: [coding-agent, litellm-coding-agent-setup]
---

# Agent CLI tuning (perf + limits)

## When to Use

- "pi / openclaude / codex lags", hangs for minutes on a one-line prompt, or
  burns CPU after the answer is already printed.
- A configured limit is ignored or breaks at an extreme value: a billion-token
  context window that still compacts, a caps that only make sense at 200k.
- A CLI needs reconfiguring so it starts and turns fast without losing tools.

Not for wiring a CLI to a proxy (see `litellm-coding-agent-setup`) or for
spawning agents to do work (see `coding-agent`).

For when a locally installed agent CLI "lags", sits for minutes on a one-token
prompt, or does not honour a configured context/limit. Applies to `pi`,
`openclaude`, `codex`, `opencode`, `kilo` and friends — they all have the same
shape: a settings file listing plugins/extensions plus a per-turn hook pipeline.

## Rules (always on)

1. **Measure CPU, not wall clock.** A one-line prompt still pays a model
   round-trip, so wall time swings 5s↔45s on an unchanged config. `user+sys` CPU
   from `/usr/bin/time -f` is the number that moves when *the CLI* is the problem.
2. **Take two samples per config.** A single lucky sample has already produced a
   wrong conclusion (12s hiding a 40s steady state).
3. **Find the floor first.** Run the same prompt with every plugin/extension
   disabled. If the floor is 4-5s and the real config is 40s+, the model is
   innocent and a plugin is burning CPU — bisect, do not guess.
4. **Bisect by config, not by reading code.** Back up the settings file, drop
   half the entries, measure, repeat. Two or three halvings land on the culprit
   faster than reading plugin source.
5. **Never `pkill -f <pattern>` from a tool call.** The pattern matches the
   invoking `bash -c` command line, so it kills your own shell mid-run. Use
   `pgrep -f`, drop your own PID, kill by PID.
6. **Always `timeout -k 5 N`.** Agents that ignore SIGTERM leave plain
   `timeout N` waiting forever and eat the whole tool-call budget.
7. **Fix config, keep capability.** Keep one plugin per job (one memory, one
   tracer, one context-rewriter), not zero. State the rollback in the report.
8. **When a feature "doesn't work" at an extreme value, hunt the constant that
   encodes the old assumption** (a 200k-era default) instead of widening the
   value the user already set. See `references/context-window-plumbing.md`.
9. **Trace hook failures to the registered hook before changing settings.**
   Preserve the exact event, command, plugin identity, and exit status; a broad
   CLI health check does not prove that hook handlers executed successfully.

## Procedure

```bash
# 1. floor: everything off
/usr/bin/time -f "floor wall=%e user=%U sys=%S maxrss=%MkB" \
  timeout -k 5 200 pi -p "reply with exactly: OK" --no-session -ne -ns --no-mcp

# 2. real config, same prompt, twice
/usr/bin/time -f "full wall=%e user=%U sys=%S maxrss=%MkB" \
  timeout -k 5 400 pi -p "reply with exactly: OK" --no-session
```

- Floor fast, real config slow → plugin stack. Bisect: `cp settings.json
  settings.json.bak-speedup`, remove half the plugin entries with a short Python
  edit, re-measure, repeat until cheap. Keep the `.bak-speedup` as the rollback.
- Both slow → provider/network. Check the endpoint before touching config.
- Slow *after* the answer is printed → per-turn post-processing hooks (memory
  extraction, vector indexing, tracer flush). Same bisection applies.

Profile without restarting anything (node-based CLIs accept it in NODE_OPTIONS):

```bash
NODE_OPTIONS="--cpu-prof --cpu-prof-dir=/tmp/prof --cpu-prof-interval=500" \
  timeout -k 5 250 pi -p "reply with exactly: OK" --no-session ...
# aggregate hitCount per node_modules/<pkg> across the .cpuprofile files
```

Reading the profile: module-loading frames (ESM loader, `jiti`, `vm`,
`bootstrap/realm`) = startup import cost; one plugin dominating = per-turn work;
40%+ "native" with no JS parent = GC/JSON, i.e. something allocates enormous
structures (huge vector index, giant prompt rewrites).

## Hook failure triage

1. Read the active hook registry and current plugin-enable config; map each
   reported failure to its event, command, and plugin. Keep the original config
   as a rollback before changing registrations.
2. Re-run each candidate command individually with a representative JSON event
   payload and the same working directory and plugin-root environment Codex
   supplies. Record command, event, stdout/stderr, timeout, and exact exit code.
   Do not trust an aggregate harness that ends in `;`, `|| :`, or another
   success-returning command: it can mask the hook's failing status.
3. For exit 126, check the resolved executable, execute bit, shebang
   interpreter, and parent-directory traversal permissions. For exit 1, capture
   stderr and follow the failing branch to its missing input or failed
   prerequisite; do not infer the cause from the number alone.
4. Change only the responsible layer. Prefer repairing a path, permission, or
   required environment setting when the capability is wanted. Disable a
   plugin only when the user authorizes removing that capability or its
   prerequisite cannot be provided; preserve a backup and state what capability
   is lost.
5. Re-test the exact event after the edit, then start a fresh CLI session and
   verify the runtime-loaded hook list: config edits do not update hooks already
   registered in a running session.

## Verify before reporting

- Tool round-trip, not just text: `pi -p "Use the bash tool to run exactly: echo PIOK"`
  must print `PIOK`.
- Confirm the plugin list really shrank: `pi list` (entries marked `(filtered)`
  are still loaded).
- Kill orphaned daemons the removed plugins started — they keep the port and
  the RAM after the package is gone.

## Reporting shape this user wants

Before/after table of `wall | user CPU | maxRSS`, then the flat list of what was
cut grouped by job (one line each), the exact one-line rollback, and one
"next lever" line. No prose tour of what each plugin does.

## References

- `references/pi-extension-stack.md` — pi layout, flags, and what the plugin
  piles cost on this box.
- `references/context-window-plumbing.md` — context-size resolution order,
  message-count caps, and how to verify a claimed window offline.
- `scripts/fake_openai_stub.py` — stdlib OpenAI-compatible stub server for
  end-to-end checks with no credentials.
- `scripts/measure_turn.sh` — repeatable N-run wall/CPU measurement for any CLI.
