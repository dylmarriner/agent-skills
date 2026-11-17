---
name: git-sync-and-worktree-audit
description: Use when syncing with GitHub, auditing or landing worktrees.
---

# Git Sync and Worktree Audit

Reconcile a local clone with its remote, report the true state of every branch and worktree hanging off
it (including stale agent worktrees), and — when asked — land that work onto main and push it.

Triggers: "pull and push", "sync with github", "what is in those worktrees", "is this
branch merged", "what is on these branches", "merge that branch in", "land the worktree work".

## Non-negotiable rules

- **Derive state from counts, not from git's summary prose.** `git status -sb` and pull/fetch
  output can be condensed by shell wrappers (`ok fetched (2 new refs)`, `ok 427 files +48323 -29328`).
  Every number you report must come back from `rev-list`/`--porcelain`, re-derived after the fetch.
- **Fetch before you count, count once.** `git fetch` moves the remote ref, so "behind 25" before a
  fetch becomes "behind 56" after. Fetch, then take all measurements, then act.
- **Never mutate state to inspect it — and never touch the working tree while a merge or rebase is in
  progress.** No `git checkout <ref> -- .`, `reset`, `stash`, or `clean` to "clean up" so the picture is
  simpler, and none of them mid-merge: `git stash` aborts the merge and clears `MERGE_HEAD`, so the staged
  result is silently gone and only the branch commits survive. Read-only first, always. To compare
  "before vs after" numbers (lint counts, test results) check the other ref into a **separate worktree**
  (`git worktree add /tmp/baseline origin/main`) — never swap the tree you are working in.
- **Pull with `--ff-only`.** It fails loudly on divergence instead of silently planting a merge commit
  in the user's repo. Only fall back to merge/rebase if the user asks for it.
- **Report what you did not touch.** Branches with no upstream, other worktrees, uncommitted piles —
  name them. A silent exclusion reads as "this is all there is".
- Clean tree + 0 ahead + clean push means "Everything up-to-date" is a *success* result. Say so; do not
  frame it as a failure or as "nothing happened".

## Procedure

### 1. Orient (read-only)

```bash
git status -sb && echo "---REMOTES---" && git remote -v && git branch -vv
git fetch --all
git rev-list --left-right --count HEAD...origin/main   # behind<TAB>ahead
git rev-list --count origin/main..HEAD                 # local-only commits
git log --oneline -3 origin/main
```

Interpret:
- `0\tN` → local ahead only: push.
- `N\t0` → behind only, fast-forwardable: pull.
- `N\tM` both non-zero → genuinely diverged. This is the one case worth asking about
  (rebase vs merge); everything else you decide and execute.

### 2. Pull

```bash
git pull --ff-only origin main
```

### 3. Push and verify

```bash
git push origin main
git rev-list --left-right --count HEAD...origin/main    # must be 0\t0
```

### 4. Sweep the whole clone, not just the current branch

```bash
git status --porcelain          # uncommitted + untracked in THIS worktree
git stash list
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  up=$(git rev-parse --abbrev-ref --symbolic-full-name "$b@{u}" 2>/dev/null)
  [ -n "$up" ] && echo "$b -> $up $(git rev-list --left-right --count $b...$up)"
  echo "$b not-in-main: $(git rev-list --count $b..main) main-not-in-branch: $(git rev-list --count main..$b)"
done
git worktree list
```

`main-not-in-branch == 0` on a worktree branch means it is fully merged → dead worktree,
offer `git worktree remove <path>` (`git worktree prune` for ones whose dirs are already gone).

### 5. Per-worktree triage

For each path from `git worktree list`:

```bash
git -C <path> status -sb
git -C <path> status --porcelain | wc -l        # uncommitted + untracked
git -C <path> log --oneline -5
git -C <path> diff --stat | tail -30            # scale of the uncommitted pile
git -C <path> rev-list --count main..HEAD       # commits this worktree has that main lacks
```

Report every worktree in three piles: **(a)** clean + merged = dead weight, **(b)** commits not in main,
**(c)** uncommitted changes and untracked files. See `references/agent-worktrees.md` for the Cline layout.

