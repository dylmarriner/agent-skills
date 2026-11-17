# OpenViking → Synapse Memory Gap Analysis

Source: volcengine/OpenViking (26.4k stars, AGPLv3)
Target: Synapse Memory (dylanmarriner/synapse-memory)
Date: 2026-07-08
Session: Deep-dive into OpenViking's architecture via repo browsing and source reading.

## Context

OpenViking is a **Context Database** designed specifically for AI agents. It abandons flat vector storage for a **filesystem paradigm** (RAGFS) where agent context is organized as hierarchical directories with tiered abstraction levels. Built primarily in Rust+Python (PyO3 bindings), with a full Python SDK, CLI, and MCP endpoint.

## Gap Summary

| Feature | OpenViking | Synapse Memory | Priority | Effort |
|---------|-----------|---------------|----------|--------|
| Filesystem memory hierarchy | viking://user/{id}/memories/{type}/ URIs | Flat `memories` table with agent_id + tags | HIGH | Large |
| L0/L1/L2 context tiering | .abstract.md / .overview.md / full content | Single content field | HIGH | Small |
| YAML memory type schemas | User-extensible schema files defining validation + extraction | 5 hardcoded types (world/experience/observation/preference/lesson) | HIGH | Medium |
| Session extraction (ReAct loop) | VLM-based ReAct with tools (ls/read/search) + patch-merge | Single-call LLM extraction | MEDIUM | Large |
| Skill extraction from conversations | Auto-detects skills learned, generates SKILL.md, deduplicates | None | MEDIUM | Medium |
| Training/policy optimization | RolloutAnalyzer → GradientEstimator → PolicyOptimizer → PolicyUpdater | None (no learning loop) | LOW | Very Large |
| Hierarchical retrieval | Directory-based recursive search + score propagation + reranker | Flat vector + lexical + graph + temporal fusion | MEDIUM | Large |
| Memory lifecycle (decay/archival) | Hotness scoring, consolidation, archival policies | Basic consolidation only | LOW | Medium |
| Peer memory isolation | viking://user/{id}/peers/{peer_id}/memories/ | None | LOW | Medium |
| Ingest from agent logs | Built-in source for Hermes, Claude Code, Codex, Cursor, OpenClaw, OpenCode | None | LOW | Medium |
| Rust-native filesystem ops | RAGFS with PyO3 — ls, read, write, mkdir, mv, cp, rm at native speed | PostgreSQL + pgvector only | LOW | Very Large |
| Observability/metrics | OpenTelemetry, Prometheus, usage audit, system probes | Basic admin metrics endpoint | LOW | Medium |

## Architecture Details

### 1. Filesystem Paradigm (RAGFS)

OpenViking organizes ALL context as a virtual filesystem with `viking://` URIs:

```
viking://user/{user_id}/memories/preferences/
viking://user/{user_id}/memories/entities/
viking://user/{user_id}/memories/events/
viking://user/{user_id}/memories/cases/
viking://user/{user_id}/memories/patterns/
viking://user/{user_id}/memories/tools/
viking://user/{user_id}/memories/skills/
viking://user/{user_id}/memories/trajectories/
viking://user/{user_id}/memories/experiences/
viking://user/{user_id}/resources/
viking://user/{user_id}/skills/
viking://user/{user_id}/peers/{peer}/memories/
viking://user/{user_id}/sessions/
viking://user/{user_id}/privacy/
viking://resources/        (global shared)
viking://agent/skills/     (shared agent skills)
```

Each directory has a `DirectoryDefinition` with pre-populated L0 + L1 descriptions. Directories are discoverable via `ls` commands — agents can navigate memory like a filesystem.

**Key insight:** Instead of a single `memories` table with agent_id + tags, each memory has a path that encodes its scope (user/agent), category (memories/resources/skills), and subtype (preferences/entities/events/patterns/cases/tools/trajectories/experiences).

**Current Synapse Memory model:** Single `memories` table with `agent_id`, `memory_type` (string enum), `tags` (JSON array), `content` (text). No hierarchy, no directory structure.

### 2. Tiered Context (L0/L1/L2)

Each memory entry stores three files at its URI:

| Level | Suffix | Content | Agent loading |
|-------|--------|---------|--------------|
| L0 | `.abstract.md` | 1-line summary | Always load LD of everything |
| L1 | `.overview.md` | Paragraph overview | Load L1 for matched items |
| L2 | Full content | Complete text | Load L2 for selected items |

The context builder: scan → ls all L0 (cheap), semantic search finds relevant directories → ls L1 summaries (token-light), then deep-read only what's needed. Dramatic token savings vs always loading full content.

### 3. Session Memory Extraction (ExtractLoop + SessionCompressorV3)

OpenViking's memory extraction uses a **ReAct loop with tool use** — not a single-shot LLM call:

