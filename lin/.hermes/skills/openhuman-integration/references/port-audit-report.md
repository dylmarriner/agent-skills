# OpenHuman Port Audit

Full audit of all ~80 OpenHuman Rust modules evaluated for porting to Hermes.
For the general port-audit methodology, see `cross-codebase-port-audit` skill.

## Ported (8 plugins)

| Module | Plugin | Why | Effort |
|--------|--------|-----|--------|
| tokenjuice (src/openhuman/tokenjuice/ + vendor/tinyjuice/) | tokenjuice | Tool output compression with CCR cache | Medium |
| subconscious (src/openhuman/subconscious/) | subconscious | Background goal processing loop | Medium |
| memory_tree (src/openhuman/memory_tree/) | memory_tree | Hierarchical memory with cascade sealing | Medium |
| model_council (src/openhuman/model_council/) | model_council | Parallel model deliberation + chair synthesis | Medium |
| codegraph (src/openhuman/codegraph/) | codegraph | BM25 ranked code search | Medium |
| learning (src/openhuman/learning/) | learning | Behavioral profile building from agent turns | Hard |
| ragflow (external: infiniflow/ragflow) | ragflow | Enterprise RAG engine (Docker + API) | Easy (API client) |
| obelisk (external: dylmarriner/obelisk) | obelisk | Token-optimizing engine (Rust binary + plugin) | Easy (pre-built plugin) |

## Evaluated but Skipped (with reasons)

| Module | Why Skipped |
|--------|-------------|
| prompt_injection | User explicitly vetoed |
| flows/ | 300KB+, tightly coupled to tinyflows vendor crate |
| rhai_workflows/ | Coupled to Rhai runtime + tinyagents ReplSession |
| cron/ | Hermes already has cronjob tool |
| channels/ | Hermes already has gateway with 20+ platforms |
| approval/ | Hermes already has approval gates |
| search/ | Hermes already has web_search |
| sandbox/ | Hermes already has Docker sandbox |
| voice/ | Hermes already has STT/TTS |
| screen_intelligence/ | Hermes already has browser_vision |
| mcp_client/registry/server | Hermes already has MCP native client |
| artifacts/ | File read/write tools cover this |
| encryption/ | OS keyring handles secret storage |
| codegraph dense mode | Requires embedding provider; lexical only was sufficient |

## Key Porting Patterns Discovered

1. **Rust → Python translation**: OpenHuman modules are Rust, ported to Python Hermes plugins. Core logic (scoring, tokenization, caching) is algorithmically identical. Rust-specific async/type-system constructs are replaced with Python equivalents.

2. **CCR pattern** (from tokenjuice): Content-addressed cache (SHA-256) with recovery footers. Lossy compressors store originals for later retrieval. Two-tier: memory + disk.

3. **Stability detector** (from learning): Recency-decayed weighted scoring with per-class budgets. Generic pattern for any evidence-based system.

4. **BM25-Okapi** (from codegraph): Search ranking with k1=1.5, b=0.75. Code tokens extracted via camelCase/snake_case splitting.

5. **Fan-out orchestration** (from model_council): N parallel async tasks, collect results, pass to synthesis step. Generic for any parallel-model pattern.

## Never Suggest Again

- prompt_injection_guard — user explicitly vetoed
