---
name: repo-canon-audit
description: Audit a repository against its roadmap, blueprint, canon docs, and UI/spec artifacts to identify drift, conflicts, and missing implementation scope.
metadata:
  category: software-development
---

# Repo Canon Audit

Use this skill when the user asks to audit a repository against a roadmap, blueprint, canon, UI plan, or similar source-of-truth documents.

## Goal

Determine whether the repository’s active docs, UI specs, and implementation state match the current canon, and identify:
- aligned items
- conflicts / drift
- legacy or archival-only material
- missing implementation scope
- ambiguous decisions that need freezing

## Workflow

1. Find the authoritative documents first.
   - Search for roadmap, blueprint, canon, decisions, implementation state, and UI/spec docs.
   - If names are unclear, search for likely terms and inspect file locations.
   - Prefer canonical docs over historical raw-sync or transcript dumps.

2. Establish document hierarchy before judging content.
   - Identify which file is the current source of truth.
   - Treat roadmap/plans as subordinate if a blueprint or canon doc says so.
   - Treat raw-sync and historical consolidation docs as reference material unless explicitly promoted.

3. Read the highest-priority canon docs in full enough to extract:
   - product objective
   - hard constraints
   - architecture/stack
   - core flows
   - explicitly rejected ideas
   - performance and UX requirements

4. Inspect the actual app shell and route/navigation structure early.
   - Confirm whether the implementation already exposes the canonical navigation surface.
   - Check which screens are wired to each tab/route, not just which screen files exist.
   - Verify whether legacy screen names are aliases for canonical surfaces or truly outdated concepts.
   - Also inspect root layout/theme injection files; shared CSS/layout drift often hides even when individual pages look aligned.

5. Compare the repo against the canon in these buckets:
   - navigation / IA
   - UI surfaces and interactions
   - stack / architecture / data model
   - performance constraints
   - terminology and naming
   - phased roadmap sequencing
   - rejected features that still appear in specs
   - active UI screen copy and branding, not just markdown docs
   - legacy vs active wording in screens, not only markdown files
   - shared source-of-truth drift (duplicate registries, duplicated theme tokens, parallel package APIs)

   If a canonical UI/spec file is broader than the locked blueprint, rewrite that file down to the approved surface instead of trying to preserve brainstormed extras.

   If governance docs conflict with the blueprint, explicitly mark them legacy/subordinate and align the hierarchy in the doc itself.

   If the repo has mobile/web screens or generated UI text, search them explicitly for legacy product names, dashboard-first framing, template-like UI wording, and other canon-breaking copy before concluding the audit.

   If you discover duplicate implementations of the same authority (for example, two product registries or two theme sources), collapse them onto one canonical package/API before making surface-level UI judgments.

   When the repo includes implementation-status or completion-summary docs, treat them as claims to verify, not evidence. Cross-check them against a canonical gap map or requirement checklist and prefer the most specific source that enumerates missing/partial/blocking items over broad "complete" narratives.

6. Classify findings clearly.
   - Aligned
   - Conflicting
   - Missing
   - Ambiguous / needs decision
   - Historical only / archive-worthy
   - Copy drift
   - Flow drift
   - Stack drift
   - Backend scope drift
   - Source-of-truth split

7. Prioritize the report.
   - Start with the most canon-breaking drift.
   - Call out any docs that appear broader than the locked blueprint.
   - Note when older roadmap assumptions conflict with newer canon.
   - Separate product-surface drift from platform/secondary-tool drift.
   - Prefer fixes that restore a single source of truth over repeated per-page edits.

8. Convert findings into an implementation plan when asked.
   - Order phases by highest user-visible drift first.
   - Use the sequence: shared source-of-truth consolidation → mobile/web shell and core flows → backend support surfaces → stack convergence → docs/governance cleanup.
   - Include explicit verification gates and stop points.
   - Call out blocked validation if dependencies or installs are missing.

9. If asked to continue into fixes, propose concrete file-level patch targets.
   - Prefer one canonical source to reduce drift.
   - Recommend archiving or narrowing legacy docs rather than letting them compete with canon.
   - After patching, re-scan the exact affected surfaces to confirm the drift is actually gone.

## Important rules

- Do not assume the first roadmap you find is still current.
- Do not treat historical sync docs as canon unless a newer doc promotes them.
- If a blueprint explicitly says another doc is subordinate, obey that hierarchy.
- Separate "implementation drift" from "documentation drift."
- If search results are sparse, widen the search by directory and keyword before concluding a file is missing.
- Do not assume the project is at the current working directory. Check `lsblk`, `/mnt/`, `/media/`, and common development roots if the user says it's on a "separate drive" or gives an unfamiliar path.
- When a canonical registry exists (products/modules/bundles), treat it as the source of truth for all public indexes, detail pages, entitlement mapping, and nav labels.
- If legacy branded landing pages duplicate canonical registry entries, convert the legacy pages into redirects or thin wrappers instead of leaving competing implementations live.
- When verifying route coverage, search for lingering legacy imports/copy patterns (for example package-specific product content modules) as well as the canonical registry helpers; both can reveal drift.
- In Next.js repo audits, inspect root layouts for duplicated inline theme blobs or CDN CSS before judging page-level UI alignment; theme drift often lives in app shells, not components.
- When a dev server appears to disagree with on-disk changes, clear stale build artifacts and re-check the live browser before editing further; cached bundles can mimic code drift.
- For data-heavy admin surfaces, label safe no-DB fallback shells clearly during verification, but do not mistake them for the final production-grade data-backed implementation.
- If the repo has an obvious control-plane app, separate “shell alignment” from “operational data wiring” in the audit report so the remaining gap is explicit.