### 6. Flag intent conflicts before anyone merges

Ahead/behind counts cannot show this: check whether the divergent branch **deletes files main recently
added or fixed** — `git -C <path> diff --stat` on one side, `git log --oneline -10` on main on the other.
Report the collision explicitly ("branch X deletes the file main just gained three commits to") — it is the
reason a merge will fight, and it is invisible from the counts.

### 7. Land the pile (only when the user asks to merge or push it)

A merge carries **commits**, not working-tree files: uncommitted work in a worktree is invisible to
`git merge` until it is committed on its branch. Commit it there first, one commit per concern, matching
the repo's own message prefix style.

```bash
cd <worktree>
git add -A -- <explicit paths...>        # never blind `git add -A`; agent scratch stays out
git commit -q -F - < message.txt         # or -m for short messages
cd /home/lin/Documents/<repo>
git merge --no-ff --no-edit -m "<message>" <branch>
```

Then, in this order: prove the merge's intent, run the suite on the **merged** tree, push, verify sync.

```bash
git ls-files | grep -iE "<removed-subsystem patterns>" || echo NONE       # no tracked remnants
grep -rn "<removed symbol>" --include="*.py" --include="*.ts" app core scripts tests main.py  # no dangling refs
.venv/bin/python -m pytest tests/ -q        # full suite, not just the tests the branch added
git push origin main
git rev-list --left-right --count HEAD...origin/main                     # must be 0\t0
```

Keep agent scratch out of history: `notes.md`, `task_plan.md`, `*plan*.md` written by an agent are working
files, not repo content. Commit code and tests, leave the scratch untracked, and name it in the report.
See `references/merge-integration.md` for split-commit and conflict recipes.

## Pitfalls

- **Uncommitted and untracked files are invisible to `git log` and to the main worktree.** Agent scratch
  work (plans, notes, tests) only shows up via `status --porcelain` *inside* each worktree. Run it there,
  not from the main clone.
- **`git worktree remove` refuses while work is uncommitted/untracked — and `--force` destroys it.**
  Never force; report the pile and let the user decide.
- **A worktree directory that looks busy is not evidence of unique work.** Check the branch's
  not-in-main count first; a 0 means the directory content is already on main.
- **Don't push "to be safe".** Verify the ahead-count is non-zero first. Pushing a branch the user did not
  name, or rewriting anything, is out of scope for a sync request.
- When a sync finishes with nothing to publish, still run the sweep (section 4) and report the leftovers —
  "synced + here is the pile you did not ask about" is the useful answer, not a bare "up to date".
- If a named branch/worktree has no upstream at all, say that plainly instead of reporting `0 0` —
  "local-only, never pushed" is the actual state.
- **Auto-fixers rewrite the whole tree.** `ruff check --fix`, eslint `--fix`, prettier over a broad path set
  reformat files unrelated to the change and that churn lands in your commit. Scope the fixer to the files
  you touched (`ruff check --fix $(git diff --name-only <base> HEAD | grep '\.py$')`), then
  `git checkout -- <path>` for anything it reached beyond that. A repo-wide formatter sweep is a separate
  commit the user did not ask for.
- **A removal merge needs three proofs, not a passing test run.** Tracked remnants (`git ls-files`), no
  dangling references (`grep -rn`), and the runtime behaviour the removal was meant to restore — import the
  app entrypoint and assert the thing is gone (e.g. `socket.socket.__module__` is bare `socket` once a
  monkeypatch guard is deleted). Fix the docs in the same change: delete or banner any doc that still
  promises the removed mechanism, or the next reader trusts a guarantee the code no longer makes.
- **Collection errors that are env gaps are not regressions.** `ModuleNotFoundError` during pytest
  collection (missing `python-multipart`, `pyusb`, …) fails identically before the merge. Install the module
  into the project venv, re-run, and only then judge the branch — do not report it as merge damage.
- **When the branch and main both touched the same subsystem, a clean auto-merge is still a semantics
  question.** `git merge` reporting "Automatic merge went well" only means no textual conflict; check that the
  branch's intent (delete / rewrite) is what you actually verified, not just that the tree compiles.
