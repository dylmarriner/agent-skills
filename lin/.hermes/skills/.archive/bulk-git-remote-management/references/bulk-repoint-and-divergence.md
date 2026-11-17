# Bulk Repoint & Divergence Preservation

## Scenario
User: "change the remotes to user dylmarriner with the same name and see if they have
anything to push."

## Discovery
- 40 git repos across `~/Documents`, `~/CascadeProjects`, `/mnt/development1` (full-depth
  `find`, NOT `-maxdepth 4` — shallow missed 4).
- One straggler: `~/Documents/Cline/MCP/github.com/NightTrek/Software-planning-mcp` — a
  Cline-managed MCP tool clone. NOT a personal repo. Left it; flagged (repointing would
  break Cline's MCP setup).
- Mix of: own repos under a typo'd old account (`dylanmarriner`), third-party forks under
  other owners, and local-only crates with no origin.

## The Trap (most important lesson)
A repo reported "ahead 3" — but that was relative to the STALE old remote (`dylanmarriner`).
After repointing `origin` to `dylmarriner`, `git fetch` + `git status -sb` revealed it was
actually **behind 125** on the new remote and diverged (3 local vs 125 remote).

Naive `git pull --ff-only` aborts (not a fast-forward). A `git rebase origin/main` hit real
conflicts in 5 files (app/main.py, mcp.py, memory/ingest.py, models/schema.py,
requirements.txt). Blindly resolving a 5-file conflict dump risks corrupting the code.

## Safe Resolution (preserve everything)
```bash
git -C <repo> rebase --abort            # if mid-rebase
git -C <repo> branch openviking-upgrades # snapshot local commits (3 here)
git -C <repo> push -u origin openviking-upgrades
# prints: https://github.com/dylmarriner/synapse-memory/pull/new/openviking-upgrades
```
- Zero work lost. Canonical `main` and remote `main` untouched.
- User reviews/merges the PR later.

## What pushed cleanly
- `private-dialer-mvp`: `git push -u origin master` → "Everything up-to-date" (remote
  already had the 2 commits; VERIFY, don't assume).
- `synapse-memory`: diverged → preservation branch (above).
- Behind repos (`funeral-cottage-website` 14 behind, `LinkrNZ` 90 behind): NOT pushed.
  Offered pull+merge, left for user.
- ATLAS-GATE-EXTENSION / ATLAS-GATE-MCP: no repo under `dylmarriner` (or `dylanmarriner`)
  → can't push until created.
- 11 SCOS crates: files present but 0 commits locally, no remote repo → nothing to push.

## Rules (embedded in SKILL.md §3/§4)
1. Full-depth scan; flag tool-vendored clones, don't repoint.
2. Verify target repo exists (`gh api repos/OWNER/NAME`) before push.
3. "Ahead vs OLD remote" ≠ safe to push — re-check vs NEW remote after repoint.
4. Never force-push / blind-merge behind repos.
5. Diverged → preservation branch + PR, not force-merge.
