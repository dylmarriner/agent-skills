# Merge Conflict Resolution Patterns

## Pattern 1: Diverged Remote (Pull Merge)

**Situation:** Remote has commits local doesn't have *and* local has commits remote doesn't have. `git push` is rejected with "fetch first".

**Best strategy:** `git pull --no-rebase origin <branch>` then resolve. Use `--rebase` only on personal branches where you're confident about linear history.

**Real example — papatoetoe-funeral-cottage (June 2026):**

9 files conflicted across 3 categories:

| File | Category | Resolution |
|------|----------|-----------|
| `package-lock.json` | Generated | Took theirs (`git checkout --theirs`) |
| `package.json` | Dependencies | Took theirs, then re-added local package entries |
| `.gitignore` | Config | Merged both — kept HEAD's project file entries + local's env exclusions, deduplicated |
| `next.config.ts` | Config | Merged: HEAD's expanded remotePatterns + local's security headers + both sides' allowedDevOrigins |
| `layout.tsx` | Source | Merged: HEAD's payment guard + local's UI components (ScrollProgress, BackToTop, etc.) |
| `globals.css` | Source | Merged both theme entries |
| `obituariy-tributes/[slug]/page.tsx` | Source | HEAD was empty; took local's full implementation |
| `TributeDetail.tsx` | Source | Merged: local's sanitizeHtml + HEAD's style adjustments |
| `payload.config.ts` | Source | Merged: both collections lists, enhanced DB pool config |
| `not-found.tsx` | Add/add conflict | Merged: exported both PaymentLockPage (HEAD) and NotFoundPage (local) |

## Pattern 2: Rebase During Conflict Resolution

**When to use:** Feature branch where you want a clean linear history.

**Steps:**
```bash
git rebase --abort  # if current attempt is stuck
git pull --rebase origin main
# Resolve each commit's conflicts sequentially
git add <resolved>
git rebase --continue
```

**Pitfall:** Rebasing replays *each* of your commits sequentially, potentially causing the same file to conflict multiple times. A merge conflates all differences into one resolution step.

## Pattern 3: Strategic File Batching

Always resolve in this order:
1. **Lock files** (`package-lock.json`, `Cargo.lock`, `Gemfile.lock`) — take theirs
2. **Config files** (`.gitignore`, config files) — merge
3. **Source files** — merge per-file, reading each conflict
4. **Generated types** — take theirs
5. **Add/add files** — merge exports

This order minimizes rework: lock files don't affect source resolution, config don't affect code logic.
