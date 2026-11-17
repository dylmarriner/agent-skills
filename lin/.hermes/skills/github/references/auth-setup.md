# GitHub Authentication Setup

## Detection Flow

Run this check first:

```bash
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"
```

**Decision tree:**
1. `gh auth status` OK → use `gh` for everything
2. `gh` installed but not authenticated → use `gh auth login`
3. No `gh` → use git-only method (HTTPS token)

## Method A: HTTPS Personal Access Token (most portable)

Tell user to create a token at https://github.com/settings/tokens
with `repo` scope (and `workflow` if needed).

```bash
git config --global credential.helper store
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
# Trigger auth prompt:
git ls-remote https://github.com/<user>/<repo>.git
# Username = GitHub username, Password = token (NOT GitHub password)
```

## Method B: SSH Key

```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub  # Add to https://github.com/settings/keys
ssh -T git@github.com  # Verify
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

## Method C: gh CLI

```bash
gh auth login                    # Interactive browser
echo "$TOKEN" | gh auth login --with-token  # Headless
gh auth setup-git                # Wire into git
```

## API Token Without gh

```bash
export GITHUB_TOKEN="<token>"
# Use in curl:
curl -s -H "Authorization: token *** \https://api.github.com/user

# Or extract from git credentials:
grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `git push` asks for password | Use personal access token, or switch to SSH |
| `remote: Permission denied` | Token may lack `repo` scope |
| `fatal: Authentication failed` | Run `git credential reject`, re-authenticate |
| `gh: command not found` + no sudo | Use git-only Method A |
