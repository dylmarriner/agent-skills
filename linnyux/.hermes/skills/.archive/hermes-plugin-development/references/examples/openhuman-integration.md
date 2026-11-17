# OpenHuman Integration — Real-World Plugin Case Study

This reference documents how three features from [OpenHuman](https://github.com/tinyhumansai/openhuman) and [TinyAgents](https://github.com/tinyhumansai/tinyagents) were ported to Hermes as plugins.

## Overview

| Feature | Source | Hermes Plugin | Pattern |
|---------|--------|---------------|---------|
| TokenJuice | OpenHuman `vendor/tinyjuice/` | `~/.hermes/plugins/tokenjuice/` | Transform hooks |
| Subconscious | OpenHuman `src/openhuman/subconscious/` | `~/.hermes/plugins/subconscious/` | pre_llm_call + cron |
| Memory Tree | OpenHuman `src/openhuman/memory_tree/` | `~/.hermes/plugins/memory_tree/` | Standalone SQLite lib |

## 1. TokenJuice — Tool Output Compression

### Original (Rust, OpenHuman)

OpenHuman's TinyJuice engine (`vendor/tinyjuice/`) is a Rust crate with:
- Content detection (`detect/`) — identifies JSON, code, HTML, search, logs
- Compressors (`compressors/`) — each content kind gets its own compression strategy
- CCR cache (`cache/`) — recently-compressed results cache for retrieval tools
- Rules engine (`rules/`) — configurable compression rules
- Tool integration (`tool_integration/`) — inline compaction during agent turns

The engine is installed at startup via `install_from_config()` and hooks into the agent's tool output pipeline to compact results before they reach the LLM.

### Ported (Python, Hermes)

The Hermes plugin at `~/.hermes/plugins/tokenjuice/` implements the same pipeline:

```
raw output → detect_content_kind() → choose compressor → compress → return str|None
```

Key design decisions:
- **Content detection**: Regex/structural heuristics (JSON starts with `{`/`[`, HTML has tags, code has keywords, search has file:line patterns)
- **Compressors**: 7 compressors — JSON minify, HTML strip, code strip, search dedup, log RLE, CSV condense, generic dedup
- **Passthrough safeguard**: If compressed output is ≥95% of original, returns None (no-op)
- **Size gate**: Skips outputs under 512 bytes (configurable via `min_bytes_to_compress`)
- **Tool exceptions**: Never compresses `browser_snapshot` or `browser_vision` to preserve spatial data
- **Stats tracking**: JSON file at `~/.hermes/tokenjuice_savings.json` with per-compressor breakdown

Hook used: `transform_terminal_output` + `transform_tool_result`

Typical savings:
- JSON: 50-70%
- HTML: 60-80%
- Code: 30-50%
- Logs with repeats: 60-90%

## 2. Subconscious — Background Goal Processing

### Original (Rust, OpenHuman)

OpenHuman's Subconscious (`src/openhuman/subconscious/`) is a cron-driven loop:
- **Observer**: Diffs memory sources against a baseline checkpoint
- **Reflector**: Runs a slim decision LLM agent over the diff
- **Committer**: Advances the checkpoint, persists state
- Runs every 20 minutes per "world" (memory, tinyplace)
- Uses TinyAgents graph runtime for durable checkpointed execution

### Ported (Python, Hermes)

The Hermes plugin at `~/.hermes/plugins/subconscious/` implements:
- **Goal store**: JSON file at `~/.hermes/subconscious/goals.json` — persistent, editable
- **State tracker**: `~/.hermes/subconscious/state.json` — tick count, last tick time, diff summary
- **Context injection**: `pre_llm_call` hook injects active goals into every LLM turn (5-min cooldown)
- **Tick loop**: Cron job `subconscious-tick` runs every 30 minutes

Goal data model:
```python
{
    "id": "g1234567890",
    "title": "Implement OAuth2 flow",
    "description": "Add OAuth2 with refresh token grant",
    "priority": "high",         # critical | high | medium | low
    "state": "active",          # active | paused | completed | abandoned
    "tags": ["auth", "security"],
    "created_at": 1234567890.0,
    "updated_at": 1234567890.0,
    "progress_notes": [
        {"text": "Designed token refresh pattern", "at": 1234567890.0}
    ]
}
```

The context injected by `pre_llm_call`:
```
[SUBSCONSCIOUS — Active Goals]
  [HIGH] Implement OAuth2 flow — Designed token refresh pattern
  [MEDIUM] Fix memory leak — Still investigating
[/SUBSCONSCIOUS]
```

## 3. Memory Tree — Structured Memory Storage

### Original (Rust, OpenHuman)

OpenHuman's Memory Tree (`src/openhuman/memory_tree/`) uses SQLite with a hierarchical node structure:
- L0 leaves: raw memory entries
- L1-LN summaries: cascading seal compression
- Retrieval: keyword + score walk
- `memory_store::trees` persistence layer

### Ported (Python, Hermes)

The Hermes plugin at `~/.hermes/plugins/memory_tree/` implements:
- Per-namespace SQLite databases at `~/.hermes/memory-tree/<namespace>.db`
- TreeNode: `{id, parent_id, level, content, score, entities, topics, timestamp}`
- `seal_level(n)`: Summarizes Ln nodes into L(n+1) summary
- `retrieve(query)`: Keyword matching with dedup and score sorting
- `walk()`, `drill_down()`: Tree traversal
- `get_stats()`: Database statistics

## Files Created

| File | Role |
|------|------|
| `~/.hermes/plugins/tokenjuice/plugin.yaml` | Plugin manifest |
| `~/.hermes/plugins/tokenjuice/__init__.py` | 7 compressors + 2 hooks |
| `~/.hermes/plugins/subconscious/plugin.yaml` | Plugin manifest |
| `~/.hermes/plugins/subconscious/__init__.py` | Goal CRUD + pre_llm_call hook |
| `~/.hermes/plugins/memory_tree/plugin.yaml` | Plugin manifest |
| `~/.hermes/plugins/memory_tree/__init__.py` | MemoryTree class (SQLite) |
| Cron job `subconscious-tick` | Every 30 min background tick |
| `~/.hermes/skills/openhuman-integration/SKILL.md` | Integration docs |
