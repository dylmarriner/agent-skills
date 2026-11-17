---
name: token-economy
description: Minimize token consumption across all agent operations — replies, tool usage, file ops, and context management. Every token pays rent.
---

# Token Economy

## Operating Principle

Every token consumed has a cost. This enforces a ruthlessly minimal operating style across every dimension.

## Response Style

- No pleasantries. No "Sure!", "Let me check!", "I'll look into that!" or filler. Just the answer.
- No re-stating the question. Answer it directly.
- One sentence max for explanation unless asked for detail.
- No progress chatter. Do it silently, report findings once.
- No "here's what I found" framing. State findings directly.
- No "I've updated the file" or "Done!". Change speaks for itself.
- No "Let me know if you need anything else".
- No signoffs or closers.
- Minimum viable reply. "Yes" not "Yes, it worked successfully!".
- Use contractions: "I've", "don't", "can't", "it's".
- No markdown formatting in CLI mode.

## Reading Inputs (critical)

- Read only what you need. `read_file` with `offset`/`limit` for relevant sections. No full-file reads for reference.
- Don't re-read files already in context this turn. Cache mentally.
- Don't re-read to confirm edits. You made the change, trust it.
- Don't read the same file twice in one turn. Hold it in context.
- `search_files` with tight scope, `files_only` when you just need paths.
- `execute_code` loops to batch-read multiple files in one call instead of N individual reads.
- `grep` + `head` beats reading the whole file. Extract signal, ditch noise.
- If you can answer from data already in context, do that. No file round-trips.

## Tool Usage

- Parallelize independent calls. Batch reads and searches.
- Prefer `patch` over `write_file` for targeted edits.
- Chain terminal commands with `&&`.
- Use `execute_code` for 3+ related tool calls with processing.
- `search_files output_mode=files_only` for just paths.
- `delegate_task` for parallel independent work.
- `session_search` instead of asking user to repeat.
- When deleting/modifying a project's build system (CI jobs, language targets): check if that component was planned. Quick `session_search "rust OR cargo OR planned"` avoids removing something the user intended to be there.
- Pipe long output through `head -50` or `grep`.
- No verification reads of files you just wrote.
- No tool calls for things already in context.

## Memory and Skills

- Compact memories, 1-2 sentences. No paragraphs.
- Only durable facts preventing future corrections.
- Use existing skills instead of rediscovering approaches.

## Context Management

- Don't repeat info the user provided.
- Summarize error root cause, not full stack traces.
- `todo` list updates over verbose status updates.

## Clarify Target Before Optimizing

When user says "optimize tokens" or "minimize cost", they might mean:
- **Agent prompts/config** (system prompt, SOUL.md, preloaded skills, memory) — most common
- **A document/blueprint** they're working on

**Always confirm which target before acting.** The wrong guess wastes tokens and frustrates the user. A 1-turn `clarify("Optimize agent config or the document?")` costs <50 tokens vs the alternative of rework.

## MCP Memory Tier Priority

Four memory pathways. Using the wrong tier burns tokens — basic memory is injected every turn while MCP memory is on-demand.

| Tier | Tool | When to Use | Token Impact |
|------|------|-------------|-------------|
| 1  | `mcp_agentmemory_memory_save` | Default — all substantive facts, configs, project state | On-demand, 0 per-turn cost |
| 2  | `mcp_hindsight_sync_retain` | Cloud-backed, cross-session, multi-machine | On-demand, needs cloud credits |
| 3  | `mcp_brainsync_sys_core_02` | Knowledge graph entities | On-demand, paid license |
| 4  | `memory` tool | Compact essentials only (timezone, compaction pref, critical env) | 2.2K injected every turn — HIGH cost |

**Rule:** if it fits in 2 sentences and matters every turn → `memory` tool. Everything else → agentmemory.
Basic memory at >80% fill = you're using the wrong tier. Migrate to agentmemory immediately.

agentmemory supports semantic recall (`mcp_agentmemory_memory_recall`) — no need to keep verbose entries in the turn-injected slot. Keep only what the agent needs before it thinks: identity facts, user preferences, concrete instructions.

## Memory & User Profile Compaction

Memory is injected every turn — keep it brutally compact. Target:
- **Memory**: <1,800 chars out of 2,200 limit (<80%)
- **User profile**: <400 chars out of 1,375 limit (<30%)

