---
name: project-survey-and-orientation
description: Find a project on the filesystem and run a systematic health/state survey — structure, build status, test health, git activity, and docs landscape.
metadata:
  category: software-development
---

# Project Survey & Orientation

Use when the user asks to find a project, check what state it's in, see where things are, or understand an unfamiliar codebase's current health. Also use when you need to orient yourself to a project before making changes.

## Goal

Quickly locate a project on disk and survey it to answer:
- Where is it?
- What tech does it use?
- What is its structure (frontend/backend/monorepo)?
- Does it build? Do tests pass?
- What is the recent commit history?
- What documentation exists?
- What is broken or needs attention?

## Workflow

### Phase 1: Locate the project

**Critical pattern**: Projects are almost always on secondary drives (`/media/kubuntux/DEVELOPMENT*` or similar), not under `/home/`. The home directory may contain stale clones or workspace copies, not the canonical project. Search the user's named development drive FIRST — do not start with `/home`.

1. **When the user names a project, ask yourself: do I know the right location?** If unsure, state which location you're searching. If the user just said the project name without a path, check ALL common locations before concluding.

2. **If the user gives a project name OR mentions a drive (e.g., "DEVELOPMENT1", "development1"), search that specific location first — it is the canonical project location**:
   ```bash
   # If user mentions "DEVELOPMENT1" — this is THE primary drive, search it before /home:
   ls /media/kubuntux/DEVELOPMENT1/ 2>/dev/null                    # list all projects first
   find /media/kubuntux/DEVELOPMENT1 -maxdepth 2 -iname "*project*" 2>/dev/null  # exact name match
   find /media/kubuntux/DEVELOPMENT1 -maxdepth 2 -iname "*foo*bar*" 2>/dev/null   # fuzzy name
   ```

3. Search multiple mount points systematically — do NOT rely on `/home` alone:
   ```bash
   # The canonical development drives — always check these FIRST
   ls /media/kubuntux/DEVELOPMENT*/ 2>/dev/null     # Primary: development drives
   ls /media/kubuntux/DEVELOPMENT*1/ 2>/dev/null    # Named variant: DEVELOPMENT1, dev1
   # Fallback: other common locations
   find /home -maxdepth 4 -iname "*projectname*" 2>/dev/null        # Home dir (least likely for active projects)
   find /mnt -maxdepth 4 -iname "*projectname*" 2>/dev/null         # External drives
   find /srv -maxdepth 4 -iname "*projectname*" 2>/dev/null         # Server roots
   ```

4. **Account for duplicate/case-variant clones.** This user has multiple copies of the same project with different casing (e.g., `automation-suite` vs `Automation-suite` on the same drive). When you find one copy, keep searching — there may be a second, more recent fork:
   ```bash
   # Case-insensitive search catches both variants
   find /media/kubuntux/DEVELOPMENT1 -maxdepth 2 -iname "*automation*suite*" 2>/dev/null
   ```

5. If the project was worked on by a different tool/agent (PaperclipAI, Windsurf, another session), search session history first:
   - `session_search("projectname OR toolname")`
   - The session may reveal the project path or that it exists somewhere else.

6. Search for common naming patterns:
   - `DEVELOPMENT`, `DEVELOPMENT1`, `DEV1`, `PROJECTS`, `workspace`, `code`
   - User may say "development1" but actual folder is `DEVELOPMENT1` (case varies)

7. Check agent metadata directories (Paperclip, Windsurf, Codex) for project references:
   ```bash
   ls ~/.paperclip/instances/*/companies/ 2>/dev/null          # Paperclip company folders
   ls ~/.config/Windsurf/User/globalStorage/ 2>/dev/null       # Windsurf storage
   ls ~/.local/share/codex/ 2>/dev/null                        # Codex sessions
   ```

8. If filesystem search and session search both fail, try broader filesystem search without case sensitivity and deeper recursion.

### Phase 2: Structure survey

Once located, get the lay of the land:

1. **Top-level listing** — `ls -la` the project root. Look for:
   - `frontend/`, `backend/`, `web/`, `api/` — split repos
   - `docker-compose.yml` — containerized setup
   - `package.json`, `Cargo.toml`, `pom.xml`, `Gemfile` — language/ecosystem
   - `prisma/`, `schema.prisma` — database ORM
   - `docs/` — documentation directory
   - `.github/` — CI/CD
   - `README.md` — project description

2. **Git history** — understand recent activity:
   ```
   git log --oneline -20                     # recent commits
   git log --oneline --all -30               # all branches
   git branch -a                              # branch landscape
   git status                                 # dirty state
   ```

3. **Stack identification** — read key config files:
   - `README.md` — purpose, stack, setup instructions
   - `package.json` (root + frontend + backend) — dependencies, scripts
   - `docker-compose.yml` — service topology

### Phase 3: Health check

For each service area, run these diagnostics:

| Area | Command | What to check |
|------|---------|---------------|
| Backend types | `npm run type-check` or `tsc --noEmit` | TypeScript error count |
| Backend tests | `npm test` (or `jest --passWithNoTests`) | Suite pass/fail, test count |
| Frontend types | `cd frontend && npm run type-check` | TypeScript error count |
| Frontend build | `cd frontend && npm run build` | Production build success |
| Backend build | `cd backend && npm run build` | Backend compile |

For each, capture the numeric error/failure count so the user knows the magnitude. Summarise the most common error categories (e.g., "prisma not imported", "missing jest types", "missing required fields").

### Phase 4: Docs and backlog survey

1. List `docs/` directory — look for game plans, status docs, gap maps, checklists.
2. Read these high-priority docs first (if they exist):
   - `README.md` — project purpose, setup
   - `VISION.md` or `ROADMAP.md` — strategic direction
   - Major checklists (e.g., `LAUNCH_CHECKLIST.md`, `IMPLEMENTATION_STATUS.md`)
   - `THREAT_MODEL.md` or `SECURITY_REVIEW.md` — security posture

