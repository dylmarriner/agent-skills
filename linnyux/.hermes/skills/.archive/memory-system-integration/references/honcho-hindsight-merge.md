# Honcho + Hindsight Merges into Synapse Memory

## Honcho Merge (plastic-labs/honcho)

Cloned to `~/honcho` from `https://github.com/plastic-labs/honcho` (3 commits, 58f9abb).

### What was absorbed

Two modules into `app/adopted/`:

1. **dialectic_agent.py** — Multi-level agentic reasoner over memory. Supports configurable reasoning depth: minimal/low/medium/high/max. Core design:
   - `DialecticAgent` class with reasoning level configs in `LEVEL_CONFIGS`
   - Tool-calling LLM loop: prefetch → search → synthesize
   - Self-contained DB sessions per tool call (`SessionLocal()`)
   - Uses `app.search.vector.vector_search()` + `app.search.lexical.lexical_search()` via internal wrappers
   - Uses `app.llm.get_llm_client()` for LLM
   - No Honcho branding anywhere
   - REST: `POST /v1/adopted/dialectic`
   - MCP: `adopted_dialectic` (120s timeout)

2. **dreamer.py** — Background memory consolidation. Design:
   - 5-minute cycle via asyncio `create_task`
   - Clusters observations by cosine similarity on embeddings (threshold 0.65)
   - Derives deductions via LLM (1-2 sentence insights)
   - Detects contradictions within clusters
   - Saves `memory_type="deduction"` with importance=0.75
   - Tracks watermark by creation timestamp
   - REST: `POST /v1/adopted/consolidate/{agent_id}`, `POST /v1/adopted/dream/cycle`
   - MCP: `adopted_consolidate`, `adopted_dream_cycle`
   - Background lifecycle: `start_dreamer()` / `stop_dreamer()`

### Integration points touched

| File | Change |
|------|--------|
| `app/adopted/__init__.py` | Imports + REGISTRY entries + __all__ |
| `app/adopted/dialectic_agent.py` | New file |
| `app/adopted/dreamer.py` | New file |
| `app/routers/adopted.py` | 3 new endpoints |
| `app/mcp.py` | 3 tool schemas + 3 dispatch handlers |
| `app/main.py` | Dreamer startup in lifespan |

## Hindsight Merge (vectorize-io/hindsight)

Cloned to `/tmp/hindsight` from `https://github.com/vectorize-io/hindsight`.

Core UI at `/tmp/hindsight/hindsight-control-plane/` — Next.js + Tailwind + shadcn/ui app.

### What was absorbed

Three additions to the inline `_DASHBOARD_HTML` in `app/main.py`:

1. **Memory Detail Modal** — Click-to-expand modal with 3 sub-tabs (Detail, JSON, Related). Shows full metadata grid, tags, content. Confirm/contradict buttons. Copy JSON. Escape to dismiss.

2. **Entities Tab** — Grid of entity cards from `/v1/graph`. Name, type, memory/relation counts. Click to expand and see associated memories. Type distribution pills. Top entities panel.

3. **Documents Tab** — Browses Synapse's project system for ingested files. Lists with name, kind, date. Falls back to project listing if files API not available.

### Key UI patterns from Hindsight

Reference components at `/tmp/hindsight/hindsight-control-plane/src/components/`:
- `think-view.tsx` — LLM-powered reflection interface (inspirational for future reflect tab)
- `data-view.tsx` — Memory table with sorting, filtering, constellation view
- `memory-detail-modal.tsx` — Rich memory inspection
- `entities-view.tsx` — Entity browser
- `documents-view.tsx` — Document management
- `constellation.tsx` — Graph visualization
- `sidebar.tsx` — Collapsible side nav with Lucide icons
