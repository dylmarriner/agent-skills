---
name: blueprint-audit-rollout
description: Audit a codebase against a technical blueprint/spec, then implement ALL remaining gaps simultaneously with production-grade code only (no mocks, stubs, fixmes, todos, or placeholders). Verified end-to-end.
metadata:
  author: Macuntu
  version: 1.0.0
  category: software-development
---

# Blueprint Audit Rollout

Use this skill when you have an existing project with a technical blueprint or specification document, and the user wants everything implemented — no partial passes, no placeholders, production-grade only.

## Core pattern

1. Load the spec/blueprint
2. Audit current implementation against it
3. Identify all gaps across ALL phases/areas
4. Implement every gap in a single session with production-grade code
5. Verify with type-check and build
6. Report completion

## Prerequisites

- A technical blueprint, PRD, or specification document exists in the project
- The project has an existing codebase to audit against
- The user has explicitly (or implied) that they want everything done

## Steps

### 1. Load and understand the spec

Read the full specification document. Identify:
- All phases/areas of work
- Every individual feature or component listed
- Acceptance criteria for each
- Dependencies between work items

### 2. Audit current state

For every item in the spec, check if it exists in the codebase:
- Is the component/file present? Check the filesystem.
- Is it complete or just a stub/placeholder? Read the content.
- Does it integrate properly? Check imports, registrations, route handlers.
- Does it use mock data or real production code?

Categorize each item as: **implemented**, **partial/stub**, or **missing**.

### 3. Create a unified implementation plan

Group all gaps into a single work order. Consider:
- **Dependencies first** — collections before API routes before components
- **Parallel where possible** — independent features can be built simultaneously
- **Production-grade only** — every file must be complete, no FIXMEs, no TODOs, no placeholder text, no simplified/mock implementations

Track progress with `todo` — create one item per feature area.

### 4. Implementation rules

Every file you create or modify must be **production-grade**:
- Real error handling (try/catch, proper error boundaries)
- Real loading states (skeletons, spinners, not "TODO: loading")
- Real data from the actual API/collection, not mock/test data
- Proper TypeScript types throughout
- No `// TODO: fix later` or `// FIXME: implement`
- No stub functions that throw "not implemented"
- Accessibility attributes (aria-labels, roles, semantic HTML where applicable)
- Responsive design (mobile-first when applicable)
- Proper import paths and module integration

### 5. Verify

After implementing everything:
1. Run `npx tsc --noEmit` (or equivalent type checker) — fix any errors
2. Run `npm run build` or `next build` — fix any build errors
3. If applicable, run lint — fix any warnings
4. If the user expects browser testing, verify in a clean session

Do not stop at the first error. Fix everything and keep going.

### 6. Communication

- Do NOT report intermediate status per feature
- Do NOT describe each file you create
- Do NOT ask for permission between steps
- Final message: summary table of what was implemented per spec area, verification result, and any remaining work (true blockers only)

## Pitfalls to avoid

- **Stubs leak into production** — the "I'll come back and fix this later" trap. Every file must be complete before the session ends.
- **Mock data in components** — components should use real API calls or real collection data, not hardcoded sample data.
- **Missing imports/registrations** — a component file is not done until it's wired into the actual page or route.
- **Context window death** — with 25+ files and multiple feature areas, context compaction will happen. Be ready for it — use `todo` to track progress, and re-read work from previous turns via `session_search` if needed.
- **Build breaks from forgotten exports** — always run the type checker at the end, not during (that's chatter).
- **Assuming a file name means it's done** — always read the actual file content when auditing. A component file with just "export default function Foo() { return null }" is a stub.

## When to use

- User says "implement everything" referring to a spec/blueprint
- User says "no mocks no stubs no fixmes no todos no placeholders"
- User gives you a roadmap doc and says "build it all"
- You've audited a project and found many gaps — the playbook says to fill them all at once
