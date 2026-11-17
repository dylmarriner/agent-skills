---
name: architecture-to-execution-plan
description: "Transform architecture/design documents into exhaustive, zero-hallucination implementation plans with exact code structures, function signatures, dependency versions, file paths, test stubs, and phase sequencing. Use when the user has design docs and wants an AI-executable implementation plan."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [architecture, implementation, planning, system-design, zero-hallucination]
related_skills: [architecture-to-implementation-plan, writing-plans, subagent-driven-development]
---

# Architecture-to-Execution Plan

## When to Use

Trigger when the user:
- Provides a set of architecture/design documents (documents, markdown files, Notion exports, volume/section structured specs)
- Asks for an "execution-ready implementation plan," "implementation roadmap," "build plan," or "code generation plan"
- Has N separate design docs that need to be synthesized into a single coherent plan
- Says the plan must be detailed enough that "AI agents can't hallucinate or make mistakes"

## Core Principle

A zero-hallucination plan eliminates ambiguity at every level. Every struct field, function signature, dependency version, and file path must be explicitly stated. The implementing agent should never need to invent APIs, guess types, or decide where to put files.

## Process

### Step 0: Check the Existing Project State

Before reading docs, inspect the project root to understand what already exists:

```bash
ls -la /path/to/project-root/
```

Read any existing config files (CLAUDE.md, .cursorrules, .windsurfrules, .mcp.json, .gitignore) to understand:
- Existing project conventions and rules
- Already-established tooling and MCP servers
- Any agent memory or lesson files
- Existing code stubs or scaffolding

This prevents suggesting scaffolding that's already in place and ensures the plan respects existing project rules.

### Step 0: Check the Existing Project State

Before reading docs, inspect the project root to understand what already exists:

```bash
ls -la /path/to/project-root/
```

Read any existing config files (CLAUDE.md, .cursorrules, .windsurfrules, .mcp.json, .gitignore) to understand:
- Existing project conventions and rules
- Already-established tooling and MCP servers
- Any agent memory or lesson files
- Existing code stubs or scaffolding

This prevents suggesting scaffolding that's already in place and ensures the plan respects existing project rules.

### Step 1: Discover and Read All Docs (Parallel Batch Reading)

```bash
# Find all documents
ls /path/to/docs/
```

**Read every doc — batch-read in parallel, 6 at a time.** Do not skip any document — even a short volume may define schemas or constraints used across the system. Every volume may contain cross-references needed in the plan.

Use `read_file` in parallel calls (up to 6 independent reads) to speed up the discovery phase. For 18 docs, this means 3 batches of 6.

As you read each volume, create a mental index of what each doc covers and note:
- Shared schema types (fields, structs, enums) that appear in multiple volumes
- System fabrics or layers referenced across volumes
- Message types, protocols, or data contracts defined in one place but used in others
- Hard constraints / non-negotiable rules scattered across volumes
- Components that depend on other components
- Volume numbering or phase mappings that define implementation order Hard constraints / non-negotiable rules scattered across volumes
- Components that depend on other components
- Volume numbering or phase mappings that define implementation order

### Step 2: Cross-Reference and Map Dependencies

Build a dependency map:
- Which components depend on which?
- What's the implementation order constraint?
- What shared types/schemas cross-cut multiple components?
- Are there "hard constraints" or "non-negotiable rules" sections?

Mapping technique: create a dependency graph either mentally or as a section in the plan. This determines phase ordering.

### Step 3: Determine the Plan's Depth

**Zero-hallucination depth means:**
- Every crate/package has an exact `Cargo.toml` / `package.json` with ALL dependency names and versions pinned
- Every `pub struct` lists EVERY field with its type
- Every `pub fn` has its EXACT signature including return type
- Every `pub enum` has EVERY variant listed
- Every module's `lib.rs` re-exports are shown
- All error types enumerated in a dedicated error module
- File creation order is a strict numbered sequence
- Test stubs with assertions are included per phase
- Configuration files have exact schema (TOML/JSON/YAML with all fields)
- CLI commands have exact clap derive definitions
- Protobuf/IDL messages have exact field numbers

