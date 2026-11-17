# Replicating a Full Hermes Profile to Another Host

Class of work: "copy your config / skills / memories to <user>@<host>" — one-shot
replication of the local `~/.hermes/` profile onto a host that usually already
has a working Hermes install of its own. Merge, verify, never blind-overwrite.

## 0. Resolve the target first

A bare Tailscale IP is not an address you can `ssh` to — resolve hostname and
local username:

```bash
tailscale status --json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(p.get('HostName'), ip) for p in d['Peer'].values() for ip in p.get('TailscaleIPs',[]) if ip=='<IP>']"
```

Then probe candidate users non-interactively:

```bash
for u in <candidate-users> root; do
  echo "== $u"
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 $u@<IP> 'id; hostname; ls -d ~/.hermes' 2>&1 | head -5
done
```

- Tailscale SSH (`tagged-devices`, ACL-driven) authenticates as the **remote
  local user**. A user that does not exist on that box returns
  `tailscale: failed to look up local user "<name>"` and closes port 22 — that
  is a username error, not a network/connectivity error. Don't debug the
  network; probe another username.
- `root` frequently works when the tag grants it, but copying into `/root/.hermes`
  is only right if Hermes actually runs as root there. Check `ls /home/` and
  `ls -d /home/*/.hermes` to find the real install owner.
- The correct username can be unusual (e.g. a truncated-looking one). List
  `/home/` on the box rather than guessing spellings.

## 1. Inventory both ends before writing

```bash
# source
ls -la ~/.hermes | head -40
du -sh skills plugins memories
# target
ssh $u@$HOST 'ls >/dev/null; ls ~/.hermes; du -sh ~/.hermes; which hermes; hermes --version'
```

Target almost always already has: `config.yaml`, `.env`, `state.db`, its own
`skills/` tree (often the stock bundled set), caches. Treat the job as a merge.

## 2. Back up the target (before the first write)

```bash
ssh $u@$HOST 'cd ~/.hermes; B=$HOME/hermes-backup-$(date +%F-%H%M); mkdir -p "$B"; \
  cp -a config.yaml .env memories SOUL.md USER.md MEMORY.md AGENTS.md IDENTITY.md "$B"/ 2>/dev/null; \
  ln -sfn "$B" $HOME/hermes-backup-latest; ls -la "$B"'
```

`cp` errors for files the target simply doesn't have (USER.md, MEMORY.md, …)
are expected — keep `2>/dev/null` and confirm the files that do exist landed.

## 3. `.env` — merge, never overwrite

A target `.env` can be far larger than yours (it may hold provider/gateway keys
you don't have). Blind `rsync`/`cp` onto it silently deletes working
credentials. Union the keys, source values win:

```python
import re
def parse(p):
    d, order = {}, []
    for line in open(p):
        m = re.match(r'^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=', line)
        if m:
            k = m.group(1)
            if k not in d: order.append(k)
            d[k] = line.rstrip('\n')
    return d, order

loc, lo = parse('<local .env>')
rem, ro = parse('<remote .env>')
rem_only = [k for k in ro if k not in loc]          # preserve these
out = [loc[k] for k in lo] + ['', '# --- preserved from target (target-only) ---'] + [rem[k] for k in rem_only]
open('/tmp/merged.env', 'w').write('\n'.join(out) + '\n')
print('source', len(lo), 'target', len(ro), 'target-only', rem_only)
```

Push it over an existing file with `cat` (not `scp -t` truncation games) and
re-fix permissions:

```bash
scp -q /tmp/merged.env $u@$HOST:/tmp/merged.env
ssh $u@$HOST 'cat /tmp/merged.env > ~/.hermes/.env && chmod 600 ~/.hermes/.env'
```

Report the key counts and that target-only keys were kept. Empty `rem_only` is
the common good case.

## 4. Skills — rsync with the junk excluded

`~/.hermes/skills/` size is dominated by dev junk, not skills:

| Path | Typical size | Why |
|------|--------------|-----|
| `skills/.curator_backups/` | 1.5G+ | rotating tarball snapshots of the whole tree |
| `*/node_modules/` | ~1G | vendored web UIs inside imported skills |
| `*/.git/`, `*/.venv/`, `*/__pycache__/` | 10s of MB | dev leftovers |

```bash
cd ~/.hermes && rsync -a --info=progress2 \
  --exclude '.curator_backups/' --exclude 'node_modules/' --exclude '.git/' \
  --exclude '__pycache__/' --exclude '.venv/' \
  skills/ $u@$HOST:.hermes/skills/
```

- **Measure both sides with the same `--exclude` set.** `du -sh skills` on the
  source includes `node_modules` while the target's (fresh, excluded) copy does
  not: the numbers differ by ~1G and look like a failed transfer when nothing
  is wrong. Compare like for like: 245M vs 247M is a complete transfer.
- `--exclude 'node_modules/'` (anchored pattern) is fine; `du --exclude=` takes
  paths **relative to the directory argument** (`du -sh --exclude=node_modules skills`).
- No `--delete`: target-only skills are legitimate and stay.

## 5. Memories, identity files, config

```bash
rsync -a config.yaml SOUL.md AGENTS.md IDENTITY.md MEMORY.md USER.md OBELISK.md $u@$HOST:.hermes/
rsync -a memories/ $u@$HOST:.hermes/memories/
```

- Multi-source `rsync` **requires the destination directory to already exist**;
  rsync will not mkdir it. Copy straight into `~/.hermes/` (it exists) rather
  than inventing a staging dir.
- A leftover staging dir from an earlier run (e.g. `/tmp/<something>`) silently
  collects the files and the `~/.hermes/` write never happens — verify at the
  final path, not the staging path.
- Trailing slash matters: `memories/` copies contents, `memories` copies the dir.
- The same file can exist at both `~/.hermes/MEMORY.md` and
  `~/.hermes/memories/MEMORY.md` with different content; copy both, don't assume.

## 6. Verify by content, not by exit code

```bash
# config + identity files: compare hashes on both ends
md5sum ~/.hermes/config.yaml ~/.hermes/SOUL.md ...
ssh $u@$HOST 'md5sum ~/.hermes/config.yaml ~/.hermes/SOUL.md ...'

# skills: relative-path set comparison
find skills -name 'SKILL.md' -not -path '*/.curator_backups/*' | sed 's#^skills/##' | sort > local.txt
ssh $u@$HOST 'cd ~/.hermes && find skills -name SKILL.md | sed "s#^skills/##" | sort' > remote.txt
comm -23 local.txt remote.txt   # MUST be empty = nothing missing
comm -13 local.txt remote.txt   # target's pre-existing extras the merge keeps
```

The `comm -13` list is not a failure — report it as "kept the target's own N
extras". Parse the config with a real YAML parser on the target to prove it
still loads (use the target's own venv python: `~/.hermes/hermes-agent/venv/bin/python`).

## 7. Report state honestly

- A **running `hermes` process does not re-read `config.yaml`** — the new config
  applies at next start. Say that; don't imply the target is now live on the new
  config. `pgrep -af hermes` tells you what is running.
- State what was skipped (backups, `node_modules`, `plugins/`, `state.db`,
  `sessions/`) and how to get it if wanted. Dylan expects explicit skips, not
  silent exclusions.
- Give the backup path and the `hermes-backup-latest` symlink so the change is
  trivially reversible.
