---
name: git-history-replacement
description: Use when replacing a branch's history with a new tree.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, force-push, import, worktree, release]
    related_skills: [git-repo-replace, git-advanced]
---

# Replacing a branch's history with a new tree

Publishing an existing directory tree as a repository, and moving an existing
branch onto that history. The dangerous half is the second step: the new history
is unrelated to the old one, so it can never fast-forward.

## When to Use

- "Make this directory the new repo" / "push this tree as it is."
- "Change the remote to <repo> and push it how it is."
- "Force <default-branch> to the new setup."
- Importing a working copy that contains nested repositories or worktrees.

## Sequence

### 0. Settle where the repository root should be

If the intended root is genuinely ambiguous — promote an existing repo, or start a new one around it — ask once, with a recommended option, before doing anything. Repository surgery plus a push is expensive to unwind, and one question is cheaper than a wrong force-push. Once answered, execute without further check-ins.

### 1. Write the ignore file before the first `git add`

Dependency and build-output trees dominate a working copy and are rarely wanted
in the commit. On a real project tree the ignore file was the difference between
a 241 MB push and a 563 MB one, and `node_modules` alone accounted for roughly
twenty times the source size. Include dependency directories, build output,
caches, and machine-specific tool state.

### 2. Move nested `.git` entries aside before adding

**A directory containing `.git` is recorded as a gitlink — a bare commit
pointer — and none of its files are committed.** This silently drops entire
subtrees. It applies to nested clones and to `git worktree` checkouts, whose
`.git` is a file rather than a directory:

```sh
mkdir -p /tmp/saved-git
mv path/to/nested/.git /tmp/saved-git/nested.git
mv path/to/worktree/.git /tmp/saved-git/worktree.git   # this one is a file
# ... git init, git add -A, git commit, git push ...
mv /tmp/saved-git/nested.git path/to/nested/.git       # restore; do not delete
```

Restoring returns each nested repo to a working state. Keep them.

### 3. Init, stage, and check the numbers before committing

```sh
git init -b <new-branch>
git remote add origin <url>
git add -A
git diff --cached --name-only | wc -l
git diff --cached --name-only | tr '\n' '\0' | du -ch --files0-from=- | tail -1
```

A staged file count far below the tree's actual file count means a `.git`
boundary or an ignore rule swallowed a subtree. Find out which before committing.

### 4. Push to a NEW branch first

A fresh, unrelated history cannot fast-forward an existing branch, so the only
non-destructive push is to a name that does not exist yet. It also proves the
content lands before you touch anything real:

```sh
git push -u origin <new-branch>
```

### 5. Preserve the old tip, then move the target branch under a lease

Before pointing an existing branch at the new history, put the old tip somewhere
safe, and make the force conditional on the remote not having moved:

```sh
git fetch origin
OLD=$(git rev-parse origin/<target-branch>)
git push origin "$OLD:refs/heads/<target-branch>-pre-import"
git push --force-with-lease=<target-branch>:"$OLD" origin <new-branch>:<target-branch>
```

`--force-with-lease` aborts if the remote ref no longer matches the value you
fetched, so a concurrent change is never clobbered. Never use raw `--force`.

### 6. Verify from the remote, not from the push output

A successful exit only means the ref moved. Read the content back:

```sh
gh api "repos/<owner>/<repo>/git/trees/<branch>?recursive=1" \
  --jq '[.tree[] | select(.type=="blob")] | length'
gh api "repos/<owner>/<repo>/branches/<branch>" --jq '.commit.sha'
git rev-parse HEAD
```

Confirm the remote sha equals local HEAD and the blob count matches what you
staged. Also confirm the other branches still exist — report that you checked
rather than assuming.

## Pitfalls

- **Nested repositories commit as gitlinks, not files.** The most common silent
  data loss in this workflow. Check with `find . -name .git -not -path '*/node_modules/*'`
  and move every hit aside before staging.
- **Unrelated histories cannot fast-forward.** Expect a rejection on the first
  push to an existing branch name; that is the reason for steps 4 and 5, not a
  problem to force through immediately.
- **Never delete the backup branch you created.** It is the user's rollback. Ask
  before cleaning it up.
- **Do not silently commit near-duplicate trees.** A directory holding worktrees
  or clones of the *same* project triples the repository size. Commit what was
  asked for, then tell the user what is duplicated and offer to drop it.
- **`--force-with-lease` needs a fetched remote-tracking ref.** In a freshly
  `git init`-ed repo there is none, so `git fetch origin` first or pass the
  expected sha explicitly.
- **Report the old sha and the backup branch name.** The user needs a concrete
  rollback path, not reassurance that nothing was lost.
- **A wrapper folder hides the project.** `git init` in a directory that holds a
  single subdirectory produces a repository whose entire content is that folder,
  so the remote opens on one directory instead of the project and the tree looks
  empty. Confirm the intended root before committing; if it lands this way, say
  so plainly rather than letting the user discover it.