```
Session messages
       │
       ▼
Read current memory files (ls + read to understand what exists)
       │
       ▼
LLM decides: call tools (ls/read/search current memory) OR emit final operations
       │
       ▼
If tools called → execute, feed results back, loop
       │
       ▼
If operations emitted → patch-merge existing files → done
```

Key differences from Synapse Memory's single-call extractor:
- **Patch-merge, not overwrite**: Edits existing memory files by finding and replacing specific sections, not rewriting from scratch.
- **Page IDs**: Each memory item has a stable page_id for reference. New items get page_id >= 100. Edits reuse existing page_id. Deletes reference page_id.
- **Link management**: Memories can link to each other (forward+backward links).
- **Tool use**: The LLM can explore what's already in memory before deciding what to change — avoids duplication.
- **Isolation handler**: Prevents cross-peer memory contamination.

### 4. YAML Memory Type Schemas

Memory types are defined as YAML schema files:

```yaml
name: cases
stage: user
peer_enabled: true
fields:
  - name: case_name
    type: string
    required: true
  - name: problem
    type: string
    required: true
  - name: resolution
    type: string
    required: true
  - name: applicability
    type: string[]
    required: false
```

The `SchemaModelGenerator` creates Pydantic models + extraction prompts dynamically. Users can define new memory types without code changes.

Synapse Memory has 5 hardcoded types in `memory/extract.py` — adding a new type requires code changes.

### 5. Training / Policy Optimization

The `session/train/` module implements a full gradient-descent-style pipeline over memories:

| Component | Role |
|-----------|------|
| Rollout | A recorded execution (conversation + tool calls) |
| RolloutAnalyzer | Parses a rollout → extracts trajectory + outcome |
| GradientEstimator | Compares rollout outcome vs policy → emits "semantic gradients" |
| PolicyOptimizer | Aggregates gradients → plans patch-merge updates to experience files |
| PolicyUpdater | Applies the plan to VikingFS with file locking |
| StreamingPolicyTrainer | Real-time trainer in the compressor loop |

A **semantic gradient** is defined as a `PatchSemanticGradient` — a before/after `MemoryFile` pair with rationale and confidence. The optimizer merges multiple gradients into a single `PolicyUpdatePlan`.

This enables: the system learns from its own execution patterns and iteratively improves its knowledge files.

### 6. Ingest System

OpenViking can **ingest session logs** from all major agent platforms:

```python
# openviking/ingest/sources/hermes.py
# Reads ~/.hermes/sessions/*.jsonl
# Normalizes messages, extracts user/assistant turns
# Also supports: claude_code, codex, cursor, openclaw, opencode
```

The ingestor reads `session_meta` (model + platform), user/assistant messages, and reconstructs sessions for memory extraction.

## Key Source Files (for future reference)

| File | Purpose |
|------|---------|
| `openviking/core/context.py` | Core `Context` class with URI, levels, ownership |
| `openviking/core/directories.py` | `PRESET_DIRECTORIES` — the directory tree definition |
| `openviking/core/namespace.py` | URI parsing, canonicalization, scope resolution |
| `openviking/core/building_tree.py` | `BuildingTree` — in-memory context tree container |
| `openviking/core/retrieval_targets.py` | Target resolution for search/find |
| `openviking/session/compressor_v3.py` | `SessionCompressorV3` — extraction orchestrator |
| `openviking/session/memory/extract_loop.py` | `ExtractLoop` — ReAct loop for memory updates |
| `openviking/session/memory/tools.py` | Memory tools (read, search, ls) |
| `openviking/session/memory/core.py` | `ExtractContextProvider` interface |
| `openviking/session/memory/memory_updater.py` | `MemoryUpdater` — applies resolved operations |
| `openviking/session/memory/schema_model_generator.py` | Generates Pydantic models from YAML schemas |
| `openviking/session/memory_policy.py` | `MemoryPolicy` — extraction policy config |
| `openviking/retrieve/hierarchical_retriever.py` | `HierarchicalRetriever` — directory-based search |
| `openviking/storage/viking_fs.py` | `VikingFS` — filesystem abstraction over AGFS |
| `openviking/storage/queuefs/` | Filesystem-based async queue for semantic processing |
| `openviking/pyagfs/` | Python SDK for the Rust RAGFS filesystem |
| `openviking/ingest/sources/hermes.py` | Hermes session log ingester |
| `openviking/session/train/engine.py` | `PolicyTrainingEngine` — training pipeline |
| `openviking/session/train/gradients.py` | `PatchSemanticGradient` — gradient definition |
| `openviking/session/train/domain.py` | Training domain models (Policy, PolicySet, Rollout) |
| `openviking/server/mcp_endpoint.py` | MCP SSE endpoint |
| `openviking/server/routers/` | All REST API routers (20+ routers) |
