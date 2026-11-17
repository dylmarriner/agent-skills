---
name: github
description: Complete GitHub workflow — auth, issue/PR management, code review, and repo administration via gh CLI or git+curl API.
category: devops
emoji: 🐙
---

# GitHub Operations

A single umbrella skill covering all GitHub interactions. This merges five previously-separate skills (github-auth, github-issues, github-pr-workflow, github-code-review, github-repo-management) into one organized reference.

## Auth Detection — Shared Setup

All subsections below depend on one of these auth methods. Detect at the start of any session:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -n "$REMOTE_URL" ]; then
  OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
  OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
  REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
fi
```

See `references/auth-setup.md` for the full authentication setup workflow including HTTPS tokens, SSH keys, gh CLI login, and headless token auth.

---

## Section A: Authentication Setup

### Quick Setup — HTTPS Personal Access Token (most portable)

Tell user to create a token at https://github.com/settings/tokens with `repo` scope (and `workflow` if needed).

```bash
git config --global credential.helper store
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
# Enter username + token (NOT password) when prompted
git ls-remote https://github.com/<user>/<repo>.git
```

### SSH Key Setup

```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
# Add to https://github.com/settings/keys
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

### gh CLI Setup

```bash
gh auth login                          # Interactive browser
echo "$TOKEN" | gh auth login --with-token  # Headless
gh auth setup-git
```

---

## Section B: Issues Management

### View/Create/Manage Issues

```bash
# List
gh issue list --state open --label "bug"
gh issue list --assignee @me

# View
gh issue view 42

# Create
gh issue create --title "Login bug" --body "## Steps\n1. ..." --label "bug" --assignee username

# Edit
gh issue edit 42 --add-label "priority:high" --add-assignee @me

# Comment
gh issue comment 42 --body "Root cause found — fixing."

# Close / Reopen
gh issue close 42 --reason "completed"
gh issue reopen 42
```

### Curl API Fallback

| Action | Endpoint |
|--------|----------|
| List issues | `GET /repos/{o}/{r}/issues` |
| View issue | `GET /repos/{o}/{r}/issues/N` |
| Create issue | `POST /repos/{o}/{r}/issues` |
| Add labels | `POST /repos/{o}/{r}/issues/N/labels` |
| Assign | `POST /repos/{o}/{r}/issues/N/assignees` |
| Comment | `POST /repos/{o}/{r}/issues/N/comments` |
| Close | `PATCH /repos/{o}/{r}/issues/N` |
| Search | `GET /search/issues?q=...` |

### Templates

- `templates/bug-report.md` — Standard bug report template
- `templates/feature-request.md` — Feature request template

---

## Section C: Pull Request Workflow

### Branch → Commit → Push → PR

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/my-feature
# ... make changes with read_file/write_file/patch ...
git add <files>
git commit -m "feat: add my feature"
git push -u origin HEAD

# Create PR
gh pr create --title "feat: ..." --body "## Summary\n..." --label "enhancement"
```

### CI Monitoring

```bash
gh pr checks --watch           # Blocking watch
gh run list --branch $(git branch --show-current) --limit 5
gh run view <RUN_ID> --log-failed
```

### Merging

```bash
gh pr merge --squash --delete-branch        # Clean merge
gh pr merge --auto --squash --delete-branch # Auto-merge when CI passes
```

### CI Troubleshooting

See `references/ci-troubleshooting.md` for diagnosing common CI build failures and GitHub Actions log analysis.

### PR Templates

- `templates/pr-body-feature.md` — Feature PR body
- `templates/pr-body-bugfix.md` — Bugfix PR body

---

## Section D: Code Review

### Local Change Review (Pre-Push)

```bash
git diff main...HEAD --stat               # Scope
git diff main...HEAD                      # Full diff
git diff main...HEAD --name-only          # File list
git diff main...HEAD | grep -n "print(\|console.log\|TODO\|FIXME"   # Common issues scan
```

### Checklist

- **Correctness**: edge cases, error paths
- **Security**: no hardcoded secrets, injection prevention
- **Quality**: naming, DRY, single responsibility
- **Testing**: paths covered?
- **Performance**: N+1 queries, blocking in async?

### PR Review

```bash
gh pr view 123
gh pr diff 123
gh pr checkout 123

# Leave review
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

### Inline Comments via API

```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="Use parameterized queries to prevent SQL injection." \
  -f path="src/auth.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45 \
  -f side="RIGHT"
```

### Review Output Template

See `references/review-output-template.md` for the structured review format (Critical / Warnings / Suggestions / Looks Good).

---

## Section E: Repository Management

### Clone/Create/Fork

```bash
gh repo clone owner/repo
gh repo create my-project --public --clone
gh repo fork owner/repo --clone
```

### Settings

```bash
gh repo edit --description "..." --visibility public
gh repo edit --enable-wiki=false --enable-issues=true
gh repo edit --default-branch main
```

### Secrets & Releases

```bash
gh secret set API_KEY --body "value"
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release list
```

### Branch Protection

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{"required_status_checks":{"strict":true,"contexts":["ci/test"]},"required_pull_request_reviews":{"required_approving_review_count":1}}'
```

### GitHub Actions

```bash
gh workflow list
gh workflow run ci.yml --ref main
gh run list --limit 10
gh run view <RUN_ID>
gh run rerun <RUN_ID> --failed
```

### API Quick Reference

See `references/github-api-cheatsheet.md` for the full curl-based endpoint reference table.

---

## Git Conventions

### Conventional Commits

- `feat:` — new feature
- `fix:` — bug fix  
- `refactor:` — code restructuring
- `docs:` — documentation
- `test:` — test additions
- `ci:` — CI/CD changes
- `chore:` — maintenance

Format: `type(scope): short description`

---

## Cross-References

These support files were migrated from the sub-skills that were absorbed into this umbrella:

- `references/auth-setup.md` — Full authentication workflow
- `references/conventional-commits.md` — Commit message conventions
- `references/ci-troubleshooting.md` — CI failure diagnosis
- `references/github-api-cheatsheet.md` — REST API endpoint reference
- `references/review-output-template.md` — Code review output format
- `templates/bug-report.md` — GitHub issue bug report template
- `templates/feature-request.md` — GitHub issue feature request template
- `scripts/gh-env.sh` — Auth detection script
