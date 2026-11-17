---
name: auto-memory-implement
description: Implement an accepted AutoMemory design with tests and a reversible adapter in an isolated agent worktree.
---

# AutoMemory Implement

Read **the full** `/home/lin/.hermes/automemory/commands/auto-memory-implement.md` and follow its prerequisites, steps and artefact contracts.

- Require the completed, accepted `memory_design.md` and `worktraces/note.md`.
- Develop in a dedicated worktree. Record a baseline with failing tests before writing production logic, then make them pass.
- For Lin's Hermes, preserve existing OptMem, SCOS and all local changes. Integrate via an opt-in adapter or lifecycle hook; do **not** displace existing memory wiring or alter global configuration without explicit owner approval.
- Avoid duplicate writes, recursive retrieval, unbounded token injection and writeback of secrets. Add safeguards and rollback.
- Produce implementation docs, tests and refine state exactly as specified upstream.
- Run focused and existing regression tests and report results accurately.
