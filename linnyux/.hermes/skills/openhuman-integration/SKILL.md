---
name: openhuman-integration
description: "All OpenHuman/TinyAgents features ported to Hermes: 9 plugins covering tool compression, goal processing, memory trees, parallel model deliberation, BM25 code search, behavioral learning, RAGFlow, Obelisk, and Synapse Memory. NOTE: prompt injection guard was evaluated and rejected — do NOT suggest or build it."
---

# OpenHuman Integration — Features Ported to Hermes

**DO NOT BUILD PROMPT INJECTION GUARD.** Deleted and permanently forbidden per user veto. Never suggested, built, or referenced.

For the port-audit methodology used to evaluate all 80+ OpenHuman modules before building, see `skill_view(name="cross-codebase-port-audit")`. For general plugin-development patterns (hooks, plugin.yaml structure, debugging), see `skill_view(name="hermes-plugin-development")`. For the TinyJuice Rust engine that inspired TokenJuice v2, see `references/tinyjuice-architecture.md`.

Six features ported from OpenHuman and TinyAgents into Hermes as plugins, plus RAGFlow (external RAG engine) and Obelisk (token optimizer):

## 1. TokenJuice — Tool Output Compression (v2)

**Plugin:** `~/.hermes/plugins/tokenjuice/`

Port of OpenHuman's TinyJuice engine. Compresses tool output before it reaches
the LLM using content-aware compressors with CCR (Compress-Cache-Retrieve) for
lossy recovery, profiles, and savings tracking.

| Content Kind | Compressor | Typical Savings | Lossy? |
|---|---|---|---|
| JSON | serde minify | 40-70% | No |
| Code | Comment/whitespace strip | 30-50% | Yes (CCR) |
| HTML | Tag strip + text extract | 60-80% | No |
| Search Results | Top-K per file | 60-80% | Yes (CCR) |
| Logs | Run-length encode | 50-90% | No |
| Tables/CSV | Condense long runs | 40-70% | No |
| Generic | Line dedup/RLE | 20-40% | Yes (CCR) |

**Architecture:**
```
Tool output → profile check → content detection → compressor
  → CCR store original (if lossy) → append recovery footer → return compacted

Agent sees: compacted output + "call tokenjuice_retrieve '<token>'" footer
Agent calls: tokenjuice_retrieve(token) to get full original
```

**Profiles:**
- `full` — all compressors + CCR + lossy reductions (max savings)
- `light` — lossless only (JSON minify, HTML strip, log RLE)  
- `off` — bypass entirely

**CCR Cache:**
- Content-addressed (SHA-256 prefix, 32 hex chars)
- Two-tier: in-memory (256 entries / 64MiB) + disk at `~/.hermes/tokenjuice/ccr/`
- Lossy compressors store originals; compacted output carries recovery footer
- `tokenjuice_retrieve(token)` recovers full original

**Config:**
```yaml
tokenjuice:
  profile: full              # full | light | off
  min_bytes_to_compress: 2048
  json_enabled: true
  code_enabled: true
  html_enabled: true
  search_enabled: true
  generic_enabled: true
  max_output_chars: 50000
  ccr_max_entries: 256
  ccr_max_bytes: 67108864    # 64 MiB
  ccr_disk_enabled: true
```

**Stats:** `~/.hermes/tokenjuice_savings.json` — per-compressor breakdown with
tokens saved and events count.

## 2. Subconscious — Background Goal Processing

**Plugin:** `~/.hermes/plugins/subconscious/`
**Cron Job:** `subconscious-tick` (every 30 min)

A background loop that:
- Maintains persistent goals (stored in `~/.hermes/subconscious/goals.json`)
- Injects goal context into the LLM prompt on every 5th turn
- Ticks every 30 min to advance progress

**Goal Management:**
Goals have: title, description, priority (critical/high/medium/low), state (active/paused/completed/abandoned), progress notes.

**Usage:**
```python
from plugins.subconscious import add_goal, update_goal, list_active_goals

# Add a goal
add_goal("Implement OAuth2 flow", priority="high", tags=["auth", "security"])

# Update progress
update_goal("g1234567890", note="Designed token refresh pattern")
update_goal("g1234567890", state="completed")

# List active goals sorted by priority
goals = list_active_goals()
```

**Context Injection:**
The plugin hooks `pre_llm_call` every 5 minutes to inject active goals into the prompt, so the agent sees:
```
[SUBSCONSCIOUS — Active Goals]
  [HIGH] Implement OAuth2 flow — Designed token refresh pattern
  [MEDIUM] Fix memory leak in cache layer — Still investigating
[/SUBSCONSCIOUS]
```

## 4. Model Council — Parallel Model Deliberation

**Plugin:** `~/.hermes/plugins/model_council/`
**Command:** `/council <question> [--members model1,model2,...]`

