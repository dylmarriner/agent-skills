---
name: divergent-codebase-merge
description: |
  Merge two diverged copies of the same codebase (e.g. same repo on two machines
  with independent changes). Uses rsync + git stash to combine both codebases
  while preserving local-only files. For the user Dylan — no narration, no
  explanations, just execution.
version: 1.0.0
toolsets: [terminal, file]
platforms: [linux]
---

# Divergent Codebase Merge

Synchronize two diverged copies of the same repository — one on the local
machine, one on a remote host via SSH. Preserves local-only files that the
remote version doesn't have. Common scenario: two machines with the same git
checkout but different uncommitted work and untracked files.

## When to Use

- Two machines have the same repo but different uncommitted changes
- Remote machine has more advanced feature work (exploit modules, AI integration)
- Local machine has deployment plumbing (Dockerfile, nginx config, migrations)
- User asks "merge X version into the local version" or "is Y better than Z"

## Workflow

### Phase 1: Recon
```bash
# 1. List both repos
ls -la /local/path/
ssh root@host "ls -la /remote/path/"

# 2. Compare git history
cd /local/path && git log --oneline -5
ssh root@host "cd /remote/path && git log --oneline -5"

# 3. List uncommitted on both sides
cd /local/path && git status --short | grep -v '__pycache__'
ssh root@host "cd /remote/path && git status --short | grep -v '__pycache__'"

# 4. File-level comparison
find /local/path -type f -not -path '*/.git/*' | sed 's|.*/||' | sort > /tmp/local_files.txt
ssh root@host "find /remote/path -type f -not -path '*/.git/*' | sed 's|.*/||' | sort" > /tmp/remote_files.txt
diff /tmp/local_files.txt /tmp/remote_files.txt
```

### Phase 2: Stash Local Changes
```bash
cd /local/path && git stash --include-untracked
```

### Phase 3: Rsync Remote → Local
```bash
rsync -avz --delete --exclude='.git/' --exclude='venv/' --exclude='__pycache__/' \
  --exclude='node_modules/' --exclude='.DS_Store' \
  root@host:/remote/path/ /local/path/
```

### Phase 4: Restore Local-Only Files
```bash
cd /local/path && git stash pop
```
If conflicts occur (files overwritten by rsync), resolve by:
- Taking remote version for functional code (new modules, exploit implementations)
- Taking local version for deployment config (Dockerfile, nginx, CI configs, package.json)

### Phase 5: Verify Integrity
```bash
cd /local/path
python3 -c "import sys; sys.path.insert(0, '.'); from backend.module import ClassName"
```

### Phase 6: Update .gitignore
After merge, update `.gitignore` to cover both sides:
- `__pycache__/`, `*.pyc`, `venv/`, `.venv/`, `.env`
- `dist/`, `node_modules/`, `.DS_Store`
- `*.db`, `*.sqlite`, `*.sqlite3`

## Recommended rsync Flags

| Flag | Purpose |
|------|---------|
| `-a` | Archive mode (preserves permissions, timestamps) |
| `-v` | Verbose output |
| `-z` | Compress during transfer |
| `--delete` | Remove local files not on remote (critical for merge) |
| `--exclude='.git/'` | Don't mess with git metadata |

## Pitfalls

- **--delete removes local-only files**: Always stash BEFORE rsync, so local-only
  files (Dockerfile, migrations, CI configs, package.json variants) can be restored.
- **git stash pop fails on overwritten files**: If rsync overwrote a modified file,
  stash pop will refuse. Let the remote version stand and drop the stash entry:
  `git checkout . && git stash drop`
- **__pycache__ and .pyc can't rsync properly**: Always exclude them.
- **Ownership mismatch**: rsync preserves UID/GID. If remote runs as root and local
  as a user, files may need `chown -R $USER:$USER`.
- **Git safe.directory**: If the repo owner differs from the SSH user, git refuses
  to operate. Fix with `git config --global --add safe.directory /path/to/repo`.
- **Import verification after merge**: Always run a Python import test on every
  module that was overwritten. rsync with --delete can leave half-files if interrupted.
- **Large file sets**: If >100 files differ, batch the restore of local-only files
  by category rather than file-by-file.
- **GitHub token in remote URL**: After pushing with a PAT in the URL, immediately
  `git remote set-url origin https://github.com/user/repo.git` to avoid leaking
  credentials in `git remote -v` output.

## User Preference

No narration of what you're about to do. No step-by-step explanations. No "now I'll" or "first let's". 
Deliver results and commands. If something fails, state the next step compactly. 
If it works, confirm in one line. No apologies.
