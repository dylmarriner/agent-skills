---
name: git-repo-replace
description: Replace a git repository clone and verify no tracked files were lost — cloning from a different fork, swapping versions, recovering from corruption
---

# Git Repo Replace

Replace an existing git clone with a fresh one from a different source or URL, and verify that no tracked source files were lost in the process.

Used when: user asks to "clone this repo and replace the old one", "swap this repo for a different version", or "re-clone from a different URL."

## Workflow

### 1. Check what exists

```bash
ls -d ~/repo-name*
```

Multiple clones may exist (`~/obelisk/`, `~/obelisk-fresh/`). Check which one the user means.

### 2. Record old state

```bash
cd ~/existing-repo
git ls-files | sort > /tmp/old-tracked.txt
git remote -v > /tmp/old-remote.txt
```

### 3. Clone to temp location

```bash
mkdir -p ~/repo-temp
cd ~/repo-temp
git clone https://github.com/user/repo .
```

If the target dir is the same name as what we're replacing, clone to a sibling temp dir and move it.

### 4. Replace the clone

Move old aside, move new in place:

```bash
mv ~/existing-repo ~/existing-repo.old
mv ~/repo-temp ~/existing-repo
```

### 5. Verify integrity

```bash
cd ~/existing-repo.old && git ls-files | sort > /tmp/old-tracked.txt
cd ~/existing-repo && git ls-files | sort > /tmp/new-tracked.txt

echo "=== Files in old but NOT in new ==="
diff /tmp/old-tracked.txt /tmp/new-tracked.txt | grep '^<'

echo "=== Files in new but NOT in old ==="
diff /tmp/old-tracked.txt /tmp/new-tracked.txt | grep '^>'
```

### 6. Interpret results

- **No old-only files** = full preservation. The new repo is a superset.
- **Old-only files present** = something was lost. Investigate before declaring success.
- **git objects/build artifacts** in old-only = expected (`.git/objects`, `target/`, `node_modules/`, compiler output). These are not source files.
- **New-only files** = additions to report to the user.

## Pitfalls

- `rm -rf ~/existing-repo` is destructive and may be blocked. Use `mv` to move old aside instead.
- Always compare **tracked files** (`git ls-files`) not filesystem files — build artifacts and `.git` internals create noise.
- `diff` exits 1 when files differ (which they will). This is not an error — check the output, not the exit code.
- The old backup (`~/repo-name.old`) can be cleaned up after the user confirms everything looks right:
  ```bash
  rm -rf ~/repo-name.old
  ```

## Reporting to the User

Report concisely:
1. All old tracked files present ✓ or list what's missing
2. List new additions by category (new modules, integrations, scripts)
3. Note if the old binary/build needs recompiling for the new code
