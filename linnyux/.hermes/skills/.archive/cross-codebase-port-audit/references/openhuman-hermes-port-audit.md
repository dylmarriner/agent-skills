# OpenHuman → Hermes Port Audit (session example)

Assessment of 5 OpenHuman `src/openhuman/` modules for porting to Hermes Agent.

## Methodology

1. Located modules in `src/openhuman/<name>/` (not `vendor/` crates)
2. Read `mod.rs` first for architecture overview
3. Read `README.md` for design docs
4. Read 2-3 key source files per module (entry point + core types + orchestrator)
5. Compared feature-by-feature to Hermes equivalents (`search_files`, existing skills)
6. Assessed coupling depth (traits, config, event bus, vendor crates)
7. Estimated difficulty + produced recommendation

## Per-Module Assessment

### learning/ — Agent self-learning subsystem

**Feature summary:** Post-turn hooks that reflect on completed turns, extract user preferences (style, identity, tooling, vetoes, goals, channel), track tool effectiveness (success/failure/duration stats), and store learned facets in a decaying `user_profile_facets` cache. Core: `FacetClass` taxonomy (6 classes), `CueFamily` weighted evidence, `StabilityDetector` with half-life scoring, ring-buffer `Buffer`, `ProfileMdRenderer` for prompt injection.

**Hermes equivalent:** None. Hermes has no post-turn learning or behavior-based profile enrichment.

**Port difficulty:** Hard (~2-3 weeks). Deeply coupled to OH's `Memory` trait, `PostTurnHook` trait, `Agent` loop, `config::LearningConfig`, `ApprovalGate`, event bus, `memory_store::profile` table. `ReflectionHook` calls an LLM for structured output.

**Dependencies:** `Memory` trait, `PostTurnHook`, `config::LearningConfig`, `ApprovalGate`, event bus (`CacheRebuilt`), `memory_store::profile`, `Agent` runtime, `EmbeddingProvider`

**Recommendation:** Skip — too coupled to OH-specific hooks/infra. Revisit if Hermes develops a post-turn hook system.

---

### model_council/ — Multi-model deliberation

**Feature summary:** Runs one question through N member models concurrently (max 5), each with read-only agent loops, then a chair model synthesizes their answers highlighting agreement/disagreement/unique insights. Partial failure tolerated. Two APIs: batch (`run`) and progressive (`answer_member` + `synthesize`). Uses `tinyagents::graph::parallel::map_reduce` for fan-out.

**Hermes equivalent:** None. Single model per conversation. No council pattern.

**Port difficulty:** Medium (~1 week). Core is pure functions + orchestrator calling N concurrent model completions. Synthesis prompt is a hand-written template. Depends on `Agent::from_config_for_read_only_council_juror` (tool filtering) and standard inference.

**Dependencies:** `Agent` (read-only mode), inference provider, `tinyagents::graph::parallel::map_reduce` (can be replaced with `tokio::join_all`)

**Recommendation:** Port — high-value, self-contained, ~25KB. Only module with clear "port" verdict.

---

### flows/ — Workflow automation builder

**Feature summary:** Full workflow CRUD, run/resume with HITL approval gates, autonomy-tier gating, n8n import (9+ node types mapped to tinyflows), conditional routing, parallel fan-out, merge barriers, per-node error handling, retry, durable checkpoints.

**Hermes equivalent:** None. No workflow engine. `kanban-orchestrator` is task decomposition, not graph runtime.

**Port difficulty:** Hard (~3-4 weeks). ~300KB across 15 files. Deeply coupled to `tinyflows` vendor crate, `tinyagents` state-graph runtime, `ApprovalGate`, `Config`, `SecurityPolicy`, SQLite store, event bus.

**Dependencies:** `tinyflows` (vendor crate), `tinyagents` (state-graph runtime), `ApprovalGate`, `SecurityPolicy`, `Config`, SQLite (store), event bus (bus), `caps::*` trait seam

**Recommendation:** Skip — massive and coupled. If ever needed, fork `tinyflows` first.

---

### codegraph/ — Content-addressed code retrieval

**Feature summary:** Indexes git worktree code files → BM25 + dense vector RRF fusion for ranked file relevance. Content-addressed by blob SHA so incremental indexing is free. Pure Rust: `rusqlite`, `git ls-files`, heuristic structural doc extraction (no tree-sitter). Two modes: `Lexical` (BM25 only) and `Dense` (BM25 + embeddings). Two agent tools: `codegraph_index`, `codegraph_search`.

**Hermes equivalent:** Partial. `search_files` (ripgrep), `understand` (code analysis/knowledge graph). But none use BM25+dense RRF, content-addressed incremental indexing, or file relevance ranking.

**Port difficulty:** Medium (~1 week lexical, +1 week dense). ~67KB across 5 files. Dependencies: `rusqlite`, `serde`, `anyhow`, `async_trait`, `tokio`, and `EmbeddingProvider` trait for dense mode.

**Dependencies:** `rusqlite`, `EmbeddingProvider` trait (dense mode only), git CLI

**Recommendation:** Port (lexical first) — BM25 ranked search fills a gap nothing in Hermes covers. Content-addressed indexing stays fast on large repos.

---

### rhai_workflows/ — Language-based scripting runtime

**Feature summary:** Exposes TinyAgents' Rhai `.ragsh` REPL as a `rhai_workflows` tool. Model writes Rhai scripts (fan-out, loops, batched calls, dedup/verify pipelines) run cell-by-cell against persistent per-session namespace. Fail-closed: layered timeouts, LRU sessions (16), idle TTL, op limits, cancellation. Excludes recursion hazards.

**Hermes equivalent:** Partial. `delegate_task` / `subagent-driven-development` for sub-task orchestration. But no embedded scripting language runtime.

**Port difficulty:** Hard (~2-3 weeks). Tightly coupled to `tinyagents::ReplSession`, `tinyagents::CapabilityRegistry`, `tinyagents::ReplPolicy`. Bridge wires OH tools/provider/agents into tinyagents capability registry. Would require vendoring tinyagents or building Rhai integration from scratch.

**Dependencies:** `tinyagents` (ReplSession, CapabilityRegistry, ReplPolicy), `ApprovalGate`, `SecurityPolicy`, OH tool registry, OH provider model, OH sub-agent runner

**Recommendation:** Skip — tinyagents-coupled. If ever wanted, use `rhai` crate standalone.

## Summary Table

| Module | LOC | Hermes equiv | Difficulty | Verdict |
|--------|-----|-------------|-----------|---------|
| learning/ | ~200KB | None | Hard | Skip |
| model_council/ | ~25KB | None | Medium | Port |
| flows/ | ~300KB | None | Hard | Skip |
| codegraph/ | ~67KB | Partial (grep/understand) | Medium | Port (lexical first) |
| rhai_workflows/ | ~60KB | Partial (delegate_task) | Hard | Skip |

## Top Recommendations

1. **Port model_council/** — high-value multi-model deliberation, clean boundary, ~25KB
2. **Port codegraph/** (lexical mode first) — BM25 ranked file search, content-addressed incremental indexing

## Actual Outcomes (post-session)

| Module | Recommended | Actually Built | Plugin |
|--------|-------------|---------------|--------|
| model_council/ | Port ✅ | Built ✅ | model_council |
| codegraph/ (lexical) | Port ✅ | Built ✅ | codegraph |
| learning/ | Skip ❌ | User requested, built ✅ | learning |
| flows/ | Skip | Not built | — |
| rhai_workflows/ | Skip | Not built | — |
| — (not audited) | — | RAGFlow (external) | ragflow |
| — (not audited) | — | Obelisk (external) | obelisk |
