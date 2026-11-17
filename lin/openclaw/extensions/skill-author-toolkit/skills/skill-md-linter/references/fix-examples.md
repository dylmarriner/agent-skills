# Before/after fixes for common lint findings

Use these as templates when surfacing a fix to the user. Each section
matches one check from `checks.md`. Adapt the wording to the actual
content; never paste verbatim if it would override the user's voice.

## description-length (too long, > 1500 chars)

**Before:** A multi-paragraph description that explains what the skill
does, why it exists, who built it, when to use it, when not to use it,
and a list of twenty trigger phrases.

**After:** A 600 to 1000 character description that contains:

- one sentence on what the skill does,
- one sentence on the user signal that should fire it,
- three to seven quoted trigger phrases,
- one sentence on what NOT to fire it on.

## description-trigger-phrases (under 3 quoted phrases)

**Before:**

> "Audit your skills and tell you what is wrong."

**After:**

> "Audit installed skills. Use this skill whenever the user wants to
> review, debug, or clean up their installed skills, including phrases
> like 'why did the wrong skill fire,' 'audit my skill library,' or
> 'do any of my skills conflict.'"

## permissions-declared (mismatch)

**Before:** Body mentions reading and writing files, but frontmatter
has no permissions block.

**After:** Add a permissions block to frontmatter that lists what the
skill actually touches:

```yaml
metadata:
  permissions:
    files:
      read: ["~/.skill-doctor/cache"]
      write: ["~/.skill-doctor/cache"]
    shell: false
    network: false
```

## when-not-to-use (missing)

**Before:** Skill description lists what triggers it, but never says
when it should stand down.

**After:** Add a clause to the description and a body section:

> "Do NOT trigger on [overlapping scenario], on [too-broad scenario], or
> on [adjacent-but-different scenario]."

Body section heading: `## When NOT to use` with a bulleted list of 2 to 4
specific exclusions.

## vague-trigger-detection (per match)

**Before:**

> "Use this skill when the user says 'schedule this' or 'help me with
> follow-ups.'"

**After:**

> "Use this skill when the user says 'set up a reliable nightly backup,'
> 'monitor my scheduled jobs for silent failure,' or 'help me catch a
> cron job that silently stopped.'"

Rule: replace generic verbs with specific verb-plus-domain-noun phrases.
"Help me with X" becomes "help me catch X" or "help me set up X."
