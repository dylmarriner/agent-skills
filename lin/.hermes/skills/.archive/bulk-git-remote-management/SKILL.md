---
name: bulk-git-remote-management
description: "Repoint many local git repos to a new GitHub owner in one pass, find unpushed commits, and sync safely when repos are behind or diverged."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Git, Remotes, Bulk, Sync, Repo-Migration]
    related_skills: [github-repo-management, github-auth]
---

# Bulk Git Remote Management

Repoint many local repos to a new GitHub owner/account at once, audit which have
unpushed commits, and sync them WITHOUT force-pushing or blind-merging. Use when a
user says "change all my remotes to X with the same name", "consolidate my repos
under Y", or "see if anything needs pushing".

## Trigger
- User wants to repoint remotes across multiple local repos (rename account, typo fix,
  consolidate to one owner).
- Audit/cleanup: "which of my repos have unpushed commits / are behind".
- Migrating a renamed GitHub account while preserving repo names.

## Prereqs
- Authenticated with GitHub (see `github-auth`). Token needs `repo` scope.
- Don't persist tokens — use [REDACTED] in any notes/logs.

## 1. Discovery (full depth, scan ALL roots)
- Search every known project root, not just one. Examples: `~/Documents`,
  `~/CascadeProjects`, `/mnt/development1`.
- Use FULL depth: `find ROOTS -type d -name .git`. A shallow `-maxdepth 4` MISSED
  4 repos in practice; full depth found 40.
- Repos nest under tool-managed dirs (e.g. `~/Documents/Cline/MCP/github.com/<owner>/<repo>`).
  These are vendored clones owned by a tool, NOT personal repos. Repointing them breaks
  the tool's setup. LEAVE them and FLAG for the user.
- Reusable scanner: `scripts/scan_git_repos.sh` (captures url, branch, upstream,
  ahead/behind via three-dot rev-list, dirty status; optional `--repoint OWNER`).

## 2. Repoint remotes (URL-only — never push from the scanner)
- Preserve SAME repo name: build a `dir -> basename` map; `git remote set-url origin
  https://github.com/NEWOWNER/<basename>.git`.
- User's own typo'd/old account (e.g. `dylanmarriner`->`dylmarriner`): set-url directly.
- Repos with NO origin (local-only crates/workspaces): `git remote add origin ...`.
- Third-party forks (origin under someone else): repoint to `NEWOWNER/<same-basename>` ONLY
  if the user said "same name". The repo won't exist on the new account yet, so pushes 404
  until you create it — flag this.

## 3. Push / sync rules (CRITICAL pitfalls)
- VERIFY target exists before pushing: `gh api repos/NEWOWNER/NAME` — 404 means create
  first (`gh repo create --private --source . --push`) or the push fails.
- **"Ahead N vs the OLD remote" is NOT a license to push.** After repointing origin to the
  NEW account, RE-CHECK: `git fetch origin; git status -sb`. The new remote may hold
  commits your local lacks. Seen: a repo "ahead 3" vs stale old remote was actually
  BEHIND 125 on the new one.
- NEVER force-push or blind-merge a behind repo. Repos behind remote (e.g. 14 / 90 behind)
  stay local; OFFER to pull+merge, don't auto-push.
- Clean + truly fast-forwardable: `git push origin <branch>`.
- No upstream (new repo): `git push -u origin <branch>` — if it says "Everything up-to-date"
  a remote already had the commits; VERIFY, don't assume success.

## 4. Diverged repo — safe preservation (do THIS, not force-merge)
When local has commits the new remote lacks AND the remote has commits local lacks,
`git pull --ff-only` aborts and a naive rebase conflicts across many files. Do NOT hand-
resolve a big conflict dump blindly. Instead:
1. `git rebase --abort` (if mid-rebase).
2. Preserve local work on a dedicated branch: `git branch <topic>-upgrades` (from HEAD).
3. `git push -u origin <topic>-upgrades` — creates the branch and prints a PR URL on the
   new remote. Nothing on `main` is force-overwritten.
4. Report the PR link; leave `main`/remote `main` untouched for the user to review/merge.
This lost zero work and kept the canonical branch clean.

## 5. Final verification
After repointing, re-scan full depth and confirm every non-tool-vendored repo's origin
contains the expected owner:
```bash
find ROOTS -type d -name .git | while read g; do
  r="${g%.git}"; u=$(git -C "$r" remote get-url origin 2>/dev/null)
  echo "$u" | grep -q "github.com/NEWOWNER/" || echo "STRAY: $r -> $u"
done
```

## References
- `references/bulk-repoint-and-divergence.md` — full worked session transcript (40 repos,
  the divergence trap, preservation-branch resolution, what pushed vs stayed local).
