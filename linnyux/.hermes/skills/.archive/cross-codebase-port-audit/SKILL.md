---
name: cross-codebase-port-audit
description: |
  Evaluate modules from a source codebase against a target codebase and
  produce structured port/no-port/skip recommendations. Assesses feature
  overlap, integration coupling, port difficulty, and priority. The pre-port
  audit — answers "what should we port?" before anyone writes code.
trigger: |
  Use when the user asks to evaluate, assess, analyze, or compare modules
  from one codebase for integration or porting into another. Signals:
  "audit these modules", "are any of these worth porting", "what should we
  take from X", "compare X and Y modules", "should we port Z".
  Also use for architecture-level gap analysis: "what is this project
  doing differently that we should adopt", "integrate anything we're
  missing from X into Y", "how does X compare to our stack".
---

# Cross-Codebase Port Audit

Systematically evaluate source-codebase modules and recommend which to port
to a target codebase and which to skip.

## Workflow

### 1. Locate the Modules

Source modules often live under a `src/`, `crates/`, `packages/`, or
`vendor/` directory. Find them first:

```bash
# Explore the source tree
find <src_dir> -maxdepth 3 -type d | head -40

# Search for the specific module names
ls <src_dir>/<module_name>/
```

Don't assume where they are — search for them if the first guess fails.

### 2. Read Structural Overview (mod.rs / __init__.py)

Every Rust module has a `mod.rs` (or the newer directory-as-module pattern).
This is the map of the territory. Read it first:

```python
mod.rs = read module's mod.rs
mod.rs tells you: what submodules exist, what's re-exported, what the
module's docstring says it does.
```

The docstring at the top of `mod.rs` is authoritative — it tells you what
the module authors intended, which may differ from the code's de facto role.

### 3. Read Design Documentation (README.md)

Many modules have a README.md with design rationale, responsibility
boundary definitions, and architecture notes that mod.rs omits.

Pay attention to:
- **Responsibilities** section — what it explicitly owns vs delegates
- **Key files** table — which file does what
- **Public surface** — what's exported (this is the API, the rest is internal)
- **Dependencies** — what other modules/systems it couples to

### 4. Read Key Source Files

For each module, read 2-3 core implementation files. Which ones?

- `mod.rs` tells you: look for the file that has the orchestrator/runner
  function (e.g., `council.rs`, `ops.rs`, `run.rs`)
- If there's a `candidate.rs` or types file, that defines the core types
- If there's an `ops.rs` or main logic file, that has the meat

Read enough to understand:
- **Core types** — what data structures define the module
- **Main orchestrator** — how does the module do its primary job
- **Integration points** — what traits/objects from the rest of the codebase
  does it depend on (these are the coupling costs)

### 5. Find Feature Equivalents in Target

For each module feature, ask: does the target codebase (Hermes) already
have something that does this?

Check:
- Agent tools (tools/ directory or tool registry)
- Existing skills (with skills_list)
- Existing modules (src/openhuman/ or src/ directory)
- Search for keywords from the source module in the target

Mark each feature as: already-covered / none / partial

### 6. Assess Coupling Depth

For each module, identify ALL dependencies on the source codebase's
infrastructure:

| Dependency type | Examples |
|----------------|---------|
| Traits/Abstractions | Memory trait, PostTurnHook, EmbeddingProvider |
| Config sections | LearningConfig, SecurityPolicy |
| Runtime services | Event bus, approval gate, agent registry |
| External crates | tinyagents, tinyflows |
| Vendor crates | vendored submodules not on crates.io |

Count how many of these would need to be ported, stubbed, or abstracted.

### 7. Estimate Difficulty

Three levels:

- **Easy** (<1 day): Self-contained logic, no traits, no external deps.
  Pure functions + schemas. Can be lifted out.

- **Medium** (~1 week): Uses one or two trait abstractions that can be
  replaced with a small Hermes equivalent. Moderate coupling.

- **Hard** (2+ weeks): Deeply coupled to source-specific traits, runtime,
  event bus, config, vendor crates. Requires porting supporting infrastructure.

Rule of thumb: if it imports from 5+ source-internal modules and depends
on a vendor crate, it's Hard.

### 8. Produce Structured Report

For each module, deliver:

```
## Module name — one-line verdict

**Feature summary:** 3-5 sentence overview

**Hermes equivalent:** What Hermes already has (or "None")

**Port difficulty:** Easy / Medium / Hard

**Key dependencies:** List the top integration couplings

**Recommendation:** Port / Skip / Already-covered

**Rationale:** 2-3 sentence justification
```

