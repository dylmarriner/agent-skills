---
name: swarm
description: Use a high-rigor swarm-style workflow with parallel exploration, implementation, independent review, and critic validation for substantial coding tasks.
---

# Swarm Workflow (Cline adaptation)

This skill is adapted from ZaxbyHub/opencode-swarm's `.opencode/skills/swarm/SKILL.md` and `.agents/skills/swarm/SKILL.md`. It is a workflow posture only: do not invoke OpenCode slash commands or assume the OpenCode plugin is installed.

## Use when

- The user explicitly asks for swarm mode, team mode, parallel investigation, or unusually high review rigor.
- A substantial task spans multiple modules or has meaningful security, safety, migration, or correctness risk.

## Procedure

1. **Scope and plan.** Establish task boundaries, constraints, current worktree state, and concrete validation gates. Preserve the plan in task artifacts when multi-step.
2. **Explore in parallel.** Split independent read-only exploration across teammates where available. Ask for findings and evidence, not speculative edits.
3. **Implement in bounded slices.** Assign disjoint implementation tasks only after interfaces and ownership are clear. Avoid concurrent edits to the same files.
4. **Validate objectively.** Run relevant tests, static checks, builds, and inspect the final diff. Record exact commands and outcomes. Tests do not substitute for hardware or production validation.
5. **Independent review.** Have a separate teammate review the actual latest diff for defects, safety/security issues, and mismatches between claims and behavior. If delegation is unavailable, state the limitation and perform a self-review without representing it as independent approval.
6. **Critic challenge.** Obtain a separate skeptical review of high-impact findings and the final evidence. Do not mark done while blockers remain.
7. **Close out.** Summarize changes, validation results, risks, and remaining work. Do not edit after review gates unless the changed diff is reviewed again.

## Principles

- Evidence and correctness outrank speed or dispatch count.
- Keep candidate generation separate from validation when practical.
- Use parallelism for independent work only; avoid duplicate or conflicting edits.
- Do not overstate test evidence, supported scope, or reviewer independence.
- Keep the user informed during longer work and stop for missing safety-critical inputs.