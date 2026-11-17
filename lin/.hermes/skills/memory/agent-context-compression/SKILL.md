---
name: agent-context-compression
description: Deploy and enhance headroom — the context compression layer for AI agents. Covers installation, RTK fusion, agentmemory-aware priority compression, structural delta compression, context budgeting, and Hermes/OpenClaw/Paperclip plugin wiring.
category: memory
emoji: 🗜️
requires:
  bins: [python3, pip3, rust]
trigger: |
  User asks about headroom, context compression, reducing LLM costs,
  token optimization beyond RTK, compressing tool outputs, setting up
  a compression proxy, or enhancing headroom with agentmemory.
  Also triggered by "my context window fills up too fast".
---

# Agent Context Compression — Headroom Integration

Headroom compresses everything your agent reads — tool outputs, logs, RAG
chunks, files, conversation history — before it hits the LLM. Typical savings
are 60–95% with no information loss (reversible compression via CCR).

This skill covers: install, proxy modes, MCP integration, and 6 enhancements
that fuse headroom with agentmemory and RTK.

## Quick Install

```bash
pip install "headroom-ai[all]"          # Python — full install
# or
npm install headroom-ai                  # Node/TypeScript
```

## Modes

| Mode | Command | Use Case |
|------|---------|----------|
| CLI | `headroom compress "text"` | One-off compression |
| Proxy | `headroom proxy --port 8787` | Transparent intercept — zero code changes |
| Agent wrap | `headroom wrap claude` | Wrap a coding agent |
| MCP server | `headroom mcp` | Compress/retrieve/stats as MCP tools |
| Library | `from headroom import compress` | Inline in any Python app |

## Key Compressors (6 algorithms)

- **SmartCrusher** — JSON compression
- **CodeCompressor** — AST-aware code slicing
- **Kompress-base** — ML-based prose compression (HuggingFace model)
- **DiffCompressor** — Git diff compression
- **LogCompressor** — Structured log dedup
- **SearchCompressor** — Code search result compression

## Hermes Plugin

Headroom ships a Hermes plugin at `plugins/hermes/headroom_retrieve/` which
registers the `headroom_retrieve` tool — the agent can fetch original content
behind compression markers instead of re-running commands.

Install: copy `plugins/hermes/headroom_retrieve/` to
`~/.hermes/plugins/headroom_retrieve/`. It auto-registers on next session.

## The 6 CipherCompress Enhancements

These enhancements fuse headroom with agentmemory and RTK. They're implemented
as a Hermes plugin at `~/.hermes/plugins/headroom_retrieve/`:

### 1. RTK+Headroom Fusion Pipeline
Two-stage: RTK pattern filtering (cargo, test, git, json) then headroom ML
compression on the remaining signal. Detects output type automatically.

```
raw output → RTK (pattern filter, 60-90% off) → Headroom (ML, 60% of remainder) → LLM
                                                         Total: ~93-97% off raw
```

### 2. Context-Aware Priority Compression
Queries agentmemory for relevance scores before compressing. High-relevance
content gets light compression (preserve detail), noise gets aggressive
summarization. Uses content hash caching to avoid hammering agentmemory.

### 3. Headroom Learn → Agentmemory
Redirects `headroom learn` output from flat CLAUDE.md to agentmemory's
vector+BM25 store. Lessons become searchable, persistent across machines,
and auto-injected via `AGENTMEMORY_INJECT_CONTEXT=true`.

### 4. Cross-Session Structural Compression
Learns JSON/document schemas across sessions using SQLite. Once a schema
is known, only transmits deltas on repeat data. 99%+ compression on repeated
crawl/API JSON outputs. Hit count tracks schema frequency.

### 5. Context Budget Allocator
Given N content items and a total token budget, allocates proportionally
by agentmemory relevance score. Each item gets budget = (score / total_score)
* total_budget. Low-relevance items are aggressively truncated.

### 6. MCP-Native Compression Router
Single endpoint for compress/retrieve/search/stats through agentmemory.
Applies all 5 stages above in sequence, stores compressed output in
agentmemory with a content-hash marker for retrieval.

## Agentmemory Sync

A cron-ready daemon at `headroom_agentmemory_sync.py` monitors headroom's
SQLite memory store (`~/.headroom/memory.db`) and pushes new entries to
agentmemory's REST API at `POST /agentmemory/remember`.

```bash
# One-shot sync (cron every 5m)
python3 headroom_agentmemory_sync.py --once

# Continuous daemon
python3 headroom_agentmemory_sync.py
```

## Hermes Tool Reference

When the plugin is loaded, 8 tools are available:

| Tool | Function |
|------|----------|
| `rtk_headroom_pipe` | Two-stage RTK→Headroom compress |
| `cipher_compress` | Relevance-aware priority compress |
| `learn_to_am` | Save lessons to agentmemory |
| `structural_compress` | Schema-learning delta compressor |
| `budget_allocate` | Token budget by relevance |
| `mcp_compress` | Full MCP router (compress/retrieve/search/stats) |
| `headroom_retrieve` | Get original from headroom proxy |
| `headroom_agentmemory_bridge` | Push/search agentmemory directly |

## Agent Compatibility