End with a summary table:

| Module | LOC | Hermes equiv | Difficulty | Verdict |
|--------|-----|-------------|-----------|---------|
| name | ~NKB | None/Partial | Easy/M/H | Port/Skip/Covered |

And a top recommendation(s) section: which module(s) to prioritize and why.

## Architecture-Level Gap Analysis (Variant)

When the target is to compare **architectural approaches** rather than
individual code modules (e.g. "what is X doing differently that we should
adopt"), adapt the workflow:

### A1. Learn the Source's Mental Model

Read the README and top-level docs first. The source project has a core
abstraction that drives everything (e.g. OpenViking's "filesystem
paradigm"). Understand that abstraction before diving into code.

### A2. Map the Source's Directory Tree

Get the full recursive file list — this reveals the scope:
```
curl -sL https://api.github.com/repos/org/repo/git/trees/main?recursive=1 \
  | python3 -c "import json,sys; data=json.load(sys.stdin); [print(t['path']) for t in data.get('tree',[]) if t['type']=='blob']"
```

Group files by semantic domain (core, storage, retrieval, ingest, etc.).

### A3. Read Core Abstraction Files

For each semantic domain, read the module's `__init__.py` to see its
public API, then the 1-2 core implementation files. Don't try to read
everything — sample strategically across domains.

### A4. Read the Prompt Templates

OpenViking stores all LLM prompts under `prompts/templates/` — these
reveal the LLM usage pattern. Always check if the source project has a
similar `prompts/` directory. The prompts tell you how they think about
the problem.

### A5. Build a Feature Matrix

For each identified feature/concept in the source, create a row:

| Feature | Source approach | Target approach | Gap | Priority | Effort |
|---------|---------------|----------------|-----|----------|--------|

Include both existing Target features that overlap (even partially) and
those that don't exist yet.

### A6. Produce Verdict with Priority

End with a ranked list of "most valuable integrations" — what's worth
building first, and why. Include effort estimates.

## Reference Files

- `references/openhuman-hermes-port-audit.md` — detailed session example
  covering learning/, model_council/, flows/, codegraph/, rhai_workflows/
- `references/openviking-synapse-gap-analysis.md` — architecture-level gap
  analysis: filesystem paradigm, L0/L1/L2 tiering, session extraction ReAct
  loop, YAML memory schemas, training/policy optimization for memory

## Pitfalls

- **Module path isn't where you expect.** The source may use `crates/`,
  `vendor/`, `packages/`, or be flat in `src/`. `search_files` first.
- **`mod.rs` doesn't exist for newer Rust editions.** Rust 2024 allows
  `module.rs` instead. Also check for `lib.rs` in crate roots.
- **README.md describes intent, not reality.** The actual code may be less
  capable or more coupled than the README suggests. Always read source.
- **Don't confuse LOC with difficulty.** A 25KB module that uses only pure
  functions + serde is easier to port than a 5KB module that imports 10
  source-internal traits and a vendor crate.
- **Partial Hermes equivalents aren't substitutes.** Having `search_files`
  (grep) doesn't make `codegraph` (BM25+vector ranking) "already covered" —
  they solve different problems. Be precise about what overlap exists.
- **Vendor crates are the biggest coupling signal.** If a module depends on
  an in-house crate not on crates.io, porting means either bringing that
  crate along or replacing it. Flag these explicitly.
- **Per-module read budget.** Spend no more than 5 minutes per module on
  the initial scan. Go deeper only for modules that pass the first filter.
- **Event bus + approval gate coupling hides everywhere.** Many source modules
  sprinkle event emissions and approval-gate checks throughout their logic.
  These are the hardest couplings to strip.

- **Don't suggest porting security/guardrail features unless the user asks.**
  Users running unrestricted agents explicitly do NOT want content filters,
  safety classifiers, or prompt-injection guardrails bolted on. Recommending
  them wastes effort and frustrates the user. If the source has a security
  module (e.g. prompt_injection, safety_classifier, toxicity_filter), flag it
  in the report but do NOT recommend porting it — and especially do NOT build
  it without explicit instruction. Let the user opt in.

- **For architecture-level analysis, don't try to read every file.** A
  600+ Python file project is too large. Read the `__init__.py` of each
  major subdirectory to understand the public API, then sample 1-2 core
  files per domain. The prompt templates (if any) are often the most
  revealing single source.