Runs a question through N models in parallel, collects responses, then uses a chair model to synthesize where they agree, disagree, and what unique insights each contributes.

**Architecture:**
```
User question → spawn N member tasks (parallel, read-only context)
→ collect responses → pass debate record to chair model
→ return synthesis with agreement/disagreement/unique insights
```

**Default pool:** gpt-4o, claude-sonnet-4, gemini-2.5-flash

**Usage:**
```
/council "Explain the CAP theorem with real DB examples"
/council "How should I structure this API?" --members gpt-4o,claude-sonnet-4
```

**Features:**
- 3 default members (expandable to 5 via --members flag)
- Partial failure tolerated: individual member errors don't kill the council
- Member timeout: 60s each, council timeout: 300s total
- Chair model uses the user's configured default model

## 5. RAGFlow — Enterprise RAG Engine

**Source:** `/mnt/development1/ragflow/` (cloned from github.com/infiniflow/ragflow)
**Plugin:** `~/.hermes/plugins/ragflow/`
**Server:** Docker compose at `/mnt/development1/ragflow/docker/` (`docker compose up -d`)

Enterprise-grade RAG engine with deep document parsing (PDF, DOCX, Excel, images), intelligent chunking with layout analysis, hybrid search (BM25 + vector), and multi-turn retrieval.

