---
name: production-code-standards
description: Production code quality rules — zero stubs, zero placeholders, zero mock data. Every function does real work or fails meaningfully. Use when generating, reviewing, or refactoring any code for this user.
---

# Production Code Standards

**Applied when generating any code for this user.** They enforce this strictly — expect corrections if violated.

## Zero Tolerance

- **No stubs.** Every function must be a real working implementation.
- **No placeholders.** No `NotImplementedError`, `TODO`, `FIXME`, `pass` as a body.
- **No mock data.** No hardcoded fake return values like `"MSC001"`, `"VLR001"`, `return True` without doing the actual work.
- **No simplified/simulated implementations** that `log("success")` and `return True` without performing the operation.
- **No "would be implemented here"** comments. Either implement it or restructure it out.

## Every Function Must

1. **Do real work.** Connect to the actual service, parse real responses, compute real results.
2. **Fail meaningfully.** If it can't do the real work, return `Err`/raise with a specific error message — not `Ok` with fake data.
3. **Be verifiable.** Run the code after writing it — import, compile, test, or execute. If it doesn't run, it's not done.

## Exception

Mock data is acceptable ONLY when the user explicitly requests a demo/prototype. Otherwise, implement the real thing.

## Working Style

- **Build, don't audit.** When given a problem, build the tool immediately and run it on real data. Do not produce defensive analysis reports.
- **Extend, don't rewrite.** Prefer adding functionality to existing working scripts/configs rather than replacing them. 'Wouldn't you just add some extra tools' is the right instinct.
- **Act, don't narrate.** When the user's goal is clear, execute. Don't explain what you're about to do, don't ask permission for obvious next steps, don't stop after a plan — keep working until the code runs or the result is delivered.
- **Try everything in parallel.** When there are multiple approaches to try, batch independent reads/searches/commands into the same turn.
