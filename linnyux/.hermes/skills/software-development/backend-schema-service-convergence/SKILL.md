---
name: backend-schema-service-convergence
description: Diagnose and fix backend compile failures caused by Prisma/schema drift between services, controllers, tests, and the active schema. Use when TypeScript errors point to missing models, fields, enums, or relation shapes and the right fix is to reconcile source-of-truth schema vs service expectations.
---

# Backend Schema/Service Convergence

Use this skill when a backend codebase has widespread TypeScript errors that look like Prisma drift: missing model delegates, missing fields, enum mismatches, relation shape mismatches, or tests built against stale user fixtures.

## When to use
- `tsc` reports many errors across controllers/services after schema work
- Prisma client types do not match service expectations
- Services reference models/fields that are absent from `schema.prisma`
- Generated enum exports differ from local type wrappers
- Tests fail because fixtures no longer match required shape

## Core approach
1. Treat the TypeScript error output as the roadmap.
2. Classify errors into buckets:
   - missing model delegate
   - missing scalar field
   - missing enum member
   - relation/include mismatch
   - stale test fixture / mock shape
   - stale utility import from Prisma generated types
3. Inspect the active Prisma schema first, then inspect any reference or complete schema only as a comparison aid.
4. Decide per domain whether the canonical fix is:
   - expand the Prisma schema to match the implemented service layer, or
   - refactor the service layer down to the existing canonical schema.
5. Prefer fixing the source of truth rather than layering ad hoc casts or `any`.

## Recommended workflow
### 1) Capture the exact failures
- Run `npx tsc --noEmit --esModuleInterop --skipLibCheck` in the backend package.
- If the backend package does not have a local TypeScript binary, fall back to the workspace/root invocation that actually resolves the compiler, for example `npx --prefix .. tsc --noEmit --esModuleInterop --skipLibCheck` from the backend directory.
- If `npx tsc` prints the npm "This is not the tsc command you are looking for" banner, it is resolving the wrong package context; switch to the workspace-root invocation immediately instead of debugging TypeScript itself.
- If the checked-in schema already contains a field or model but TypeScript still reports it as missing, suspect stale generated Prisma client output, wrong package resolution, or an unrefreshed import path before expanding the schema again.
- If Prisma-related errors appear to contradict the checked-in `schema.prisma`, confirm whether the generated Prisma client has been regenerated before expanding the schema further.
- When the error wall is broad, reduce it to the smallest set of root causes by grouping errors into: schema missing field, schema missing model, schema missing enum member, stale client generation, stale test fixture, or stale controller/service import.
- If a service is still referencing fields like `price`, `lastLoginAt`, or `blockedByProvider` after the active schema has been verified smaller, prefer refactoring the service to the canonical schema rather than repeatedly expanding the schema in response to each compile error.
- If necessary, run the test suite to surface additional type/runtime drift.
- Group repeated errors by model/domain before editing.

### 2) Audit schema shape
- Read `prisma/schema.prisma` for the affected models and enums.
- Check whether the active schema intentionally omits fields the services depend on.
- Compare against reference or complete schemas only as an aid, not as the source of truth.
- When the active schema already contains a field but TypeScript still complains it is missing, suspect stale generated client output, wrong package resolution, or an unrefreshed type import path before modifying the schema again.

### 2) Audit schema shape
- Read `prisma/schema.prisma` for the affected models and enums.
- Check whether the active schema intentionally omits fields the services depend on.
- Look for legacy or reference schemas only to understand intended structure.

### 3) Fix the highest-leverage drift first
- Add missing scalar fields that are clearly part of the domain model and already used throughout the codebase.
- Align enum definitions in shared local type files when generated Prisma exports are unavailable or stale.
- Add missing relations/models only when the service layer clearly depends on them.
- Update tests and fixtures to include newly required required fields.

### 4) Avoid partial bandaids
- Do not leave production `TODO`, `FIXME`, mock data, or placeholder stubs.
- Do not silence type errors with broad casts unless you have proven the mismatch is temporary and isolated.
- Do not patch a single line if the error pattern shows a systemic schema mismatch.

### 5) Regenerate and re-verify
- After schema changes, regenerate the Prisma client if the project uses codegen.
- Re-run `tsc` and the relevant tests.
- Keep iterating until the errors collapse to zero or a true external blocker remains.

## Practical heuristics
- If many services fail on the same missing field, the schema is probably behind the service layer.
- If a generated Prisma enum import is missing, prefer a local shared enum file only when the schema/client regeneration path is unreliable or unavailable.
- If only one service uses a missing field and the schema clearly excludes it, refactor that service to the canonical schema instead of expanding the schema blindly.
- If tests are failing on object literals, update fixtures to reflect required fields and relation shapes.

## Verification checklist
- `npx tsc --noEmit --esModuleInterop --skipLibCheck` passes
- targeted tests for touched domains pass
- Prisma client is regenerated if schema changed
- no new `any`-based escape hatches were introduced
- service logic, schema, and tests agree on the same domain shape

## Pitfalls
- Expanding the schema in one place without checking all consumers can create new errors elsewhere.
- Generated enum names may not match older handwritten wrappers.
- A single domain mismatch can fan out into dozens of TypeScript errors; fix the root, not every symptom.
- Missing relation includes often masquerade as simple property access errors.

## Example trigger
- "Backend has a huge Prisma/TypeScript error wall after schema changes"
- "Services reference payment/referral/notification models that the active Prisma schema doesn’t expose"
- "Need to reconcile a codebase where the schema is smaller than the implemented domain logic"
