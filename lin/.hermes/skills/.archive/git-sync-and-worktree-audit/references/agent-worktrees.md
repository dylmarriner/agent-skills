# Agent Worktrees (Cline and friends)

Coding agents that isolate work per task check out a real `git worktree` per task id, so the main
clone silently accumulates branches and directories nobody closed out.

## Cline layout

- Worktree path: `~/.cline/worktrees/<task-id>/<repo-name>/`
- Branch name: `cline/<task-id>` (the directory name is the task id prefix, e.g. `bad58`, `78242`)
- The branch is usually tip-committed when the agent stopped, so `git log` alone looks complete — the
  *uncommitted* pile inside the working directory is what still needs a human decision.
- Nothing prunes them: a merged worktree stays on disk and in `git worktree list` forever.

## Triage order

1. `git worktree list` — the branch each directory has checked out.
2. Merged check: `git rev-list --count cline/<id>..main` == 0 → dead, removable.
3. Uncommitted: `git -C <path> status --porcelain` — agent plan/notes files (`task_plan.md`,
   `notes.md`, `*-plan.md`) are usually untracked scratch, not part of any deliverable; say so rather
   than counting them as work in progress.
4. Intent check: `git -C <path> diff --stat` vs `git log --oneline -10 main` — watch for the branch
   *removing* a subsystem that main is actively fixing. That collision, not the commit count, is the
   thing to warn about.

## Reporting

Three buckets, per worktree, no prose padding: dead/merged · commits-not-in-main (grouped by theme,
not listed one per line if there are more than ~10) · uncommitted + untracked with the diffstat totals.
Finish with the one sentence that matters: which pile conflicts with main.
