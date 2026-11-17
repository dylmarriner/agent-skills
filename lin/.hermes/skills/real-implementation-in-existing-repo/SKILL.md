---
name: real-implementation-in-existing-repo
description: "Use when replacing stubs or refusals with real code."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [implementation, refactoring, stubs, refusals, testing, verification]
---

# Real Implementation in an Existing Repo

## When to Use

- "Replace the stubs / mocks / placeholders with real implementations"
- "No TODOs, no mock data, no stubs" about an existing project
- "This file does nothing" / a module whose every entry point `raise`s
- implementing an audited gap list inside a codebase you did not write

This is the implementation half of an audit. Reading comes before writing: the fastest
way to ship a confident wrong implementation is to design before checking what the repo
already does.

## Procedure

1. **Locate the true stub set by size and markers, not by docstrings.** A module of a few
   hundred bytes whose body is a two-line comment header is a stub; a module whose every
   entry point `raise`s is a refusal-only shell that may still carry real structure worth
   keeping. Rank candidates by marker count
   (`search_files(pattern='TODO|FIXME|NotImplementedError|placeholder|mock', output_mode='count')`)
   and by line count.
2. **Read the whole unit and its neighbourhood before editing:** the module, the package
   `__init__` that re-exports it, every symbol other modules import from it, and any test
   that asserts its current behaviour. A re-exporting `__init__` means a rename breaks
   importers you never opened.
3. **Find the repo's canonical pattern for that concern and copy its shape.** If a sibling
   module already implements the same contract with a test pinning it (a pluggable
   provider, a typed refusal, a facade over a transport), reuse it instead of inventing a
   second one.
4. **Promote dead code instead of rewriting it.** Code sitting after an early `raise` is
   usually the author's real implementation, kept and disabled deliberately. Moving it
   above the `raise` preserves their domain constants; a from-scratch rewrite quietly
   loses them.
5. **Keep fail-closed only where an input is genuinely unknown, and make it typed and
   named** — say which input is missing and how to supply it (an operator-supplied
   provider, a key, a profile). Fail **before** any side effect: never send a request you
   cannot complete, because on hardware an incomplete exchange can consume a device-side
   attempt or trip a lockout.
6. **Ground every constant in a published spec and reject off-grid values** rather than
   rounding silently. Where a value is not published, take it from the caller instead of
   estimating it. Never invent a magic constant to make a test pass.
7. **Make time and I/O injectable** (clock, sleeper, transport as constructor parameters)
   so timing, retry and lockout logic is testable without real delays.
8. **Verify per module, then prove ownership of failures.** Run the new tests, then the
   neighbours touching the same modules. If untouched modules fail, move your new packages
   aside and re-run: identical failures are pre-existing. Report that per file instead of
   claiming green or blaming your change.
9. **Report as a file list with line counts, the exact test command and pass count, and
   what you deliberately skipped** with the condition for adding it. No narration of the
   process, no design essay.

## Output expectations for this class of work

- Delivered code contains no `TODO`, `FIXME`, `XXX`, `NotImplementedError`, `pass`-only
  bodies, mock data, or placeholder values. "Failing closed with a typed, named error" is
  the one legitimate exception, and only for inputs the code cannot know.
- Terse, result-first report: what changed (paths), how it was verified (command + counts),
  what was left out and when to add it.
- Execute, then report. Do not stop to ask for a decision you can default, and do not
  soften the deliverable to avoid touching unfamiliar code.
- Fix the root cause, not only the reported path: one guard in the shared function beats a
  guard in every caller.

## Pitfalls

- **Scope code searches; never search a repo root blind.** Use `search_files` with an
  explicit path and exclude `node_modules/`, `.git/`, `.venv/`, `dist/`, `archive/`, caches
  and agent/chat-state directories — a root-level recursive search on a real project can
  pull multi-megabyte chat logs into context. Read exact contents with `read_file` and edit
  with `patch`: shell `grep`/`sed` output for matching lines can arrive compressed or
  re-wrapped, so it is not a safe way to read code.
- **Give sibling modules distinct exception names.** Two modules that each define a lockout
  or timeout error collide when the package re-exports both, and a caller (or test)
  importing from the package silently gets the wrong class. Rename one, or import from the
  defining module.
- **Prove a failure is pre-existing before you own it.** Re-running the touched-module
  tests is not enough: a red suite left by someone else's half-finished refactor reads as
  your regression.
- **Do not widen a helper's signature on the first caller you find.** Search every caller
  first; the tests you did not run are the ones that pin the old shape.
- **Write the check with the code.** A branch, loop, parser or money/security path without
  a runnable check is unfinished work, not a saved minute.

`references/implementation-playbook.md` has the classification table, the
provider/typed-refusal skeleton, and the test-scaffold recipes.
