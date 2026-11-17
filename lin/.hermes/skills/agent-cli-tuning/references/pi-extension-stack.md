# pi extension stack

Everything pi loads per turn lives under `~/.pi/agent`. Four separate piles, each
with its own cost — check all four before blaming the model.

| Path | What it is | Cost profile |
|---|---|---|
| `settings.json` → `packages[]` | npm/git extension packages (`npm:foo`, `git:github.com/u/r`) | heaviest; per-package import + hooks |
| `extensions/` | ~dozens of local `.ts` files, transpiled by `jiti` at every start | ~13% CPU in a profile; fixes nothing else |
| `npm/` | node_modules for all packages (multi-GB) | drives startup import time |
| `mcp.json` | MCP servers; provided by `pi-mcp-adapter`, NOT builtin | each server = subprocess + handshake |

`settings.json` also carries `"extensions": ["-builtin:mcp"]` on this box, so
removing `npm:pi-mcp-adapter` silently kills **all** MCP servers. Re-add it
before reporting done.

## Useful flags

```
-ne            no extensions at all (floor measurement)
-ns            no skills discovery
--no-mcp       no MCP servers connect
-nc            no AGENTS.md / CLAUDE.md
-e <path>      add one extension explicitly
--no-session   do not write a session file (repeatable measurements)
```

## Bisection recipe

```bash
cp ~/.pi/agent/settings.json ~/.pi/agent/settings.json.bak-speedup
python3 - <<'EOF'
import json
p='/home/lin/.pi/agent/settings.json'; d=json.load(open(p))
def src(x): return x if isinstance(x,str) else x['source']
drop={'npm:pi-web-access','npm:pi-lsp'}          # half the suspects
[print(src(x)) for x in d['packages'] if src(x) not in drop]
d['packages']=[x for x in d['packages'] if src(x) not in drop]
json.dump(d,open(p,'w'),indent=2)
EOF
pi list   # confirm what is actually loaded; '(filtered)' = still loaded
```
Then re-add from the backup by source name to test a single package in isolation.

## Groups that compete for the same job (keep one each)

- context/compaction: `billion-context`, `pi-context-engine`, `context-mode`,
  `pi-condense`, `pi-dcp`, `pi-simplify`
- memory/wiki: `pi-hermes-memory`, `pi-knowledge`, `pi-llm-wiki`, `openwiki`
- tracing: `pi-langfuse`, `@langfuse/pi-observability-plugin`, `langsmith-pi-extension`
- routing/prompt rewriting: `jev-agent-tools`, `@riposta/pi-jev`, `pi-prompt-enhancer`

Each group adds a full extra round-trip or an index rewrite per turn. Two or
three per group is a 5-10x per-turn CPU multiplier, not a rounding error.

## Signals seen in practice

- Startup log lines naming an extension twice (`Extension error (...)` /
  `Module did not self-register`) = a native dep built for another Node ABI
  (`NODE_MODULE_VERSION 137` vs `147`). Either `npm rebuild` that package or drop
  it; it will never load, it only costs a failed import per start.
- `Host-provided extension packages must be declared in peerDependencies` warning
  = duplicate runtime modules from a nested `node_modules`; harmless-ish, noisy.
- A plugin daemon left listening on localhost after the package is removed keeps
  its RAM (check with `ss -ltnp`, kill by PID).