### Step 4: Write the Plan

#### Header
```
# [Project Name] — Execution-Ready Implementation Plan

Generated from analysis of all N design docs.
Total phases: **X**. Estimated to first runnable MVP: **Phase Y**.
```

#### Project Structure (from the monorepo/workspace docs)
Show the exact directory tree with every path. Use a code block with `├──` formatting.

#### Phase 0: Scaffold
First build the skeleton that compiles:
- Workspace Cargo.toml with workspace.dependencies for version pinning
- rust-toolchain.toml
- .gitignore
- Root package.json / pnpm-workspace.yaml if mixed-language
- Proto/IDL directory
- `cargo init --lib` for every crate
- Build script for code generation (prost, tonic, etc.)
- Verification: `cargo build` or equivalent

#### Phases 1..N (ordered by dependency graph)

Each phase follows this template:

```
## Phase N — [Name]

### [Crate/Package Name] Crate

**File:** `exact/path/to/Cargo.toml`

```toml
# Complete Cargo.toml with all dependencies
```

**File:** `exact/path/to/src/lib.rs`

```rust
pub mod module1;
pub mod module2;
pub use module1::*;
```

**File:** `exact/path/to/src/module1.rs`

```rust
// Every struct with every field
pub struct MyStruct {
    pub field1: String,
    pub field2: u64,
}

// Every pub fn with exact signature
pub fn my_function(input: &str) -> Result<Vec<u8>>;
```

**File:** `exact/path/to/src/error.rs`

```rust
#[derive(Error, Debug)]
pub enum Error {
    #[error("Variant description: {0}")]
    Variant(Type),
    // ... every variant
}
```

### Verification (Phase N DONE)

```bash
# Exact commands to verify
cargo test -p crate-name
# Expected: specific output
```

Include test code blocks:

```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_specific_behavior() {
        // exact assertions
    }
}
```

#### Phase N+1: Integration (when combining phases)

```bash
# Script that runs the full integration test
```

### File Creation Order

A strict numbered list of every file to create, in sequence:

```
Phase 0:
  1. /path/to/Cargo.toml
  2. /path/to/rust-toolchain.toml

Phase 1:
  3. /path/to/crate/Cargo.toml
  ...
```

### Hard Constraints Checklist

Use a markdown checklist with the project's non-negotiable rules:

```
- [ ] No central orchestrator
- [ ] Eventual consistency only
- [ ] Cost-aware execution mandatory
- [ ] ...
```

## Reference Files

This skill has a reference file showing a real zero-hallucination plan for a multi-crate distributed system:

- `references/scos-zero-hallucination-example.md` — SCOS v2 plan (106 KB, 12 phases, 67 files) as a worked example of every pattern below in practice. Read this before writing a new plan to internalize the depth required.

## Format Rules

1. **Every file reference** uses the absolute path: `/home/lin/Documents/Project/path/to/file.rs`
2. **Every code block** uses the correct language tag for syntax highlighting
3. **Every dependency** is version-pinned via workspace
4. **Every function** that can fail returns a `Result<T>` with the project's Error type
5. **Every test** includes the expected assertion with an explanation
6. **Every verification step** has an expected output description
7. **Phase titles** start with `## Phase N —` for consistent readability
8. **Sub-phase crate titles** use `### [crate-name]` for hierarchy
9. **Integration line count**: the plan should be 100-200KB for a project with 10+ crates

## Required Sections (Beyond Basic Phase Structure)

### Error Handling Contract

Every plan must include a dedicated Error Handling Contract that states:

```
## ERROR HANDLING CONTRACT

Every `pub fn` that can fail MUST return `scos_common::Result<T>`, not `anyhow::Result<T>`, not unwrap/expect, not panic. The only exceptions:
- `main()` in CLI binary — returns `anyhow::Result<()>`
- Pure data transformations that cannot fail
- Test functions — may unwrap
```

