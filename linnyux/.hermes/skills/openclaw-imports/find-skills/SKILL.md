---
name: find-skills
description: Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express interest in extending capabilities. This skill should be used when the user is looking for functionality that might exist as an installable skill.
tags: [skills, discover, install, ecosystem]
related_skills: [skills-cli]
---

# Find Skills

This skill helps you discover and install skills from the open agent skills ecosystem.

## When to Use This Skill

Use this skill when the user:

- Asks "how do I do X" where X might be a common task with an existing skill
- Says "find a skill for X" or "is there a skill for X"
- Asks "can you do X" where X is a specialized capability
- Expresses interest in extending agent capabilities
- Wants to search for tools, templates, or workflows
- Mentions they wish they had help with a specific domain (design, testing, deployment, etc.)

## What is the Skills CLI?

The Skills CLI (`npx skills` / `bunx skills`) is the package manager for the open agent skills ecosystem. Skills are modular packages that extend agent capabilities with specialized knowledge, workflows, and tools.

> **NOTE**: This skill overlaps with `skills-cli`, which has the complete reference and the latest CLI syntax. Load `skills-cli` for installation details, flags, and troubleshooting. This skill focuses on the DISCOVERY flow — finding and evaluating skills.

**Key commands:**

- `npx skills find [query]` — Search for skills interactively or by keyword
- `npx skills add <package> --skill <name>` — Install a specific skill from a package
- `npx skills check` — Check for skill updates
- `npx skills update` — Update all installed skills

**Browse skills at:** https://skills.sh/

## ⚠️ Cross-Ecosystem Search: Search ALL Available Ecosystems

**CRITICAL**: The user expects you to search ALL available skill ecosystems, not just one. Searching only skills.sh and assuming that's exhaustive will miss skills from ClawHub and Hermes. Always search all three ecosystems in parallel.

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Search ALL Three Ecosystems in Parallel

**Do not search ecosystems sequentially** — run all searches together to avoid the user having to ask "did you check X too?"

#### Ecosystem A: skills.sh (largest ecosystem)

```bash
# Search via CLI — run multiple related queries to cover the space
npx skills find <query>
```

Example: for security investigation skills, search `osint`, `forensics`, `reconnaissance`, `shodan`, `breach`, `dark web` — don't stop at one result.

Also check the [skills.sh leaderboard](https://skills.sh/) for top skills in the domain.

#### Ecosystem B: ClawHub (if `clawhub` CLI is available)

```bash
# Search ClawHub registry
clawhub search <query>

# Install from ClawHub
clawhub install <slug> --no-input
```

If `clawhub` is not available, note in the response that ClawHub was not searched — don't silently skip it.

#### Ecosystem C: Hermes (local skills)

```bash
# List all categories
skills_list

# Check specific categories for relevant skills
skills_list --category <category>
```

Also inspect already-installed openclaw-imports at `~/.hermes/skills/openclaw-imports/` and locally-installed skills.sh skills at `~/.agents/skills/`.

### Step 3: Cross-Ecosystem Summary

After searching all three, present a combined summary organized by category, noting which ecosystem each result came from. The user shouldn't have to piece together results across ecosystems themselves.

### Step 4: Verify Quality Before Recommending

**Do not recommend a skill based solely on search results.** Always verify:

1. **Install count** — Prefer skills with 1K+ installs. Be cautious with anything under 100.
2. **Source reputation** — Official sources (`vercel-labs`, `anthropics`, `microsoft`) are more trustworthy than unknown authors.
3. **GitHub stars** — Check the source repository. A skill from a repo with <100 stars should be treated with skepticism.

### Step 5: Present Options to the User

When you find relevant skills, present them to the user with:

1. The skill name and what it does
2. The install count and source
3. The install command they can run
4. A link to learn more at skills.sh

Example response:

```
I found a skill that might help! The "react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.
(185K installs)

To install it:
npx skills add vercel-labs/agent-skills --skill react-best-practices

Learn more: https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### Step 6: Offer to Install

If the user wants to proceed, you can install the skill for them:

```bash
npx skills add <source> --skill <name> -g -y
```

The `-g` flag installs globally (user-level) and `-y` skips confirmation prompts.

**IMPORTANT**: Use `--skill <name>` syntax. The old `owner/repo@skill-name` syntax (`@`-separated) is deprecated and does not work with the current CLI version.

## Common Skill Categories

When searching, consider these common categories:

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility     |
| Productivity    | workflow, automation, git                |

## Tips for Effective Searches

1. **Use specific keywords**: "react testing" is better than just "testing"
2. **Try alternative terms**: If "deploy" doesn't work, try "deployment" or "ci-cd"
3. **Check popular sources**: Many skills come from `vercel-labs/agent-skills` or `ComposioHQ/awesome-claude-skills`

## When No Skills Are Found

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities
3. Suggest the user could create their own skill with `npx skills init`

Example:

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, you could create your own skill:
npx skills init my-xyz-skill
```
