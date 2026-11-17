---
name: skill-md-linter
description: "Lint a SKILL.md file (or a folder of skills) against best practices learned from real ClawHub security reviews. Use this skill when the user wants to check a SKILL.md before publishing or after a review finding. Signals include 'lint my skill,' 'check my SKILL.md,' 'audit this skill before I publish,' 'is my description too vague,' 'review my frontmatter,' or 'will this skill pass ClawHub security scan.' Runs nine concrete checks: required frontmatter fields, name kebab-case matching folder, semver version, license declared, description length, three or more quoted trigger phrases, declared permissions block, presence of a when-NOT-to-use clause, and vague-trigger detection. Outputs a report card with pass/warn/fail per check and concrete suggested fixes drawn from a curated set of before/after snippets. Do NOT trigger on generic markdown-quality questions unrelated to SKILL.md, on skills already published that the user has no intent to change, or on plugin-level validation (this skill only checks individual SKILL.md files)."
license: "MIT"
metadata:
  permissions:
    files:
      read: ["<target SKILL.md path>", "<target skill or skills directory>"]
      write: []
    shell: false
    network: false
---

# SKILL.md Linter

Most ClawHub security review findings boil down to the same handful of issues: descriptions that fire too broadly, missing when-NOT-to-use clauses, undeclared permissions. This linter runs those checks before you publish so the review does not catch them.

## What this skill does

Take one of three inputs:

- A single SKILL.md file (lint just that file).
- A skill folder (lint the SKILL.md inside, plus check that any referenced `references/` files exist).
- A parent folder of skills (lint every SKILL.md found and produce a multi-skill report).

Run the nine checks defined in `references/checks.md`, then produce a report card.

## Checks (summary)

1. **required-fields.** Frontmatter must contain `name` and `description`.
2. **name-kebab-folder-match.** `name` matches `[a-z][a-z0-9-]*` and equals the parent folder name.
3. **version-semver.** `version` is present and matches `\d+\.\d+\.\d+`.
4. **license-declared.** `license` field is present in frontmatter.
5. **description-length.** Between 200 and 1500 characters.
6. **description-trigger-phrases.** Description contains at least three quoted phrases.
7. **permissions-declared.** If body mentions shell, file writes, or network, frontmatter declares them.
8. **when-not-to-use.** Body or description contains a when-NOT-to-use clause.
9. **vague-trigger-detection.** Description does not contain known vague phrases ("schedule this," "help me with," etc.).

Full rationale and detection logic for each check lives in `references/checks.md`. Concrete before/after fix snippets live in `references/fix-examples.md`.

## How to run it

1. Identify the target. If the user names a path, use it. Otherwise, ask: "Lint a specific SKILL.md, a skill folder, or a directory of skills?"
2. Read the SKILL.md and parse the YAML frontmatter.
3. Run each check against the parsed content. Record `pass`, `warn`, or `fail` per check with a short message.
4. For any `warn` or `fail`, pull the matching example from `references/fix-examples.md` and include the relevant before/after snippet inline in the report.
5. Output a report card.

## Output structure

```
# SKILL.md Lint Report: [skill name]

## Summary
- Passes: 7
- Warnings: 1
- Failures: 1

## Details

### FAIL: vague-trigger-detection
The description contains "schedule this" and "help me," which overlap broadly with other skills.

Suggested fix:
[before/after snippet from fix-examples.md]

### WARN: description-length
Description is 1612 chars (recommended max 1500). Consider tightening.

### All other checks passed.
```

If linting a directory, group findings by skill and add a top-line count: "8 skills checked, 6 clean, 2 with warnings, 0 failing."

## Style

- Lead with what failed, then what warned, then a clean note for what passed.
- Never restate the original frontmatter back to the user; they wrote it.
- Suggested fixes are concrete: paste the exact text to replace.

## When NOT to use

- Generic "is my markdown well-formatted" questions: this skill is SKILL.md-specific.
- Skills already published that the user has no intent to change.
- Plugin-level validation: this skill only checks individual SKILL.md files.
