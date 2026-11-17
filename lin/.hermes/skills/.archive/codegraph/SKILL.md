---
name: codegraph
description: Install, configure, and use CodeGraph — a pre-indexed code knowledge graph MCP server for Hermes Agent. Index any codebase locally with tree-sitter, query via MCP tools.
---

# CodeGraph MCP Server

CodeGraph is a local-first code intelligence tool that parses codebases with tree-sitter, stores results in SQLite (FTS5), and exposes a knowledge graph to AI agents over MCP. It runs 100% offline — no API keys, no data leaves your machine.

**Key benefit for Hermes:** You can answer "how does X work", "trace callers of Y", or "what files does Z affect" with 1-2 codegraph tool calls instead of fanning out across grep/glob/Read — typically cutting tool calls by 70%+ and cost by 35% on large repos.

## Installation

```bash
# Global install via npm (recommended — one binary for all projects)
npm i -g @colbymchenry/codegraph

# Configure for Hermes
codegraph install --target=hermes --yes --location=global
```

This adds an MCP server entry to `~/.hermes/config.yaml` and registers the `mcp-codegraph` toolset.

## Initialize a Project

```bash
cd /path/to/project
codegraph init -i
```

The `-i` flag runs initial indexing immediately. This parses every file with tree-sitter and builds the SQLite database at `.codegraph/` in the project root.

## Available MCP Tools

After init, these tools are available in any Hermes session connected to the project:

| Tool | Purpose |
|------|---------|
| `codegraph_context(task, maxNodes, includeCode)` | **Primary tool** — call FIRST. Composes search + node + callers + callees into one answer. Usually enough to respond with no further search/read. |
| `codegraph_search(query, kind, limit)` | Quick symbol search by name. Use before context when you need to find specific symbol names. |
| `codegraph_node(symbol, includeCode)` | Get one symbol's details + its callers and callees (the "trail"). Walk the call graph hop-by-hop. |
| `codegraph_explore(query, maxFiles)` | Returns source for several related symbols in one capped call. Efficient alternative to many `node` calls. |
| `codegraph_trace(from, to)` | Trace the call path between two symbols — "how does A reach B?" Returns the chain. |
| `codegraph_impact(symbol, depth)` | Analyze the impact radius of changing a symbol. |
| `codegraph_files(path, pattern)` | Get the project file tree from the index. Fast alternative to ls/find. |
| `codegraph_status(projectPath)` | Get index stats (files, nodes, edges). |
| `codegraph_callees(symbol, limit)` | Find what a symbol calls. |
| `codegraph_callers(symbol, limit)` | Find what calls a symbol. |

## Workflow

1. **First use in a project:** `codegraph init -i` to index
2. **After code changes:** CodeGraph has a file watcher (FSEvents/inotify) that auto-syncs. No manual re-index needed.
3. **In conversation with Hermes:** `codegraph_explore` (query with symbols or file names) or `codegraph_context` FIRST — before search_files, read_file, or terminal grep/ls. User explicitly flagged this preference: "you know you can read the indexed code." Do not default to filesystem browsing when the indexed graph returns verbatim source in ≤2 calls.
4. **For architecture questions:** `codegraph_explore(query, maxFiles=12+)` with the symbol names spanning the flow. Returns source for multiple files in one capped call — no Read after.
5. **For a specific symbol:** `codegraph_node(symbol, includeCode=true)` — source + callers + callees in one shot.
6. **To trace a call path:** `codegraph_trace(from, to)` — find how one symbol reaches another.

## Pitfalls

- **Cursor MCP cwd quirk:** Cursor launches MCP subprocesses with the wrong cwd. The installer injects `--path` into Cursor's MCP args. Not relevant for Hermes.
- **Project must be initialized first.** The MCP server connects fine, but tools return empty results if `codegraph init` hasn't been run in the project root. Run `codegraph init -i` in each project you want to query.
- **DeepSeek and codegraph tools:** Works fine — no special setup needed. The tools are local MCP calls, not LLM-dependent.
- **Large repos (10k+ files):** Indexing may take 30-60s on first run. Subsequent syncs are incremental and fast.
