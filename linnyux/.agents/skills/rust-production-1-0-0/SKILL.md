---
name: rust-production-1-0-0
slug: rust-production
version: 1.0.0
homepage: https://windsurf.local/skills/rust-production
description: Enforces strict production-grade Rust output with no stubs, placeholders, mock code, TODOs, or FIXMEs.
metadata: {"windsurf":{"emoji":"🦀","requires":{"bins":[]},"os":["linux","darwin","win32"]}}
---

## When to Use

Activate this skill whenever Rust code is requested.

Triggers include:
- writing Rust code
- refactoring Rust code
- debugging Rust code
- designing Rust architecture
- implementing Rust APIs, services, CLIs, libraries, or tools

Do not use when:
- another programming language is requested
- pseudocode or teaching stubs are explicitly requested

---

## Scope

This skill enforces **strict production Rust output**.

It guarantees that the assistant:

- writes complete Rust implementations
- outputs compile-ready code
- uses idiomatic stable Rust
- never produces scaffolding disguised as real code

---

## Hard Prohibitions

The following must **never appear** in generated Rust code:

- `todo!()`
- `unimplemented!()`
- placeholder `panic!()`
- mock logic in production code
- placeholder returns
- dummy data
- TODO comments
- FIXME comments
- XXX markers
- placeholder comments
- simplified demo logic when real code is expected

If something cannot be implemented fully, the missing external dependency must be explained instead of faked.

## Failure Rule

If a fully correct implementation cannot be completed because required external facts are missing, do not invent them.

State exactly what is missing, such as:
- API schema
- database schema
- authentication contract
- wire format
- file layout
- environment variables
- protocol details

Then implement every remaining part fully and correctly without placeholders.

---

## Implementation Requirements

All Rust output must:

1. Compile in a realistic Rust project.
2. Include all required:
   - imports
   - structs
   - enums
   - traits
   - impl blocks
   - helper functions
3. Provide real logic in every function.
4. Use proper error handling.
5. Maintain correct ownership and borrowing semantics.

---

## Rust Standards

Default behavior:

- stable Rust
- safe Rust preferred
- explicit types where useful
- correct lifetimes
- no unnecessary clones or allocations
- idiomatic patterns

Crates should only be used when appropriate.

Examples:
- `thiserror`
- `anyhow`
- `serde`
- `tokio`
- `reqwest`
- `sqlx`
- `tracing`

---

## Error Handling Rules

Errors must be deliberate.

Prefer:

- domain error enums
- `thiserror`
- `Result<T, E>`
- clear failure modes

Avoid:

- stringly typed errors
- silent failures
- swallowed errors

---

## Completeness Rule

Every function must contain real behavior.

Forbidden:

- empty bodies
- placeholder branches
- incomplete match statements
- partial module trees

---

## Tests

When tests are included they must:

- compile
- exercise real behavior
- not be placeholders
- not be trivial assertions

---

## Execution Model

When responding to a Rust request:

1. Determine artifact structure
   - binary
   - library
   - CLI
   - service
   - crate module tree

2. Identify required implementation surfaces
   - data structures
   - traits
   - IO boundaries
   - configuration
   - error types

3. Implement full code paths.

4. Verify internally:
   - no stubs
   - no placeholders
   - compile plausibility
   - error completeness

5. Output complete code.

## Compiler Simulation Rule

Before emitting any Rust code, perform an internal compiler-style validation pass.

The assistant must internally check:

### Parse Validation
- syntax is plausibly valid Rust
- braces, generics, trait bounds, and lifetimes are structurally consistent
- imports match referenced symbols

### Type Validation
- function signatures align with call sites
- return types match actual returned values
- trait impl method signatures match trait definitions
- ownership and borrowing rules are respected
- async usage is consistent with awaited values and runtime assumptions

### Module Validation
- referenced modules, types, and functions exist
- visibility is consistent with usage
- file layout is coherent if multiple files are emitted

### Error Path Validation
- every fallible path returns or propagates errors correctly
- no hidden placeholder branches remain
- no impossible type coercions are assumed

### Dependency Validation
- external crates used in code are declared explicitly
- crate features are named when materially required
- APIs used are plausible for current stable Rust ecosystem patterns

### Production Validation
- no `todo!()`
- no `unimplemented!()`
- no placeholder `panic!()`
- no fake values
- no mock production paths
- no TODO, FIXME, XXX, HACK, or placeholder comments

If any validation step fails, revise the implementation before responding.
Do not mention this validation pass unless explicitly asked.

---

## Output Format

Prefer explicit file layout when needed.

Example:

```
Cargo.toml
src/main.rs
src/lib.rs
src/error.rs
src/config.rs
tests/integration.rs
```

Primary deliverable is **code**.

Explanations should remain concise.

---

## Quality Standard

Generated Rust must resemble code written by a **senior Rust systems engineer preparing for real production use**.

It must never resemble tutorial scaffolding or partial implementations.

---

## Rust Output Gate

No Rust output may be emitted until the assistant can internally answer YES to all of the following:

- Would this plausibly compile on stable Rust?
- Does every function contain real logic?
- Are all referenced symbols defined and imported?
- Are all fallible paths handled deliberately?
- Are dependencies declared explicitly?
- Are placeholders completely absent?

If any answer is NO, revise before output.

---

## Enforcement Checklist

Before finalizing Rust output verify:

- every function has real logic
- no placeholder markers exist
- code compiles plausibly
- dependencies are declared
- error handling is correct
- external boundaries are honest

If any condition fails, revise before responding.
