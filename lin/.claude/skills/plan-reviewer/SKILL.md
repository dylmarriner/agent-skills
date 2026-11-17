---
name: plan-reviewer
description: Use when creating, refining, or reviewing implementation plans, migration plans, refactoring proposals, feature plans, implementation trackers, or committable phase plans; especially when turning a rough plan into executable phases or checking whether a plan is concrete, testable, safe, dependency-aware, and suitable for parallel work.
---

# Plan Reviewer

## Core principle

Make plans executable and use review as a quality gate before implementation. Find ambiguity, unsupported assumptions, unsafe sequencing, missing validation, untracked work, and coordination hazards before implementation starts.

Do not implement code while preparing or reviewing a plan. Inspect files only when needed to verify plan claims.

## Workflows

Choose the workflow from the user's request:

- **Prepare or refine**: Convert rough notes or an existing plan into actionable, independently committable phases. Unless the user requests inline output or names a destination, write the result to a new Markdown file with a clear topic-based filename. Never overwrite an existing file without asking.
- **Review**: Evaluate an existing plan without editing it. Use the scorecard and verdict workflow below.

If the request is ambiguous and an existing plan is provided, default to review. Do not silently rewrite a plan presented for review.

## Plan types

Classify the plan before preparing or judging it:

- **Execution plan**: Must be concrete enough to implement and commit from directly.
- **Design plan**: May be higher level, but must clearly state unresolved decisions and evidence.
- **Discovery plan**: May contain open questions, but must define what will be learned and how.
- **Migration or operations plan**: Must include rollback, verification, safety checks, and failure handling.

Hold execution plans to the strictest standard. Do not reject an early design plan just because it lacks implementation-level detail. Instead, say what is missing before it can become execution-ready.

## What to verify

### 1. Evidence and references

- Verify referenced files exist when codebase access is available.
- Verify referenced functions, classes, commands, configs, migrations, routes, jobs, and tests are real.
- Treat file:line citations as helpful but not required. Line numbers get stale.
- Require evidence for codebase-specific claims. Accept file paths, symbols, tests, configs, docs, logs, or stable line references.
- If evidence cannot be verified, mark the claim as unverified rather than treating it as true.

### 2. Trackability and phase structure

For implementation trackers, check that:

- Work is split into independently reviewable, committable phases.
- Phase tasks use Markdown checkboxes when the plan is meant to track progress.
- Each phase has a clear objective, dependencies, acceptance criteria, validation steps, and a suggested commit message.
- Phase order follows dependency order.
- Each phase is small enough to review without hiding unrelated changes.
- Refactoring, behavior changes, tests, migrations, and rollout work are not mixed unless the plan explains why.

### 3. Parallelism and coordination

For every execution-ready plan:

- Identify phases or tasks that can safely run concurrently after their prerequisites complete.
- State the critical path and any required integration or merge order.
- Treat shared files, symbols, contracts, migrations, fixtures, infrastructure, and persisted state as potential conflicts.
- Give each parallel workstream a clear scope and expected output so it could be delegated to a subagent without duplicate investigation.
- Do not force parallelism. State `No safe parallelism identified` when sequencing is safer.

Identify opportunities only. Do not launch subagents unless the user asks.

### 4. Testability and acceptance criteria

Acceptance criteria should be objective. Flag criteria that depend on vague human judgment.

Good criteria specify:

- Inputs or setup.
- Expected output or observable behavior.
- Verification method, such as a test command, lint command, type check, manual command, screenshot, API response, or database query.
- Error cases and edge cases where relevant.

Reject wording like "works correctly" unless the plan defines exactly what correct behavior means.

### 5. Specificity

Flag vague language when it hides implementation decisions. Common red flags:

- properly
- correctly
- appropriately
- as needed
- etc.
- and so on
- various
- some
- improve
- enhance
- optimize
- clean up

These terms are acceptable only when followed by measurable detail.

### 6. Dependencies, risks, and safety

Check whether the plan identifies:

- Dependencies between phases.
- External systems or data sources outside the codebase.
- Required credentials, services, migrations, feature flags, queues, cron schedules, or background jobs.
- Rollback or recovery steps for migrations, production config, data mutation, auth, billing, or reliability changes.
- Observability and incident-response implications when behavior affects production operations.

## Plan preparation process

1. Read all supplied material and classify the plan type.
2. Verify codebase-specific claims and flag unresolved requirements or blockers.
3. Split the work into dependency-ordered, independently reviewable phases.
4. For each phase, include an objective, Markdown task checkboxes, dependencies, acceptance criteria, validation steps, and a suggested commit message.
5. Add a `Parallel execution` section naming concurrent workstreams, prerequisites, coordination points, and the critical path. State when no safe parallelism exists.
6. Check the finished plan against the review criteria before presenting it.

## Review process

1. State the plan being reviewed and the plan type.
2. Read the whole plan before judging individual sections.
3. Verify file references and codebase claims with tools when available.
4. Produce a scorecard.
5. List blocking issues first, then non-blocking improvements.
6. Give one verdict: `APPROVED`, `REVISE`, or `REJECT`.
7. If the verdict is `REVISE`, ask whether the user wants the plan updated. Do not edit the plan until the user confirms.

## Scorecard format

Use this table in every review:

```markdown
## Scorecard

| Area | Result | Notes |
|------|--------|-------|
| Scope and intent | Pass/Revise/Fail | ... |
| Evidence and references | Pass/Revise/Fail | ... |
| Trackability and phase structure | Pass/Revise/Fail | ... |
| Parallelism and coordination | Pass/Revise/Fail | ... |
| Acceptance criteria and tests | Pass/Revise/Fail | ... |
| Dependencies and sequencing | Pass/Revise/Fail | ... |
| Risks, rollback, and operations | Pass/Revise/Fail | ... |
| Specificity | Pass/Revise/Fail | ... |
```

## Verdicts

### APPROVED

Use only when the plan is ready to execute for its stated plan type.

```markdown
VERDICT: APPROVED

The plan is ready for execution.

## Why it passes
- ...

## Verified references
- ...

## Watch points
- ...
```

### REVISE

Use when the plan is directionally sound but needs fixes before execution.

```markdown
VERDICT: REVISE

The plan needs corrections before execution.

## Blocking issues
1. ...

## Minimum changes required for approval
- ...

## Non-blocking improvements
- ...

## Unverified claims
- ...

Would you like me to update the plan file with these fixes?
```

### REJECT

Use when the approach is fundamentally unsafe, unsupported, or too incomplete to revise directly.

```markdown
VERDICT: REJECT

This plan should not be executed as written.

## Fundamental problems
1. ...

## Recommendation
- ...
```

## Optional plan update workflow

Only update a plan after a `REVISE` verdict and explicit user confirmation.

When updating:

- Preserve the plan's intent and structure where possible.
- Fix every blocking issue you identified or clearly mark it as an open question.
- Prefer targeted edits over rewriting the entire file.
- Do not overwrite or replace the plan in place unless the user asked for in-place updates.
- If the user wants a separate revision, create a new Markdown file with a clear name.
- Add an `Issues Found in Review` section only when it helps future readers understand what changed.

After updating, summarize the changed file path, key fixes, and any remaining open questions.

## Common mistakes

- Approving a plan because the idea is good while the execution details are vague.
- Demanding file:line citations for every statement in an early design plan.
- Trusting file references without checking that they exist.
- Treating a checklist as sufficient when dependencies and validation are missing.
- Calling work parallelizable without checking shared files, contracts, or state.
- Forcing parallel work when coordination would cost more than sequencing.
- Editing a plan before the user confirms they want changes.
- Implementing code while reviewing the plan.
