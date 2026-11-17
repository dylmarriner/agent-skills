---
name: paperclip-auth-path-troubleshooting
description: Debug and fix Paperclip auth/permission issues where resumed board/CEO sessions lose board context, fall back to unauthorized actors, or get blocked on company/task endpoints.
---

# Paperclip Auth Path Troubleshooting

Use this when a resumed CEO/board workflow hits 401 Unauthorized or 403 Board access required on company-scoped or task-scoped endpoints.

## Core idea
In authenticated deployments, the absence of a bearer token does not mean the request is unauthenticated. The server may need to resolve the Better Auth session, map it back to a board actor, and preserve company membership and run context before company/task authorization runs.

## Workflow

### 1) Trace the live actor path
Inspect the actual request pipeline:
- request headers
- session resolution (`resolveSession` / Better Auth)
- actor middleware normalization
- company access checks (`assertCompanyAccess`)
- task permission checks (`tasks:assign`, checkout ownership, etc.)

The key question: did the request become `actor.type === "board"` before the route checked permissions?

### 2) Distinguish board session vs board API key
A resumed board user may arrive in one of two valid forms:
- session-backed board actor
- board-key-backed board actor

If a user session exists, resolve it first. If the user also has an active board API key, preserve that identity when needed by downstream code.

### 3) Preserve company and run context
When normalizing the actor, keep:
- `userId`
- `companyIds` from memberships
- `isInstanceAdmin`
- `keyId` if a board API key exists
- `runId` from `X-Paperclip-Run-Id` for mutating flows and checkout ownership

Missing run context can surface later as task/session errors even if auth succeeded.

### 4) Verify the exact failure path
Before changing route guards, reproduce with a request that includes:
- authenticated board session cookies or headers
- no bearer token
- a company-scoped endpoint
- a task-scoped endpoint

Confirm whether the failure is:
- no session resolution
- session resolved but actor stayed `none`
- actor became `board` but company membership was missing
- actor became `board` but a later permission check expected board-key context or runId

### 5) Patch the smallest root cause
Prefer fixing actor normalization in middleware or shared auth helpers over loosening route guards.
Common fix pattern:
- add a helper that resolves a board actor from session
- include board API key lookup by user id if needed
- keep existing bearer-token path unchanged
- do not special-case route guards unless the route is genuinely wrong

### 6) Add regression coverage
Add tests for the specific auth branch you fixed:
- authenticated session without bearer token
- board/company access succeeds
- task endpoint with `X-Paperclip-Run-Id` still passes ownership checks
- routes still reject non-board actors and cross-company agent access

## Common pitfalls
- Treating missing `Authorization` as automatic unauthenticated access
- Resolving the session but forgetting to promote it to a board actor
- Dropping `companyIds`, which causes false 403s on company routes
- Dropping `runId`, which breaks resumed task execution and checkout ownership
- Fixing route guards instead of the actor source of truth
- Forgetting to verify with a real endpoint or request-level test

## Verification checklist
- resumed CEO/board session reaches `actor.type === "board"`
- company-scoped endpoints return 200
- task-scoped endpoints return 200 when permissions are valid
- cross-company access is still rejected
- regression tests cover the exact auth path
