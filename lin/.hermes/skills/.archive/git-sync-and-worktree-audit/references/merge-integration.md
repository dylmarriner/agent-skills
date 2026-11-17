# Landing a worktree branch into main

Recipes for the step after the audit: taking an agent branch (or a dirty worktree) and getting it onto
`main` without losing work, breaking the tree, or importing churn.

## Commit the branch before you merge anything

A merge carries commits. Working-tree files in a worktree are invisible to `git merge`, and uncommitted
work is the only thing that cannot be recovered if a merge goes wrong — everything committed on the branch
survives an aborted merge, a `reset --hard`, or a botched conflict resolution.

Ordering that makes the whole operation recoverable:

1. `git -C <worktree> status --porcelain` — see exactly what is dirty.
2. Commit it **on the branch** as one or more focused commits.
3. Only then merge into `main`.

If the working tree is clean and the branch is dirty-free, skip straight to the merge.

## Splitting one dirty pile into focused commits

Stage by concern with explicit paths — never `git add -A` blind, because agent scratch (`notes.md`,
`task_plan.md`, `*plan*.md`, coverage reports) lives in the same tree.

```bash
git add -A -- <deleted subsystem files> <call sites> <new test for the removal>
git commit -q -F - <<'MSG'
<type>: <what changed>

<why it changed — the behaviour that was broken>

- <deletion>
- <unwiring of build/test hooks>
- <new regression test>
MSG

git add -A -- <unrelated feature files, tests, docs>
git commit -q -m "<type>: <feature>" -m "<one line of intent>"
```

Deleted files go in with `git add -A -- <path>` — it stages deletions as well as modifications, so no
separate `git rm` is needed. Verify with `git status --porcelain`: whatever is still listed is what you
deliberately left out.

## Inspect a merge before committing it

```bash
git merge --no-ff --no-commit <branch>
git status --porcelain        # staged result; conflicts show as UU / DU / UD
git merge --abort             # if the result is not what you want
```

If the branch's history already contains main's recent fixes (an ancestral commit), a modify/delete
collision resolves automatically and the merge is clean — do not be surprised by "Automatic merge went
well", but still check the conflict list is genuinely empty rather than assuming.

## Conflict shapes and what to do

| Shape | Meaning | Resolution |
|---|---|---|
| `DU` / `UD` (modify/delete) | One side edited a file the other deleted | Decide by intent: if the subsystem was deliberately removed, deletion wins — `git rm <path>`. If main's edit matters, re-add with the edit. |
| `UU` (both modified) | Real content conflict | Resolve per hunk; take one side wholesale only when the other side's change is genuinely superseded |
| clean | No textual conflict | Still verify semantics — see the removal proofs in SKILL.md |

When a branch deliberately removes a subsystem, main's later fixes *to that subsystem* are dead weight;
delete them with the subsystem instead of resurrecting the file to preserve the fix.

## Pre-push verification battery

Run these on the **merged** tree, not on the branch:

```bash
git ls-files | grep -iE "<removed patterns>" || echo NONE       # tracked remnants
grep -rn "<removed symbol>" --include="*.py" --include="*.ts" app core scripts tests main.py
.venv/bin/python -m pytest tests/ -q                           # whole suite
<entrypoint smoke test proving the removal took effect at runtime>
docs check: the removed mechanism's docs are deleted or bannered
```

Test count parity matters: a suite that reports fewer tests than the branch added means collection failed
silently (often a missing module) — check the collection summary, not just the final line.

## Recovery if the merge state is destroyed mid-operation

Symptom: `MERGE_HEAD` is gone, the working tree is clean at the old HEAD, and the staged merge result has
vanished. Cause is almost always a `stash`/`checkout` run while the merge was still in progress.

It is not data loss as long as the branch was committed first:

```bash
git stash list && git stash drop        # the stashed merge tree is no longer needed
git reset --hard origin/main           # clean base
git merge --no-ff --no-edit -m "<same message>" <branch>   # deterministic: the merge is automatic
```

Never re-run the risky command to "see if it works differently" — fix the inspection method (separate
worktree) and redo the merge, which is reproducible.
