---
name: aris-repo-publishing
description: Use when pushing ARIS or scos-memory code to GitHub.
---

# Publishing the ARIS / scos-memory repos

Dylan's ARIS-family working copies live on **kubuntux** (native ext4). lin only sees them
through CIFS (`/mnt/development1` -> `//100.93.75.87/DEVELOPMENT1`).

## Ground truth paths (kubuntux)

| repo | path | GitHub origin |
|---|---|---|
| ARIS | `/media/kubuntux/DEVELOPMENT1/ARIS` | `dylmarriner/ARIS` |
| ARIS-harness | `/media/kubuntux/DEVELOPMENT1/ARIS-harness` | `dylmarriner/ARIS-harness` (fork of deepseek-ai/deepseek-harness = `upstream`) |
| ARIS-intelligence | `/media/kubuntux/DEVELOPMENT1/ARIS-intelligence` (+ worktree `/mnt/storage/worktrees/aris-wikiskill`) | `dylmarriner/ARIS-intelligence` |
| scos-memory | `/media/kubuntux/DEVELOPMENT1/scos-memory` (legacy clone) and `/media/kubuntux/DEVELOPMENT1/scos-memory-fabric` (**live clone, same origin**) | `dylmarriner/scos-memory` |

All four GitHub repos are private.

## Rules that matter

- **Never commit through `/mnt/development1` (CIFS).** The mount is case-insensitive/`mapposix`,
  so `git status` there invents phantom ` M`/` T` (typechange) entries for files that are clean
  on kubuntux, and case-colliding paths (e.g. `CLAUDE.md` vs `claude.md`) get mangled on checkout.
  Authoritative status = the same command run on kubuntux.
- **Never force-push.** Everything here is additive: push the feature/archive branch, use
  `-u`, and leave `main` alone unless Dylan asks for a merge.
- **Never commit build output or compiled binaries.** Patterns already used:
  `build/`, `__pycache__/`, `services/*/cmd/server/server`, `server.test`,
  `.claude/settings.local.json`, `.serena/`.
- **A stash is unpublished code.** Convert it to a real branch (`git stash apply` on a branch cut
  from `stash@{0}^1`, commit, push) and leave the stash in place.
- `scos-memory` and `scos-memory-fabric` are two clones of **one** repo: the fabric clone is live,
  the other is a legacy/archived lineage. Push legacy work to an `archive/*` branch, never to `main`.

## Credentials (kubuntux has no `gh` login)

`gh` on kubuntux is not authenticated. Mint a token on lin and drop it in tmpfs, then use it
for that session only:

```bash
# on lin
printf 'https://x-access-token:%s@github.com\n' "$(gh auth token)" \
  | ssh root@100.93.75.87 'umask 077; cat > /dev/shm/.gitcred; chmod 600 /dev/shm/.gitcred'
```

```bash
# on kubuntux: prefix every network git command
G() { git -c credential.helper="store --file=/dev/shm/.gitcred" "$@"; }
G -C <repo> fetch --all --prune
G -C <repo> push -u origin <branch>
```

Shred it when finished: `shred -u /dev/shm/.gitcred`.

## Commit identity

kubuntux has no global `user.name`/`user.email`; set them explicitly for the run
(`dylmarriner` / `298747229+dylmarriner@users.noreply.github.com`), otherwise commits fail.

Also add `safe.directory` entries — repos are owned by `kubuntux`, shell runs as root:
`git config --global --add safe.directory <path>`.

## ARIS-harness hooks (lefthook)

Installed hooks: `pre-commit` (lint via biome + whitespace + vendor-manifest + translation pairing)
and `pre-push` (typecheck, ~20-25 s). **Let them run** — a failing `pre-commit` means the change is
non-conforming (e.g. `@stylistic(max-len)` 140). Fix the source, not the hook. Only fall back to
`LEFTHOOK=0` if the hook is broken for unrelated reasons, and say so in the report.

## CI / runners (as of 2026-09-30)

All self-hosted GitHub Actions runners were **removed** — registrations deleted from every
`dylmarriner/*` repo, and the installs deleted from lin, kubuntux and rabuntu. Do not look for
`actions-runner-*` dirs, `actions.runner.*` units or `Runner.Listener` processes, and don't
re-install one to "fix CI".

Workflow labels were retargeted to GitHub-hosted runners in `Dispatchline` (local main +
`production-hardening-2026-09-29`), `ARIS-harness` and `ARIS-harness-upstream-fork`: the
`@aris`/`@deepseek-ai/dsh` fleet fallbacks in `ci.yml` are now `ubuntu-24.04` / `windows-2025`,
and the pool-only lanes (`serial-linux-selfhosted`, `serial-windows`, the two fleet
benchmarks) are gated behind `ARIS_CI_FAILOVER_*` / `github.repository`, so they skip instead of
queueing.

### Diagnosing "job did not start" — read the check-run ANNOTATION first

A job whose `runner_id` is 0, whose `steps` array is empty, and which flips to `failure` within
seconds never reached a runner. The reason is not in the log (there is none) — it is in
`gh api repos/<owner>/<repo>/check-runs/<job_id>/annotations`. This account's answer was:

> The job was not started because recent account payments have failed or your spending limit
> needs to be increased. Please check the 'Billing & plans' section in your settings

That is **account-wide and unfixable from code**: every job on a *private* repo is blocked until
the payment method / spending limit is fixed in GitHub → Settings → Billing and plans. Public
repos keep free minutes. Budget for this before retargeting a heavy monorepo at hosted runners —
ARIS-harness burns thousands of minutes per pipeline.

### Real breakages found once jobs could start again

- `pnpm-lock.yaml` in ARIS-harness master carried `negotiator@1.1.0` four times in `packages:` and
  four times in `snapshots:` → `ERR_PNPM_BROKEN_LOCKFILE (duplicated mapping key)` killed every
  job at install. Detected by loading the lockfile with a duplicate-key-rejecting YAML loader;
  fixed by dropping the byte-identical repeats. Validate any lockfile edit the same way before
  pushing.
- `packages/client/tsdown.client.ts` (ARIS-harness master) had the rebrand bug: `INLINE_SAFE` and
  `GENERATED_REMOTE` matched `@aris/aris-*`, but no package carries that infix (274 `@aris`
  specifiers in the lockfile, 0 with `aris-`). Every client bundle died in the purity gate. Fix is
  `@aris\/aris-` → `@aris\/`. When a mechanical rebrand is suspected, verify the pattern against
  the names that actually exist (grep the lockfile) before trusting it.

## Verify, don't assume

Pushing prints success even for a no-op. Read the refs back after every push — twice,
from two independent sources:

```bash
G -C <repo> ls-remote origin refs/heads/<branch>          # git
git -C <repo> rev-parse <branch>                          # must match
gh api repos/dylmarriner/<repo>/branches/<urlenc-branch> --jq '.commit.sha'   # on lin
```

When asserting "everything is pushed", enumerate **every local branch** and compare against
`refs/remotes/origin/<branch>`; a branch whose tip SHA is already reachable from an existing
remote branch (e.g. `tmp-merge-check` == `origin/fix/search-and-fences`) needs no push — say that
instead of pushing a duplicate name.
