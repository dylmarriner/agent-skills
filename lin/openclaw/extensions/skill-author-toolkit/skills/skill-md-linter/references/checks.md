# SKILL.md lint checks

This file is the canonical list of checks the SKILL.md Linter runs. Each
check has a unique id, a severity (fail or warn), a rationale, and the
exact rule.

## 1. required-fields (fail)

Frontmatter must contain `name` and `description`. Either missing is a fail.

Rationale: ClawHub and OpenClaw both refuse to register a SKILL.md that
lacks these. A skill without a description never appears in search.

## 2. name-kebab-folder-match (fail)

`name` matches `^[a-z][a-z0-9-]*$` and equals the parent folder name.

Rationale: directory naming is how plugins reference skills. A mismatch
breaks installation.

## 3. version-semver (warn)

`version` is present and matches `^\d+\.\d+\.\d+$`.

Rationale: ClawHub orders versions semantically. Non-semver values sort
wrong and confuse update logic.

## 4. license-declared (warn)

`license` field is present in frontmatter (any value).

Rationale: skills without a declared license cannot legally be reused.

## 5. description-length (warn)

`description` length between 200 and 1500 characters.

Rationale: under 200 chars usually means missing trigger phrases. Over
1500 chars usually means the description is doing the body's job and
making the trigger model less precise.

## 6. description-trigger-phrases (warn)

`description` contains at least three quoted phrases (matched by single
or double quotes around 2 to 12 words).

Rationale: the trigger model leans heavily on quoted phrases as exemplars.
Three concrete phrases is the floor for reliable activation.

## 7. permissions-declared (fail when mismatched)

If the SKILL.md body mentions shell execution, file writes, or network
calls, the frontmatter must declare them in a `metadata.permissions`
block (or equivalent named block). Body mentions without a declaration
is a fail; declaration without matching body prose is a warn.

Rationale: ClawHub security reviews flag this directly. Declaring
capabilities makes the skill's reach legible.

## 8. when-not-to-use (warn)

Body or description contains a section, paragraph, or sentence headed or
led by "When NOT to use," "Do NOT trigger on," or equivalent.

Rationale: tight triggers prevent the skill from firing on overlapping
prompts. The explicit not-to-use clause is the single highest-leverage
trigger-quality fix.

## 9. vague-trigger-detection (warn per match)

`description` does not contain trigger phrases from the vague-list:

- "schedule this"
- "help me with"
- "do this for me"
- "run it"
- "make a thing"
- "fix this"
- "what should I do"

Each match is a separate warning.

Rationale: these phrases overlap with most other skills and dilute the
trigger model. Replace with a specific verb plus the skill's domain noun.

---

## Severity reference

- **fail:** the skill will not work correctly or will be rejected by the
  registry. Must fix before publishing.
- **warn:** the skill will work, but the quality is below best practice.
  Recommended to fix.