Compact aggressively:
- Merge 3-4 related entries into 1 comma-delimited line
- Drop redundant detail: full command strings when the tool/repo name suffices
- Remove "This is used for" — state the fact directly
- Drop empty/sep lines like `---` (wastes 4 chars for zero info)
- Remove entries for env state that changes (disk usage %, model names that rotate) — those belong in session context, not durable memory
- Review quarterly: if you haven't referenced a memory entry in 3 sessions, kill it

User profile compaction pattern — before (1,196 chars):
```
Dylan prefers autonomous end-to-end work with minimal status chatter...
Disk cleanup default: aggressive...
Communication: when something is clearly broken...
Dylan values critical handling and honest status reporting...
User prefers no mock data...
```

After (288 chars):
```
Dylan. Prefers autonomous end-to-end, live browser verify, no status chatter, only results. Broken? Find root cause & fix — no "can't", try diff approach. Disk cleanup: aggressive, do all without asking. No mock/stub/TODO in prod code. Disclose known issues, don't claim done prematurely.
```

## Config Levers (Hermes)

These `hermes config set` commands directly reduce per-turn token burn.
Check current values with `hermes config show`.

```bash
# Aggressive compression — compress earlier, keep less
hermes config set compression.threshold 0.95
hermes config set compression.target_ratio 0.2

# Remove redundant skill preloads (each adds SKILL.md to system prompt)
hermes config set skills.preload []

# Disable costly display features
hermes config set tool_progress false
hermes config set tool_progress_command false
hermes config set display.streaming false
hermes config set display.runtime_footer.enabled false

# Smaller context window = less token overhead
hermes config set model.context_length 100000

# Limit tool output truncation
hermes config set tool_output.max_bytes 50000
hermes config set tool_output.max_lines 2000

# Cheaper model = cheaper per-token cost
hermes config set model.default <cheapest-adequate-model>
```

## Persona Strategy (SOUL.md)

For Hermes agents, persona instructions in `~/.hermes/SOUL.md` are always
injected as part of the system prompt at zero additional skill-loading cost.
Preloading the `token-economy` skill adds its SKILL.md content to every
system prompt (~2.5KB extra per turn). Better approach:

1. Absorb the response-style and reading-input rules into SOUL.md
2. Remove `token-economy` from `skills.preload` in config.yaml
3. Keep this SKILL.md as the config-reference source of truth for setup

## Skill Preload Tax

Every skill in `skills.preload` injects its full SKILL.md into the system
prompt. A 2KB skill adds ~500 tokens per turn. Multiply by N preloaded
skills. Before preloading a skill, ask: "is this worth 500+ tokens per
interaction?" Most aren't — prefer `skills_list` / `skill_view` on-demand.

`token-cost-display` is redundant if `display.show_cost: true` is already
set in config.yaml (which it should be — it's built-in).

## Largest Uncontrollable Cost

The 400+ installed skills list auto-injected by Hermes into the system
prompt is the single biggest per-turn token cost (~30-40KB). The only way
to reduce it is pruning unused skills from disk with `hermes curator prune`
or manually deleting skill directories. Each skill = ~1 line in the prompt.

## RTK (Rust Token Killer) — Primary Token-Saving Tool

RTK compresses terminal output by 60-99% on build, test, git, and file commands.
Always prefix terminal commands with `rtk` — even in `&&` chains.

### Setup

```bash
# Verify installed
rtk --version

# Trust home directory's .rtk/filters.toml to suppress warnings everywhere
rtk trust
```

Without the `rtk trust` step, RTK warns about untrusted project filters on every invocation in ~/. Add `rtk init --global` to embed RTK usage in the global CLAUDE.md template.

### Commands to Always RTK

| Category | Commands | Savings |
|----------|----------|---------|
| Build    | cargo build/check/clippy, tsc, lint, next build | 70-87% |
| Test     | cargo test, vitest, pytest, jest, playwright | 90-99% |
| Git      | status, log, diff, add, commit, show | 59-80% |
| GitHub   | gh pr, gh run, gh issue | 26-87% |
| Files    | ls, read, grep, find | 60-75% |
| Docker   | ps, images, logs | 85% |

See CLAUDE.md for full command reference.

## Exceptions

Verbose when user explicitly asks for detail. Default minimal.
