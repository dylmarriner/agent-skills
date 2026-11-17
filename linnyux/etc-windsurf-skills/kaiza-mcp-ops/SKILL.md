---
name: kaiza-mcp-ops
description: Operate Windsurf against ATLAS-GATE-MCP with plan selection, signature-based authority, and audit trails. Invoke as @kaiza-mcp-ops.
---

# Skill: ATLAS-GATE MCP Operations

## Purpose
Ensure all code modifications are made within approved ATLAS-GATE plans, executed through ATLAS-GATE-MCP tools, and auditable.

## When to Use This Skill
- Starting any coding task (feature, bug fix, refactoring, release)
- When ATLAS-GATE-MCP is available in the environment
- Before reading or writing files

## Steps

### 1) ATLAS-GATE preflight
- Call `begin_session` first with the absolute workspace root
- Call `list_plans` to see approved plans for this workspace
- Select the plan signature that matches the scope of your task

If no matching plan exists:
- Stop and ask ANTIGRAVITY to produce and approve a plan via `lint_plan` / `save_plan`
- Do not proceed until the signed plan exists

### 2) Understand plan boundaries
Each plan has:
- **scope_and_constraints**: What files/modules it covers and what constraints apply
- **path_allowlist**: Which paths may be changed
- **phase_definitions**: Which operations are allowed and what must be verified
- **verification_gates**: What checks must pass

Example ATLAS-GATE plan fields:
```
plan_metadata.plan_id: "IMPLEMENT_FEATURE_X"
atlas_gate_plan_signature: "<signed plan signature>"
path_allowlist: ["src/features/x", "tests/features/x", "docs/features/x"]
verification_gates: ["npm test", "npm run lint"]
```

### 3) Read files using ATLAS-GATE
Use ATLAS-GATE `read_file` for reads.
This ensures:
- Reads are tracked for audit
- Permissions are checked against the plan
- Context is loaded into the MCP session

### 4) Write files with provenance metadata
For every file write using ATLAS-GATE `write_file`, include:
- **plan**: The approved plan signature
- **role**: executable | boundary | library | infra | test | docs
- **intent**: Summary of the write intent

Optional metadata may still include purpose/usedBy/connectedVia/executedVia/failureModes/authority when your integration consumes them.

Example write invocation metadata:
```
plan: "<atlas_gate_plan_signature>"
role: "boundary"
intent: "Implement HTTP handler for feature X endpoints"
```

### 5) Run verification gates after every change
After each write:
```bash
npm test
npm run lint
npm run typecheck
python scripts/ci/forbidden_markers_scan.py --root .
```

If any gate fails, stop and fix before continuing.

### 6) Produce an audit summary
After all changes are complete, produce a machine-checkable audit summary:

```
ATLAS-GATE-AUDIT
Plan Signature: <atlas_gate_plan_signature>
Scope: src/features/x/handler.js, src/features/x/model.js, tests/features/x.test.js
Intent: Add HTTP API for feature X with structured logging and input validation
Key Decisions:
  - Used Express middleware for input validation (familiar, proven)
  - Stored feature X in new module to avoid tight coupling
  - Added correlation ID propagation for observability
Verification:
  - npm test: PASS (all tests pass, +3 new test cases)
  - npm run lint: PASS
  - npm run typecheck: PASS
  - forbidden_markers_scan.py: PASS
  - Coverage: 92% for feature X module (target: >80%)
Results: All gates pass. Code is ready for review.
Risk Notes: Feature X depends on external service Y; timeouts configured to 5s
Rollback: Revert commits or feature-flag can disable feature X via ENV var
ATLAS-GATE-AUDIT-END
```

### 7) Embed ATLAS-GATE-AUDIT in PR description
If using GitHub/GitLab:
- Paste the ATLAS-GATE-AUDIT block into the PR description
- CI will validate it has all required fields
- Reviewers use it to understand the scope and safety checks

## Quality Checklist

- [ ] Approved ATLAS-GATE plan signature selected (or requested via ANTIGRAVITY)
- [ ] `begin_session` called first
- [ ] All reads use ATLAS-GATE `read_file`
- [ ] All writes use ATLAS-GATE `write_file` with plan signature + intent
- [ ] All verification gates pass after each change
- [ ] ATLAS-GATE-AUDIT block is produced with all required fields
- [ ] Plan scope is respected (no out-of-scope changes)
- [ ] Risk level is appropriate for the change
- [ ] Authority rules are referenced in ATLAS-GATE-AUDIT

## Verification Commands

```bash
# Check that plans can be listed through ATLAS-GATE-MCP
# (invoke via your MCP client/runtime)

# Verify ATLAS-GATE-AUDIT format (locally)
grep -A 8 "^ATLAS-GATE-AUDIT$" PR_DESCRIPTION.md | grep -E "Plan Signature:|Scope:|Intent:|Key Decisions:|Verification:|Results:|Risk Notes:|Rollback:"
```

## How to Recover if Plan Boundary is Breached

If you realize you've made changes outside the plan scope:
1. Revert the out-of-scope changes
2. Propose a new or amended plan
3. Wait for approval
4. Resume the task with the updated plan

If a verification gate fails:
1. Stop and fix the issue
2. Re-run the gate
3. Continue only after gate passes

## ATLAS-GATE Audit Compliance

Every task using this skill must produce an ATLAS-GATE-AUDIT block with:
- **Plan Signature**: Approved plan signature
- **Scope**: Files/modules touched
- **Intent**: What outcome is delivered
- **Key Decisions**: Why these choices
- **Verification**: Exact commands executed and results
- **Results**: Pass/fail with artifacts
- **Risk Notes**: Remaining risks + mitigations
- **Rollback**: How to revert safely
