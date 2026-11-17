---
name: architecture-to-implementation-plan
description: Analyze multi-volume architecture/design documents and produce an execution-ready implementation plan with phased ordering, dependency graphs, and file manifests.
---

# Architecture Docs → Implementation Plan

## When To Use

The user asks you to analyze a set of architecture, design, or specification documents (often numbered volumes, chapters, or sections) and produce an implementation plan. Typical triggers:

- "analyse all N docs and make an execution ready implementation plan"
- "turn these specs into a build plan"
- "read the volumes and give me a phased roadmap"
- "synthesize these design docs into something actionable"

## Process

### Step 1: Discover and Read Everything

Use `read_file` to batch-read all documents in parallel (6 at a time). Do not skip any document — every volume may contain cross-references needed in the plan.

First run `ls` or `search_files(target='files')` on the doc directory to discover the full set.

### Step 2: Cross-Reference for Shared Concepts

As you read each volume, note:
- Shared schema types (fields, structs, enums) that appear in multiple volumes
- System fabrics or layers referenced across volumes
- Message types, protocols, or data contracts defined in one place but used in others
- Hard constraints / non-negotiable rules scattered across volumes
- Components that depend on other components

### Step 3: Check the Existing Project State

Run `ls -la` on the project root to see what already exists (configs, CLAUDE.md, .cursorrules, existing code stubs). This prevents suggesting scaffolding that's already in place.

Read any `.cursorrules`, `.windsurfrules`, `CLAUDE.md`, or `.mcp.json` to understand tooling and conventions already established.

### Step 4: Build the Dependency Graph

Order the implementation phases by dependency:

```
Leaf dependencies (no deps on other project crates) → depends on leaf → depends on that → etc.
```

Example ordering rule: `scos-common → scos-security → scos-network → scos-kernel → scos-executor → apps/cli`

The first runnable integration milestone comes when the critical path through the dependency graph is complete.

### Step 5: Produce the Phased Plan

Write the plan as a file (e.g., `EXECUTION-PLAN.md`) in the project root. Structure:

1. **Project structure** — the monorepo / crate / app layout from the architecture docs
2. **Phase N sections** — each phase with concrete files to create, struct signatures, commands, and verification
3. **A "First Runnable" milestone** — the earliest point two things talk to each other
4. **Dependency graph** — visual tree showing what depends on what
5. **File manifest** — table of every file to create, organized by phase
6. **Hard constraints checklist** — the non-negotiable rules extracted from the docs
7. **Post-MVP roadmap** — what comes after the first runnable milestone

### Step 6: Post-MVP Phases

For phases beyond the first runnable milestone, keep them in the plan but at lower resolution — the user needs to see the full map but the detail belongs on the near-term phases.

## Output Format

Each phase entry should specify:

- **Objective** — one-line goal
- **Steps** — numbered concrete actions (file creates, cargo commands, test commands)
- **Key structs / types** — Rust struct signatures or TypeScript interfaces with exact field names from the doc schemas
- **Dependencies** — what must be built first
- **Verification** — how to confirm this phase is done (`cargo test`, `cargo run -- node start`, two-node test)

## Example CLI Commands to Include

If the docs specify CLI commands, include them verbatim in the plan:

```bash
scos node init
scos node start
scos node status
scos peers list
scos task submit <prompt>
```

## Pitfalls

- **Don't skip any doc.** Even a short volume may define schemas used across the system.
- **Don't invent schemas that aren't in the docs.** Use field names verbatim from the design docs.
- **Don't produce a flat list of tasks.** The plan must have phased ordering that respects the dependency graph.
- **Don't forget the file manifest.** A table of every file and its action (Create/Patch) is critical for execution.
- **Don't skip the project directory check.** You'll propose files that already exist if you don't check the actual state.
- **Don't mock network behavior in production paths.** If the docs say "no mocked peer discovery", include that in the hard constraints list.