This prevents the implementing agent from picking different error patterns per file.

### Serialization Contract

State the wire format explicitly so no guessing happens:

```
## SERIALIZATION CONTRACT

All wire-format messages (NetworkMessage + variants) use `serde_json`. 
Protobuf (`prost`) is generated from `proto/scos.proto` for forward compatibility.
The primary message exchange format for MVP is JSON over GossipSub.
```

### Hard Constraints Checklist

Extract every non-negotiable rule from the design docs and format as a markdown checklist. Place this both at the top of the plan and repeated in the integration phase:

```
## HARD CONSTRAINT CHECKLIST

Copy this into your AI agent's instructions verbatim:

- [ ] No fixed central orchestrator — every node can be originator, orchestrator, or worker
- [ ] Eventual consistency only — no strong consistency guarantees
- [ ] Cost-aware execution mandatory — every execution must consider token budget
- [ ] No mocked swarm behavior in production paths
- [ ] No LLM call where deterministic code can solve the task
- [ ] No memory write without provenance
- [ ] No task execution without trace ID
...
```

### File Creation Order

Provide a strict numbered sequence of every file across ALL phases. This prevents implementing agents from jumping ahead or creating files out of dependency order:

```
## FILE CREATION ORDER (Strict Sequence)

Phase 0:
  1. Cargo.toml (workspace)
  2. rust-toolchain.toml
  3. .gitignore
  4. proto/scos.proto
  5. All crate stubs via cargo init

Phase 1:
  6. crates/scos-common/Cargo.toml
  7. crates/scos-common/src/error.rs
  ...

Phase N:
  67. ...
```

### Model Provider / Configuration Defaults

If the system uses external services (LLM providers, API keys, config files), include a factory defaults section with the exact initialization code:

```rust
## MODEL PROVIDER COST DEFAULTS

impl Default for ModelRegistry {
    fn default() -> Self {
        let mut reg = Self::new();
        reg.register_many(vec![
            ModelCapability {
                model_name: "deepseek-v4-flash".into(),
                tier: ModelTier::Small,
                context_window: 128000,
                cost_per_1k_input: 0.0003,
                cost_per_1k_output: 0.0006,
            },
            ...
        ]);
        reg
    }
}
```

### Critical Dependency Graph

After listing all phases, add a visual dependency graph showing which components depend on which. This prevents the implementing agent from attempting work in the wrong order:

```

scos-common  ← scos-security
     ↓
scos-network  ← scos-security, scos-common
     ↓
scos-kernel  ← scos-network, scos-security, scos-common
     ↓
apps/cli     ← scos-kernel
     ↓
scos-executor ← scos-kernel, scos-common
     ↓
scos-memory  ← scos-common, scos-kernel
scos-routing ← scos-common, scos-kernel
scos-tools   ← scos-common, scos-security
     ↓
apps/desktop ← scos-kernel (Tauri)
apps/android ← scos-kernel (UniFFI)
scos-observability ← everything
```

### Configuration File Default Schemas

For every config file the system needs, provide the default content with all fields:

```
## NODE CONFIG (config.toml)

```toml
[node]
name = "scos-node"
data_dir = "~/.scos"

[network]
listen_addrs = ["/ip4/0.0.0.0/udp/9090/quic-v1"]
topic = "scos-swarm"
...
```

### CLI Command Definitions

For CLI tools, include exact clap derive macros:

```
## CLI COMMANDS

#[derive(Parser)]
enum Commands {
    Init { name: String },
    Start { config: String },
    Task {
        #[command(subcommand)]
        action: TaskCommand,
    },
}
```

Include CLI commands verbatim as the docs specify them:

```bash
scos node init
scos node start
scos node status
scos peers list
scos task submit <prompt>
```

### Protobuf / IDL Contract

For systems with protobuf, include the full .proto file content in the plan, not just a reference to write it:

```
## PROTOBUF CONTRACT (proto/scos.proto)