**Requirements:**
- Docker engine running
- `RAGFLOW_API_KEY` env var set (from RAGFlow console at http://localhost:9380)
- `RAGFLOW_BASE_URL` env var (default: http://localhost:9380)
- Embedding model must be configured in RAGFlow for the dataset before search/upload will work (see `references/ragflow-troubleshooting.md`)
- If using a local embedding server (llama-server/Ollama), it MUST run as a Docker container on the `docker_ragflow` network — host port binding won't work due to Docker network isolation and UFW routed deny

**Container stack** lives at `/mnt/development1/ragflow/docker/` and runs on the `docker_ragflow` bridge network (172.22.0.x). The `--init-model-provider-tables` flag in docker-compose.yml resets the new model provider tables on restart — comment it out after initial setup.

**Tools registered (5):**
| Tool | Description |
|------|-------------|
| `ragflow_health` | Check server status |
| `ragflow_datasets` | List/create knowledge bases (action=list\|create) |
| `ragflow_upload` | Upload a file (PDF/DOCX/txt) to a dataset for indexing |
| `ragflow_search` | Hybrid search (BM25 + vector) with ranked chunks |
| `ragflow_chat` | Full RAG query — retrieves chunks and returns context |

**Usage:**
```python
from plugins.ragflow import ragflow_health, ragflow_datasets, ragflow_search

# Check status
health = ragflow_health({})
print(health)

# List datasets
datasets = ragflow_datasets({"action": "list"})
print(datasets)

# Search a dataset
results = ragflow_search({"dataset_id": "...", "query": "How does auth work?"})
print(results)
```

**SDK:** `pip install ragflow-sdk` for programmatic access outside Hermes tools.

## 6. Obelisk — Token-Optimizing Engine

**Source:** `/mnt/development1/obelisk/` (cloned from github.com/dylmarriner/obelisk)
**Binary:** `~/.local/bin/obelisk` (built from source, installed via `cargo build --release`)
**Plugin:** `~/.hermes/plugins/obelisk/`

Token-optimizing engine for AI coding agents. Compresses command output, strips boilerplate, provides symbol-level code retrieval, packs context bundles, and saves/restores work state — all through a reversible SQLite ledger.

**Tools registered (5):**
| Tool | Description |
|------|-------------|
| `obelisk_run` | Run a command and emit compact, reversible stdout/stderr |
| `obelisk_pack` | Build a provider-neutral, token-budgeted context bundle |
| `obelisk_outline` | Read file structure instead of dumping whole files |
| `obelisk_symbol` | Read one symbol definition instead of full file |
| `obelisk_stats` | Show token savings across layers |

**Usage:**
```bash
obelisk doctor                    # Check ledger health
obelisk run "cargo build"         # Compress command output
obelisk pack "*.py"               # Pack context with token budget
obelisk outline src/main.rs       # Show file structure
obelisk stats                     # Show token savings
obelisk install hermes            # Auto-install Hermes plugin
```

The plugin auto-discovers the obelisk binary at `~/.local/bin/obelisk`.

## 7. CodeGraph — BM25 Ranked Code Search

**Plugin:** `~/.hermes/plugins/codegraph/`
**Import:** `from plugins.codegraph import codegraph_index, codegraph_search`

Content-addressed BM25 code search. Indexes git-tracked code files and ranks them by relevance. Built on the BM25-Okapi ranking formula (see `references/bm25-algorithm.md`).

**Architecture:**
```
git ls-files → tokenize identifiers (camelCase/snake_case → sub-words)
→ BM25 index keyed by git blob SHA → search ranks by term frequency × IDF
→ returns ranked results with matching-line previews
```

**Usage:**
```python
from plugins.codegraph import codegraph_index, codegraph_search

# Index a repository
report = codegraph_index("/path/to/repo")
# Returns: {files, indexed, cached, skipped, timing}

# Search
results = codegraph_search("/path/to/repo", "database connection pool")
# Returns: {query, total_indexed, results: [{path, score, preview}], timing}
```

**Scoring:** BM25-Okapi with k1=1.5, b=0.75, per-term IDF. Tokens extracted from identifiers using camelCase/snake_case splitting with stop-word filtering.

**Storage:** SQLite at `~/.hermes/codegraph/<repo_id>.db`, keyed by git blob SHA — same content at same path reuses cache.

**File types:** 40+ code extensions (.py, .rs, .js, .ts, .go, .java, etc.), skips files >100KB.

## 8. Learning — Behavioral Profile Builder

**Plugin:** `~/.hermes/plugins/learning/`
**Import:** `from plugins.learning import get_profile, get_facets, get_tool_stats, force_rebuild`

Self-learning from agent behavior. Observes completed turns, extracts user preferences, tracks tool effectiveness, and builds a user profile over time. Three-phase architecture (see `references/stability-detector.md`):

**Phase 1 — Evidence Buffer:** Post-turn hooks emit evidence (preferences, tool stats, patterns) into a bounded FIFO buffer.

**Phase 2 — Stability Detector:** Periodically scores evidence using recency-decayed weighted formula. Facets below 0.15 score are pruned. Conflicts resolved by value with highest weighted support.

**Phase 3 — Profile Builder:** Renders stable facets as context block injected into system prompt every 5 minutes.

**Facet Classes (6):**
| Class | Examples | Budget |
|---|---|---|
| style | verbosity, formality, code format | 10 |
| identity | timezone, name, role | 8 |
| tooling | package manager, editor, OS | 8 |
| veto | explicit rejections, tool errors | 5 |
| goal | active projects, priorities | 5 |
| channel | preferred platform | 3 |

**Cue Families (weight):**
- explicit (1.0) — "I prefer pnpm"
- structural (0.9) — from file metadata
- behavioral (0.7) — from observed patterns
- recurrence (0.6) — from repeated behavior

**Automatic cues extracted:**
- Preference patterns: "I prefer X", "always/never use Y"
- Corrections: user says "no", "that's wrong", "stop"
- Tool effectiveness: success/failure/duration per tool
- Identity: timezone, name, role mentions

**Usage:**
```python
from plugins.learning import emit_evidence, force_rebuild, get_facets

# Manually emit evidence (public API)
emit_evidence("style", "verbosity", "concise", family="explicit")

# Force immediate rebuild
n = force_rebuild()

# Inspect learned profile
facets = get_facets()
for f in facets:
    print(f"[{f['class']}] {f['key']}={f['value']} score={f['score']:.2f}")
```

## 9. Memory Tree — Structured Memory Hierarchy

**Plugin:** `~/.hermes/plugins/memory_tree/`

Hierarchical memory storage inspired by OpenHuman's memory_tree:
- L0 leaves: raw memory entries
- L1+ summaries: compressed abstractions via cascade sealing
- SQLite persistence per namespace
- Keyword-based retrieval walks the tree

**Usage:**
```python
from plugins.memory_tree import MemoryTree

tree = MemoryTree("default")

# Store memories (L0 leaves)
tree.add_leaf("Project uses FastAPI with Pydantic v2", score=0.8, topics=["architecture"])
tree.add_leaf("Database is PostgreSQL 16 with asyncpg", score=0.7, topics=["infrastructure"])

# Seal a level — creates summary nodes
tree.seal_level(0)

# Retrieve by keyword
results = tree.retrieve("database")

# Walk the tree
root_nodes = tree.walk()
children = tree.drill_down(root_nodes[0].id)

# Stats
stats = tree.get_stats()
```

## Enabling Everything

All 9 plugins are enabled in `~/.hermes/config.yaml` under `plugins.enabled`:

```yaml
plugins:
  enabled:
    - tokenjuice
    - subconscious
    - memory_tree
    - model_council
    - codegraph
    - learning
    - ragflow
    - obelisk
    - synapse-memory
```

Configurable thresholds for TokenJuice and Learning:

```yaml
tokenjuice:
  profile: full
  min_bytes_to_compress: 2048

learning:
  enabled: true
  rebuild_interval: 300
```

Restart Hermes for new plugins to load. Subconscious-tick cron job runs every 30 min automatically.

## TinyAgents — Rust Harness Integration

The TinyAgents RLM (Recursive Language Model) harness is available as a Rust crate at `/mnt/development1/tinyagents/`. It provides:

- **Durable graph runtime** — checkpointed, LangGraph-style execution
- **Sub-agents as tools** — agents call agents recursively with depth tracking
- **`.rag` blueprint language** — declarative workflow definitions
- **`.ragsh` REPL** — imperative orchestration loop

Hermes already has `delegate_task` for sub-agents. The TinyAgents' graph checkpointing and `.rag` blueprint compiler are available as a Rust library. To use:

```bash
cd /mnt/development1/tinyagents
cargo add tinyagents
```

The recursive agent pattern (agents calling agents) is already covered by Hermes' `delegate_task` with configurable `max_spawn_depth`.

## Pitfalls & Verification

### Known Bugs Fixed Post-Deployment

**CodeGraph — `git ls-files --stage` parsing off by one.**
The `git ls-files --stage` command outputs: `mode SP sha SP stage TAB path`. The stage field (always `0` for normal files) sits *between* the blob SHA and the path. The initial code used `" ".join(parts[2:])` which merged the stage number into filepaths, causing `FileNotFoundError` on repos with spaces in directory/filenames. Fix: use `" ".join(parts[3:])` to skip the stage field. Patched in `~/.hermes/plugins/codegraph/__init__.py`.

**RAGFlow — embedding model must be configured before search/upload work.**
RAGFlow's Docker stack at `/mnt/development1/ragflow/docker/` starts clean
(ragflow + mysql + elasticsearch + valkey + minio). The API responds. But
search returns `LookupError: Provider not found for model .` and upload
returns `No file part!` until an embedding model provider is assigned to the
knowledge base. The embedding config lives in RAGFlow's console — point it at
an OpenAI-compatible endpoint (LiteLLM proxy at kubuntux:8002 works). Without
it, datasets exist but have 0 chunks and 0 results. See
`references/ragflow-troubleshooting.md` for the full debug session.

**RAGFlow — health endpoint always returns 404, that's normal.**
The API root `/`, `/_health`, `/api/` all return HTTP 404. The real API lives
at `/api/v1/` — verify with `/api/v1/datasets`. Don't diagnose "down" from a
top-level 404.

**RAGFlow — JWT warnings in logs are normal for API-only access.**
`load_user from jwt got exception No b'.' found in value` appears on every
non-authenticated request. Ignore for headless API use.

**Synapse Memory — hyphen in plugin dir name blocks direct `import`.**
Python module names cannot contain hyphens. The directory `synapse-memory/` means `from synapse_memory import ...` fails. To import for testing:
```python
import importlib
spec = importlib.util.spec_from_file_location('synapse_memory', '~/.hermes/plugins/synapse-memory/__init__.py')
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)
health = sm.synapse_health({})
```

**Memory Tree — need `sys.path` set.**
The plugin directory is not on `sys.path` by default. Import via:
```bash
cd ~/.hermes/plugins && python3 -c "import sys; sys.path.insert(0, '.'); from memory_tree import MemoryTree; ..."
```

### How to Verify Each Plugin Is Running

| Plugin | Quick Check | Expected Result | Tested |
|--------|-------------|-----------------|--------|
| **TokenJuice** | `ls ~/.hermes/tokenjuice/ccr/` | 1+ files (SHA-256 prefix hashes) | ✅ 3 CCR entries |
| **Subconscious** | `cat ~/.hermes/subconscious/state.json` | Has `tick_count`, `last_tick_at` | ✅ 2 ticks |
| **Learning** | `cat ~/.hermes/learning/facets.json` | Non-empty facet array | ✅ 3 facets learned |
| **Memory Tree** | Import + `get_stats()` | Node counts returned | ✅ Store/retrieve/seal works |
| **CodeGraph** | Index a git repo | Positive indexed count | ✅ 415 files in 3.9s |
| **Synapse Memory** | Import via importlib + `synapse_health({})` | `"status": "operational"` | ✅ All components green |
| **Obelisk** | `obelisk doctor` | `ledger : OK` | ✅ 1 blob, ledger OK |
| **Model Council** | `/council "test"` | Council invokes | ✅ Slot command registered |
| **RAGFlow** | `curl localhost:9380/api/v1/datasets` | Dataset list returned | ✅ API up, llama-server built + containerized, embedding config WIP |

### If a Plugin Disappears at Restart

Check in order:
1. Directory still in `~/.hermes/plugins/`?
2. Name in `plugins.enabled` in `config.yaml`? (JSON string, not YAML list)
3. `plugin.yaml` valid?
4. `__init__.py` with `register(ctx)` present?
5. `grep -i "plugin" ~/.hermes/logs/*.log` for registration errors