### Phase 4b: Multi-repo fork comparison

Use this sub-phase when you discover multiple copies of the same project (same name, different casing, or same project in different directories). The user may not know which one is canonical.

1. **Identify all copies:**
   ```bash
   find /media/kubuntux/DEVELOPMENT1 -maxdepth 2 -iname "*projectname*" -type d 2>/dev/null
   ```

2. **Check git remotes** — do they point to the same GitHub repo or different ones?
   ```bash
   cd /path/to/copy && git remote -v
   ```
   - If same remote: they are clones/worktrees of the same repo
   - If different remotes: they are diverged forks — compare ages carefully

3. **Compare git histories** to determine which is more recent:
   ```bash
   # Check last commit dates
   cd /copy/A && git log -1 --format="%H %ai %s"
   cd /copy/B && git log -1 --format="%H %ai %s"
   # Compare total commit count
   cd /copy/A && git rev-list --count HEAD
   cd /copy/B && git rev-list --count HEAD
   ```

4. **Compare structure counts:**
   ```bash
   echo "Copy A packages:" && ls /copy/A/packages/ | wc -l
   echo "Copy B packages:" && ls /copy/B/packages/ | wc -l
   ```
   More packages + newer commits = likely the canonical fork.

5. **Look for audit/remediation docs** that only exist in one copy — that's a strong signal it's the actively developed one:
   ```bash
   # Files that signal active development:
   ls /copy/A/AUDIT.md /copy/A/EXECUTION_PLAN.md /copy/A/FINAL_STATUS.md 2>/dev/null
   ls /copy/B/AUDIT.md /copy/B/EXECUTION_PLAN.md /copy/B/FINAL_STATUS.md 2>/dev/null
   ```

6. **Report the relationship clearly** — is one a superset of the other? Diverged forks? Stale clones? Use language like:
   - "Repo A is the **original**, Repo B is the **actively worked-on fork** with N more packages and M more recent commits"
   - "Copy C is a **stale clone** of Repo B — hasn't pulled the last N commits"

See also: `references/multi-repo-comparison-pattern.md` for the worked command sequence, heuristics table, and relationship classification language from a real session.

### Phase 4c: Cross-reference claims vs verified state (MVP reality-check)

**Critical sub-Phase** — use when the repo contains AI-agent-written completion/status/summary reports (files like `IMPLEMENTATION_COMPLETE.md`, `FINAL_IMPLEMENTATION_REPORT.md`, `SESSION_SUMMARY_*.md`).

1. **Treat all agent-written status docs as claims, not evidence.** Do not report their percentage-complete figures as facts. They reflect what was attempted, not what actually compiles or works.

2. **Find the MVP scope definition document** — look for:
   - `SCOPE_FREEZE.md` or similar in `docs/linkr/` or `docs/`
   - `LAUNCH_CHECKLIST.md` — launch gates and go-live criteria
   - Any `CANON.md`, `MVP_SCOPE.md`, `ROADMAP.md` that defines what "done" means
   - Note: if ALL checklist items are marked `[x]` but build is broken, that's a red flag — means the doc was written by the same agent doing the work without verifying

3. **Cross-reference build health against scope:**
   - Does the backend compile? (`npx tsc --noEmit`)
   - Does the frontend build? (`npm run build`)
   - Count errors and categorize them (test infra vs source code)
   - If the scope doc mentions external integrations (payment gateways, email, Jumio), check whether those are configured with real keys or just stubs

4. **Check for founder blockers and governance gaps:**
   - Look for `FOUNDER_BLOCKERS.md` or similar
   - Check if pricing, plan names, media limits, or product decisions still need the user's input
   - These are launch-blocking even if all code compiles

5. **Include this assessment in the report**, using language like:
   - "Agent-written reports claim X% complete, but actual build state shows N errors"
   - "The MVP scope requires [feature] — the code exists but [is stubbed / doesn't compile / needs live keys]"
   - "Bottom line: this is NOT MVP-ready. To reach launch: [specific gaps list]"

See also: `repo-canon-audit` skill for deeper canon-vs-implementation drift checking.

### Phase 5: Report

Present a concise summary with sections:

1. **Location** — exact path
2. **What it is** — 1-2 sentence purpose (from README/VISION)
3. **Tech stack** — frontend, backend, db, infra
4. **Structure** — key directories and what they contain
5. **Build health** — numeric status for each area with major error categories
6. **Test health** — pass/fail counts
7. **Recent activity** — last N commits (author, date, type of work)
8. **Docs state** — what docs exist, any visible game plans
9. **What needs attention** — prioritized list based on build/test failures

## Important rules

- Always check **multiple filesystem locations** — projects may be on different drives or mount points than expected.
- When the user says PaperclipAI or another agent was working on it, search **session history first** before filesystem. The path may be mentioned in past conversations.
- Run `npm run type-check` (not just `tsc`) because it respects tsconfig project references and composite settings.
- For build diagnostics, distinguish between "test file errors" (usually missing jest types — low severity) and "source code errors" (high severity — blocks production).
- When listing error counts, provide both the total and a breakdown of the top 3 error categories so the user can prioritize.
- Do NOT modify the codebase during survey — this is discovery only.

## Common pitfalls

- Searching only one mount point when the project could be on another
- Reporting TypeScript errors without categorizing them (a mix of jest types + real source errors is very different from all source errors)
- Skipping docker-compose.yml — it reveals the full service topology
- Forgetting to check both backend and frontend separately in split-repo setups
- Reporting docs from `docs/archive/` as current guidance without checking if they're superseded
