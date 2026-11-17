---
name: pm-data-hygiene
description: Audit or improve project-tracker data before planning, forecasting, reporting, or AI automation. Use for ambiguous tickets, missing ownership, stale statuses, inconsistent units, duplicate work, or weak acceptance criteria.
---

# Project data hygiene

Inspect the tracker schema and team conventions before imposing new fields. Preserve source records and stable identifiers; never bulk-delete or silently rewrite project history to improve a dashboard.

1. Select the relevant project population and record the query, observation time, and item count. Distinguish absent data from valid zero, false, or empty values.
2. Check only fields needed for the intended decision: outcome, accountable owner, workflow status, dependency links, acceptance evidence, and relevant dates or estimates. Verify timestamp zones and estimation units.
3. Classify defects separately: missing, invalid, stale, contradictory, and suspected duplicate. A matching title is not proof of a duplicate. Keep a sample of concrete record IDs for every finding.
4. Rewrite unclear work into an observable outcome with acceptance criteria that can fail. Use Given/When/Then when it clarifies behavior; do not invent requirements, dates, owners, or estimates.
5. Apply authorized corrections narrowly. For bulk updates, prepare a change preview and a recovery path, preserve original values, and verify both affected and unaffected records. Keep changes as proposals if write authorization is absent.

Deliver defect counts with denominators, representative evidence, corrected drafts or applied changes, and remaining owner decisions. Validate readiness against the original planning or reporting use case rather than an arbitrary completeness percentage.

Conceptual inspiration: [Skillbook Academy's project-manager competencies](https://skillbookacademy.com/resources/ai-powered-project-manager-skills/). Independently authored; not an official Skillbook package.
