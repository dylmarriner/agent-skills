# Remote SSH Repo Management

Pattern for finding, committing, and pushing repos on remote servers accessed via SSH.

## Discovery

Repos may live at non-standard paths (external drives, media mounts, secondary volumes):

```bash
# Broad find
find / -maxdepth 5 -type d -name '<repo-name>' 2>/dev/null

# User home candidate dirs
find /home /root ~ -maxdepth 4 -type d -name '*<keyword>*' 2>/dev/null

# Check common external mounts
ls /media/<user>/ /mnt/
```

## Ownership & git safe.directory

When SSHing as root but the repo is owned by another user:

```bash
# Fix: add safe.directory exception (as root)
git config --global --add safe.directory /path/to/repo

# Or run git commands as the repo owner
sudo -u <owner> bash -c 'cd /path/to/repo && git status'
```

## Authentication (user-specific)

`gh` auth is per-user. Root's `gh` often has no auth context while the actual user's does:

```bash
# Check auth as root
gh auth status

# Check auth as the repo owner
sudo -u <owner> gh auth status

# Run git operations as the user who owns the auth token
sudo -u <owner> bash -c '
  cd /path/to/repo
  git add -A
  git commit -m "message"
  git push origin <branch>
'
```

## Pitfalls

- Remote URL uses HTTPS but only the repo-owner user has `gh` auth cached — root cannot push.
- `find` search sensitive to max-depth: repos on external drives may be deeper than expected.
- `git safe.directory` with root SSH: if you don't add it, every git command inside a user-owned repo fails with "dubious ownership".
- The inverse: running `sudo -u <owner>` bypasses root's shell config and ssh-agent — but owner's `gh` OAuth token in their `~/.config/gh/hosts.yml` works because it's file-based, not agent-based.