## Phase-completion / release-gate verification

When the user asks to check if a project is "complete" according to its roadmap/blueprint, treat this as a **release gate audit** — a stricter subset of canon audit where the source of truth is a concrete checklist (e.g. a Phase N release-readiness doc or exit-gates checklist).

### Workflow differences from drift audit

1. **Find the gate doc first, not the overview.**
   - Look for files named `*RELEASE_READINESS*`, `*PHASE_N_*`, `*EXIT_GATES*`, `*CHECKLIST*`.
   - The README or current-status doc will typically point to the authoritative gate doc.
   - Read the entry conditions, exact checklist, and exit conditions verbatim — these are your test oracle.

2. **Build a pass/fail matrix.**
   - For every line item in the gate checklist, verify one by one.
   - Distinguish THREE states: ✅ (passes), ❌ (fails), 🟡 (untested / partial / long-running).
   - Do not infer passing from structural presence — e.g. a file existing doesn't mean its content is complete per the spec.

3. **Verify the build and tests rigorously.**
   - `cargo build --workspace --release` (zero warnings) — count warnings with `grep -c "^warning:"`.
   - `cargo test --workspace` — but watch for two blind spots:
     - **Ignored tests** (`#[ignore]` — need `-- --ignored` to run). Explicitly check for them and note what they cover.
     - **Long-running tests** (compliance, integration, multi-millennia sims). If they timeout in a normal run, flag them as untested blockers, not passing.
   - Grep for `TODO`, `FIXME`, `HACK`, `XXX` in source code.
   - Check hardcoded filesystem paths in tests — they can break when the repo is mounted at a different location (e.g. `/mnt/` vs `/media/`).

4. **Check ignored/skipped scope explicitly.**
   - `grep -rn "ignore" --include="*.rs" tests/` to find gate tests the user may not have run.
   - If important tests are `#[ignore]`d, call these out as unknowns, not passes.

5. **Verify naming conventions and invariants.**
   - Grep the *release* docs and *source code* (not just roadmap/plan docs) for forbidden patterns defined in the blueprint.
   - False positive trap: plan/roadmap docs often *discuss* forbidden patterns. Exclude `docs/roadmap/`, `docs/plans/`, `.atlas-gate/` from the violation grep so you only catch actual violations.

6. **When docs/gates list the same file in multiple places, check all paths.**
   - A file might exist but be empty, a stub, or point to a different mount location than expected.
   - Verify content completeness (file size > 10 bytes, contains real content).

### Checklist categories typical of phase gates

| Category | Example items |
|----------|--------------|
| Compilation | `cargo build --release` succeeds, zero warnings, no TODOs |
| CLI / binary | Binary exists, all documented subcommands parse |
| Documentation | README, ARCHITECTURE, CANON_PROFILE, DETERMINISM_PROOF, ANTI_SAPIENCE, VERIFICATION_REPORTS |
| Artifacts | canon digest, verification reports (100kyr/1myr/10myr), determinism proof |
| Governance | CONTRIBUTING, CODE_OF_CONDUCT, LICENSE |
| Tests | All tests pass including ignored ones, long-running compliance tests |
| Naming | No forbidden term combinations in source or release docs |

## Output format

Use a concise audit report with sections like:

- Overall verdict (phase status badge + summary)
- ✅ Already Complete (checklist items that pass)
- ❌ Still Blocking (checklist items that fail, with specifics)
- 🟡 Partial / Untested (ambiguous items)
- File-level observations
- Recommended next actions (ordered by impact)

When useful, include a table with columns:
- Area
- Canon expectation
- Repo state
- Status
- Suggested action

## Verification

Before finalizing, confirm:
- the authoritative docs were actually read
- conflicting claims were traced to specific files
- historical docs were not mistaken for active canon
- the report reflects the highest-priority source of truth
- live route behavior was physically checked (browser or curl), not inferred from source files alone
- if the dev server appears to serve stale code, restart the running process and re-check the route before changing more code
- when a route reads as fixed on disk but still fails in-browser, inspect the current running process and generated dev artifacts before assuming the file patch is wrong
- for Next.js route work, distinguish between a shell that renders and a data-backed route that still needs runtime configuration; if the environment lacks the required DB/config, use a safe no-DB fallback only for verification, and clearly label it as such

## Common pitfalls

- Auditing only the UI spec and missing the blueprint hierarchy
- Following legacy stack assumptions after the canon changed
- Overlooking archived docs that still contain attractive but rejected ideas
- Mixing implementation progress with product canon
- Fixing visible copy in screens but leaving a broader-than-canon UI spec in place
- When a public product page still exists as a standalone marketing page with legacy product-specific imports, collapse it into the canonical registry-driven surface or redirect it there instead of preserving a parallel implementation
- Forgetting to re-scan after each patch batch and assuming the first fix was enough
