# Multi-Repo Fork Comparison Pattern (Worked Example)

## Context

This user had three copies of the same project on disk: two distinct GitHub repos (different casing) and one stale clone. The user's correction: "the 2 of them here /media/kubuntux/DEVELOPMENT1/"

## The Discovery Command Sequence

```bash
# 1. List all projects on the primary dev drive
ls /media/kubuntux/DEVELOPMENT1/

# Output shows TWO matching directories:
# automation-suite/       (lowercase)
# Automation-suite/       (capitalized)

# 2. Check git remotes to determine if they're the same or different repos
cd /media/kubuntux/DEVELOPMENT1/automation-suite && git remote -v
# -> github.com/dylanmarriner/automation-suite.git  (DIFFERENT repo)

cd /media/kubuntux/DEVELOPMENT1/Automation-suite && git remote -v
# -> github.com/dylanmarriner/Automation-suite.git  (DIFFERENT repo)

# 3. Check git histories for divergence
cd /media/kubuntux/DEVELOPMENT1/automation-suite && git log --oneline -30
# -> 9 commits, latest: "fix: eliminate all security vulnerabilities"

cd /media/kubuntux/DEVELOPMENT1/Automation-suite && git log --oneline -30
# -> 18 commits, latest: "docs: final status - 100% blueprint compliance"
# The capitalized one has TWICE the commits and more recent work.

# 4. Compare package counts
echo "Lowercase packages:" && ls /media/kubuntux/DEVELOPMENT1/automation-suite/packages/ | wc -l
# 27 packages
echo "Capitalized packages:" && ls /media/kubuntux/DEVELOPMENT1/Automation-suite/packages/ | wc -l
# 30 packages (3 more: integrations, products, queues)

# 5. Look for audit/signal files
ls /media/kubuntux/DEVELOPMENT1/automation-suite/AUDIT.md 2>/dev/null
# NOT FOUND — this copy was never audited

ls /media/kubuntux/DEVELOPMENT1/Automation-suite/AUDIT.md 2>/dev/null
# FOUND — 595-line audit with 39 defects catalogued
ls /media/kubuntux/DEVELOPMENT1/Automation-suite/EXECUTION_PLAN.md 2>/dev/null
# FOUND — 645-line multi-phase fix plan
ls /media/kubuntux/DEVELOPMENT1/Automation-suite/BLUEPRINT_COMPLIANCE_COMPLETE.md 2>/dev/null
# FOUND — claims 100% blueprint compliance
```

## Key Heuristics

| Heuristic | Signal |
|-----------|--------|
| More git commits | Likely the active fork |
| Has AUDIT.md | Actively being evaluated/shipped |
| Has EXECUTION_PLAN.md | Known defects with a plan to fix |
| Has BLUEPRINT_COMPLIANCE_*.md | Infrastructure alignment done |
| More packages | Extended/stabilized fork |
| paperclip/ directory | Was recently worked on by an agent |
| Newer lock/pnpm-lock date | More recently installed |
| .env / .env.example with real configs | Closer to production readiness |

## Relationship Classification

- **Fork (diverged):** Same origin project, different GitHub repos, different histories. One may be a superset with fixes.
- **Clone (same remote):** Worktrees or copies of the same repo. Check `git log` dates — one may be stale.
- **Superset:** Same codebase but one has more packages, fix commits, and audit docs. This is the canonical one.

## Reporting Language

Use clear framing:

> "The capitalized `Automation-suite` is the canonical fork — it has N more commits, M more packages, and comprehensive audit docs. The lowercase `automation-suite` is the pre-alignment original. Copy C is a stale clone of the capitalized one."