| Agent | Method | Status |
|-------|--------|--------|
| Hermes | Plugin (`~/.hermes/plugins/headroom_retrieve/`) | ✅ |
| OpenClaw | Plugin (`plugins/openclaw/`) — context-engine type | ✅ |
| Paperclip | Adapter plugin (`~/.paperclip/adapter-plugins/ciphercompress/`) | ✅ |
| Claude Code | `headroom wrap claude` | ✅ |
| Codex | `headroom wrap codex` | ✅ |
| Cursor | `headroom wrap cursor` | ✅ |
| Any MCP client | MCP server (`headroom mcp`) | ✅ |
| oh-my-pi (omp) | Extension + `.mcp.json` + Claude plugin | ✅ |

## oh-my-pi Wiring

omp discovers headroom and agentmemory MCP servers through multiple mechanisms:

### 1. Claude Code Plugin Format

Create `~/.claude/plugins/ciphercompress-headroom/plugin.json`:

```json
{
  "name": "ciphercompress-headroom",
  "mcpServers": {
    "agentmemory": {
      "command": "npx",
      "args": ["-y", "@agentmemory/mcp"],
      "env": {"AGENTMEMORY_URL": "http://<host-ip>:3111"},
      "enabled": true
    },
    "headroom-compress": {
      "command": "/usr/bin/python3",
      "args": ["-m", "headroom.cli.mcp", "serve"],
      "enabled": true
    }
  },
  "skills": {
    "ciphercompress": {
      "path": "/home/kubuntux/.hermes/plugins/headroom_retrieve"
    }
  }
}
```

### 2. omp Extension

Create `~/.omp/extensions/ciphercompress/` with:
- `.mcp.json` — same MCP server config
- `skills/` → symlink to the Hermes plugin directory

Register in `~/.omp/agent/config.yml`:
```yaml
extensions:
  - ciphercompress
```

### 3. `.mcp.json` in project root

omp also loads `.mcp.json` from the **current working directory** (not home). Drop
a copy in each project root where omp is run, or use the extension method above
for global availability.

### Discovery Order

omp loads MCP servers from multiple providers with priority:
1. Claude Code plugins (`~/.claude/plugins/`) — user level
2. omp extensions (`~/.omp/extensions/*/`) — user level
3. `.mcp.json` / `mcp.json` in CWD — project level
4. Builtin discovery — bundled servers

The extension method (#2) is preferred for machine-wide availability. The Claude
Code plugin (#1) is a fallback for when extensions aren't loaded.

### 4. Transfer Identity + Skills to omp

After wiring MCP servers, transfer the agent's identity and skills into
omp's extension directory. omp's extension system auto-discovers:
`skills/`, `rules/`, `prompts/`, `hooks/`, and `.mcp.json`.

```bash
EXT=~/.omp/extensions/ciphercompress
mkdir -p $EXT/skills $EXT/rules $EXT/prompts $EXT/hooks/pre $EXT/hooks/post

# Identity files — omp loads SYSTEM.md as custom system prompt
cp ~/.hermes/SOUL.md       $EXT/..   # or ~/.omp/SOUL.md
cp ~/.hermes/IDENTITY.md   $EXT/..
cp ~/.hermes/MEMORY.md     $EXT/..
cp ~/.hermes/USER.md       $EXT/..
cp ~/.hermes/SYSTEM.md     $EXT/..   # omp-specific compact version
```

**Skill format:** omp skills are markdown files with YAML frontmatter:
```markdown
---
name: skill-name
description: One-line description
---
# Skill Name
Body content...
```

Create one `.md` file per skill under `skills/`. omp also loads `rules/`
for persistent operating rules and `prompts/` for prompt templates.

**Registration:** Add the extension to `~/.omp/agent/config.yml`:
```yaml
extensions:
  - ciphercompress
```

**Cognitive memory:** Copy the Hermes cognitive memory structure into
the extension for local logging alongside the shared agentmemory backend:
```bash
mkdir -p $EXT/memory/{episodes,graph,meta,procedures,vault}
cp -r ~/.hermes/memory/* $EXT/memory/
```

### Important Note

omp uses `bun` as its package manager, not `npm` or `pnpm`. The repo's `bun.lock`
and `package.json` require bun for install. If `catalog:` protocol errors appear
when using npm, that confirms the project is bun-only.

## Verification

```bash
# Headroom working
headroom compress "Hello world this is a test of the compression system"
headroom proxy --port 8787 &   # Start proxy

# Plugin loaded (after Hermes restart)
# Check available tools include headroom_retrieve, rtk_headroom_pipe, etc.

# Agentmemory bridge
curl -s -X POST http://100.93.75.87:3111/agentmemory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "compressed observation"}'
```

## Pitfalls

- **Path breaking:** The user's terminal PATH may drop system dirs. Always use
  full paths (`/usr/bin/python3`, `/usr/bin/sed`, `~/.npm-global/bin/agentmemory`)
  in background scripts and wrappers.
- **Proxy port 8787:** Default headroom proxy port. Check for conflicts.
- **agentmemory import:** Don't use `agentmemory import` while the daemon runs.
  It spawns a competing instance. Use the REST API (`POST /agentmemory/remember`)
  instead for bulk seeding.
- **Bun vs npm vs pnpm:** oh-my-pi uses `bun`, not `npm` or `pnpm`. Check
  the repo's package manager before installing.

## References

- `references/ciphercompress-implementation.md` — Full implementation details, REST API shapes, relevance scoring algorithm, structural compressor schema, Hermes plugin API patterns.
- `references/omp-wiring.md` — oh-my-pi MCP server discovery and extension wiring for agentmemory + headroom.