```protobuf
syntax = "proto3";
package scos;

message CognitiveTransaction {
  string transaction_id = 1;
  ...
}
```

### Integration Milestone (First Runnable)

After the core phases, include a dedicated "Integration MVP" section that:

1. Wires together all prior phases into a single testable scenario
2. Includes a shell script the implementing agent can run
3. Lists the exact expected output per step
4. Has a "Definition of Done" checklist from the project's own docs

```bash
chmod +x tests/two_node_mvp.sh
./tests/two_node_mvp.sh
# Expected output:
#   [OK] root — [simulated] ...
#   [OK] worker-1 — [simulated] ...
```

### Post-MVP Phases

For phases that come after the first runnable milestone, keep them in the plan but at **lower resolution** — the user needs to see the full roadmap, but the detail belongs on the near-term phases. A post-MVP phase should have:

- **Objective** — one-line goal
- **Key crate/component** — what gets built
- **Dependencies** — what must be in place first
- **Outcome** — how it extends the MVP

Do not include function signatures, field definitions, or test stubs for post-MVP phases — those would be guesswork until the MVP is built and validated.om the project's own docs

```bash
chmod +x tests/two_node_mvp.sh
./tests/two_node_mvp.sh
# Expected output:
#   [OK] root — [simulated] ...
#   [OK] worker-1 — [simulated] ...
```

### Post-MVP Phases

For phases that come after the first runnable milestone, keep them in the plan but at **lower resolution** — the user needs to see the full roadmap, but the detail belongs on the near-term phases. A post-MVP phase should have:

- **Objective** — one-line goal
- **Key crate/component** — what gets built
- **Dependencies** — what must be in place first
- **Outcome** — how it extends the MVP

Do not include function signatures, field definitions, or test stubs for post-MVP phases — those would be guesswork until the MVP is built and validated.
```

## Pitfalls

- Don't write high-level pseudocode — write EXACT code that compiles
- Don't say "add validation" — write the validation function verbatim
- Don't say "error handling" — enumerate every error variant
- Don't say "implement DAG validation" — write Kahn's algorithm inline verbatim so the implementing agent copies it directly
- Don't say "implement contextual bandit" — write the LinUCB math with Gaussian elimination inline
- Don't say "implement CRDT merge" — write the merge function with exact semantics (LWW, updated_at comparison, etc.)
- Don't say "add election scoring" — write the exact weight formula with coefficients
- Don't guess dependency versions — pin them all in workspace.dependencies
- Don't skip test stubs — every phase must have at least a compilation test
- Don't use placeholder function bodies — write the actual algorithm or mark clearly where it's a placeholder "TBD: integrate with X in Phase Y"
- Don't skip the workspace root Cargo.toml — it's the foundation everything depends on
- Don't put everything in one module — show the module separation via lib.rs re-exports
- Don't start with a small plan and iterate — when the user provides 10+ architecture docs, go straight to the 100-200KB zero-hallucination depth. The user expects a comprehensive first pass, not a draft. Iterating from a thin plan wastes a round-trip while the user tells you what they already specified in their design docs.
- Don't read docs one at a time — batch-read 6 in parallel per read_file call. For 18 docs, use 3 parallel batches to minimize round-trips.
- Don't add YAGNI modules/crates not in the design docs — stick to what the architecture specifies
- Don't use anyhow::Result in library code — use the project's custom Error type
- Don't skip serialization derives — every struct that goes on the wire needs Serialize/Deserialize
- Don't write module-level structure as prose ("the module contains types and functions") — show the actual `pub mod` and `pub use` re-export lines
- Don't leave config file schemas unspecified — write the default TOML/JSON content verbatim so no format guessing happens
- Don't omit the Error enum — write every variant with its error message template and source type
- Don't skip the existing project state check — read CLAUDE.md, .cursorrules, .gitignore first to avoid suggesting scaffolding that's already in place
