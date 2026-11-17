---
name: cross-machine-project-sync
description: "Synchronize diverged copies of a Git-tracked project across two machines (e.g. laptop + remote server) — merge the more-advanced copy into the other while preserving each side's unique files."
version: 1.1.0
author: Hermes
tags: [git, rsync, merge, sync, devops]
---

# Cross-Machine Project Sync

When you have the same project on two machines and one has significantly more advanced code (new directories, rewritten modules, reorganized structure), use this workflow to merge the advanced copy into the other while preserving local-only files.

## When to Use

- A project lives on both your local machine and a remote server
- The remote copy has commits or uncommitted work the local one doesn't (or vice versa)
- The two copies have diverged structurally (different files, reorganized directories)
- Both copies have local-only files that must be preserved (configs, Dockerfiles, SQL migrations, setup scripts)

## Prerequisites

- SSH access to the remote machine (`ssh user@host`)
- Git repo on both sides
- `rsync` installed on both machines

## Workflow

### 1. Assess divergence

Identify which side is ahead and what files differ:

```bash
# On machine A: check git history
cd /path/to/project
git log --oneline -5

# Check uncommitted work
git status --short

# Get full file listing (excluding noise)
find . -type f -not -path '*/.git/*' -not -path '*/venv/*' \
  -not -path '*/__pycache__/*' -not -path '*/node_modules/*' \
  | sed 's|^\./||' | sort > /tmp/machineA_files.txt
```

Repeat on machine B. Diff the file lists:
```bash
diff /tmp/machineA_files.txt /tmp/machineB_files.txt
```

This tells you which files exist on each side but not the other.

### 2. Stash local changes on the target machine

The target (machine receiving the merge) must have a clean working tree:

```bash
cd /path/to/project
git stash --include-untracked
```

This saves all local modifications and untracked files into a stash so they can be restored later.

### 3. Rsync the advanced copy over

From the target machine, rsync FROM the source:

```bash
rsync -avz --delete \
  --exclude='.git/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='node_modules/' \
  --exclude='.DS_Store' \
  user@source-machine:/path/to/project/ \
  /path/to/project/
```

**Flags explained:**
- `-a` — archive mode (preserves permissions, timestamps, symlinks)
- `-v` — verbose (see what's happening)
- `-z` — compress for network transfer
- `--delete` — remove files on target that don't exist on source
- `--exclude` — skip dirs that should never be synced

The trailing slashes are important: `source/` → `dest/` means contents of source go INTO dest.

### 4. Restore local-only files

After rsync, check which local-only files were deleted:

```bash
# Try normal restore
git stash pop
```

If `git stash pop` fails due to overwritten files (common), the stash is preserved. Restore untracked files via a temp branch:

```bash
git stash branch restore-local-files stash@{0}
# Now switch back to main and clean up
git checkout main
git branch -D restore-local-files
git stash drop stash@{0}
```

The temp branch recreates untracked files that rsync --delete removed, without touching overwritten tracked files.

### 5. Verify merge integrity

Test that the merged codebase actually works:

```bash
# Test core imports
python3 -c "
import sys
sys.path.insert(0, '.')
# Import key modules from the advanced copy
try:
    from backend.some_module import SomeClass
    print('OK: some_module')
except Exception as e:
    print(f'FAIL: {e}')

# Import local-only modules
try:
    from backend.local_module import LocalClass
    print('OK: local_module')
except Exception as e:
    print(f'FAIL: {e}')
"

# Check git status summary
git diff --stat
git status --short | wc -l
```

### 6. Clean up

```bash
git stash drop stash@{0}   # if still present
git checkout main
```

## Pitfalls

- **`rsync --delete` on large repos can eat unique files.** Always stash first or pass `--dry-run` to preview deletions.
- **`git stash pop` fails on overwritten tracked files.** This is normal — the stash is preserved. Handle via the `git stash branch` workaround in step 4.
- **Docker Compose: source baked into image, not mounted.** If the remote project runs in Docker Compose and the Dockerfile uses `COPY . .` without a volume mount, rsyncing new Python files onto the host won't affect the running container. See `references/docker-compose-remote-edit.md` for diagnosis and fix.
- **Python `__pycache__/` dirs cause rsync conflicts.** Always exclude them.
- **Different git histories.** Rsync won't merge git history (`.git/` is excluded). Use `git merge` or `git cherry-pick` separately for history.
- **Venvs differ between machines.** Never rsync `venv/` — each machine manages its own.

## Verification

After sync, confirm:
1. New directories from source exist on target
2. Local-only files still exist
3. Core imports work
4. `git status` shows expected modified + untracked files
5. No stale `__pycache__` directories from the other machine's Python version
