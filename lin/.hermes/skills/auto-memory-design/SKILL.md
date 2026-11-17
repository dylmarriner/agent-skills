---
name: auto-memory-design
description: Analyze a specific agent's actual memory gaps and produce a testable AutoMemory design using the reference hub.
---

# AutoMemory Design

Read **the full** `/home/lin/.hermes/automemory/commands/auto-memory-design.md` and follow its design protocol, replacing its `@Auto_Memory/` notation with `/home/lin/.hermes/automemory/`.

- Confirm target repository and existing persistence and context/injection mechanisms.
- For Hermes on Lin: source `/home/lin/.hermes/hermes-agent`; config `/home/lin/.hermes/config.yaml`; existing OptMem provider plus SCOS MCP bridge must remain operational.
- Use `ask_ref ls`, `ask_ref grep "<memory problem>"` and `ask_ref cat <technique-id>`.
- Baseline recall and write-path behaviour, observe slowdowns and missing cases before designing modifications.
- Write the design and worktraces per upstream instructions in a separate approved workspace/branch; never overwrite current memory files.
- Report measured gaps, schema, dedup, retrieval, failure cases and explicit integration/test plan.
- Stop after design. Don't implement or replace the production provider until the design is reviewed.
