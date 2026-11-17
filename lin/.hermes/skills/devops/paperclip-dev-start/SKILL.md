---
name: paperclip-dev-start
description: Start PaperClip dev server from a cloned repo — reliable approach after process conflicts
trigger: pnpm dev fails with "paperclip-dev-watch already running"
---

# PaperClip AI - Dev Server Start

## When to use
Start PaperClip dev server in a clean environment where old processes may be lingering.

## From a bare clone (first install, no instance yet)

1. Check for an instance already running before doing anything: `ss -ltnp '( sport = :3100 )'` and `curl -sS http://127.0.0.1:3100/api/health`. A healthy response means install is done — reuse it and skip to Verify.
2. Requirements: Node >= 24.11, pnpm >= 9.15, and a Rust toolchain (source builds the native runner; set `PAPERCLIP_RUNNER_BINARY` to a prebuilt runner to skip that).
3. `cd <repo> && pnpm install` — postinstall links the plugin SDK and provisions provider assets; it is safe and fast when already synced ("Already up to date").
4. `pnpm dev` — the dev script sets `PAPERCLIP_MIGRATION_AUTO_APPLY=true`, so migrations apply and the embedded Postgres cluster is created under `~/.paperclip/instances/default/db` (port 54329). **No `.env` and no `DATABASE_URL` needed.** Expect "building paperclip runner", plugin SDK build, then embedded-postgres boot — startup takes ~25-60s before it listens.
5. Default mode is `local_trusted` bound to `127.0.0.1:3100`. Pass `--bind lan` (or `--bind tailnet`) only when the UI must be reachable off-host.
6. Verify per the Verify section. A boot banner line `Agent JWT missing (run `npx paperclipai onboard`)` means the instance exists but is un-onboarded — agents cannot run until `onboard` is run; loopback UI access alone does not need it.

`~/.paperclip/instances/default/config.json` is merged into the running config but is written only after first start, so on a fresh clone set behaviour with CLI flags/config after boot, not by pre-creating the file.

## How to start (reliable approach)

1. **Stop systemd user service first** (if it exists — `pkill` won't stop it):
   ```sh
   systemctl --user stop paperclip.service
   ```

2. **Kill any remaining processes** (skip pkill -f "paperclip" to avoid matching SSH/tailscaled):
   ```sh
   pkill -f "dev-runner" 2>/dev/null; pkill -f "dev-watch" 2>/dev/null
   sleep 2
   ```

3. **Identify the working directory** — there may be two copies (e.g. `~/paperclip` and `/media/kubuntux/DEVELOPMENT1/paperclip`). Use the one the systemd service references.

4. **Start the server** with `pnpm dev:once -- --bind lan` (serves UI + plugins on 0.0.0.0:3100):
   ```sh
   cd /path/to/paperclip && pnpm dev:once -- --bind lan
   ```
   Note: `--tailscale-auth` is a legacy alias for `--bind lan` (logs will print this deprecation). Use `--bind lan`.

**Why `pnpm dev:once` instead of direct `tsx src/index.ts`?** The dev-runner starts the UI dev server and handles plugin loading. Direct `tsx src/index.ts` runs API-only mode and may miss the UI.

## Pitfalls

### Migration/journal crash loop (1514 restarts experienced)

When Paperclip fails to start and systemd shows `restart counter is at NNNN`, check the journal:

```sh
journalctl --user -u paperclip.service -n 50 --no-pager
```

**Common causes and fixes:**

**A. Duplicate migration numbers**
The migration checker at `packages/db/src/check-migration-numbering.ts` rejects files with identical 4-digit prefixes:
```
Error: Duplicate migration number 0085 in migration files: 0085_foo.sql, 0085_bar.sql
```
AND checks files vs `migrations/meta/_journal.json`:
```
Error: Migration journal/file count mismatch: journal has 87, files have 90
```
Fix: Check the journal to see which file name it expects (the journal IS the source of truth), then:
- Delete orphan `.sql` files that were superseded (renamed during development but old file wasn't cleaned up)
- Add new migration entries to `_journal.json` for legitimately new .sql files

**To add a journal entry for a new migration:**
```sh
python3 -c "
import json, time
d = json.load(open('packages/db/src/migrations/meta/_journal.json'))
d['entries'].append({'idx': len(d['entries']), 'version': '7', 'when': int(time.time()*1000), 'tag': 'XXXX_migration_name', 'breakpoints': True})
json.dump(d, open('packages/db/src/migrations/meta/_journal.json','w'), indent=2)
"
```

**B. Missing workspace packages (ERR_MODULE_NOT_FOUND)**
New adapters/plugins may not be symlinked. Run:
```sh
pnpm install --no-frozen-lockfile
```

**C. Missing adapter packages at startup**
If you see `Cannot find package '@paperclipai/adapter-XXXX'` but the directory exists under `packages/adapters/`, it just needs `pnpm install` to create the workspace symlinks in `node_modules/@paperclipai/`.

### Dev-runner vs dev-watch in systemd
The systemd unit should use `dev:once` (runs `dev-runner.ts dev`) NOT `dev` or `dev:watch` (runs `dev-runner.ts watch`). Watch mode adds unnecessary process layers on top of systemd's own `Restart=always`. The unit at `~/.config/systemd/user/paperclip.service` should use:
```
ExecStart=/usr/bin/env LD_LIBRARY_PATH=%h/.local/lib pnpm dev:once -- --bind lan
```

### journalctl for systemd logs
When Paperclip is under systemd user service control, use journalctl to see startup logs:
```sh
journalctl --user -u paperclip.service -n 50 --no-pager
```
This reveals build steps, embedded postgres init, and startup errors. The Paperclip app logs in `~/.paperclip/instances/default/logs/server.log` are only written after the server boots — pre-boot failures (config validation, missing libs, build failures) only appear in journalctl.

### Multiple repo copies
The systemd service may reference a different path than ~/paperclip (e.g. `/media/kubuntux/DEVELOPMENT1/paperclip` on a separate disk). Always check the working directory in the systemd unit file and match any `cd` or `WorkingDirectory` accordingly.

### ENOSPC / disk-full diagnostics
A "database_unreachable" health check can mean:
1. Embedded postgres isn't running (check `ss -tlnp | grep 54329`)
2. Disk is full — Postgres can't extend its files (`could not extend file "base/...": No space left on device`)
3. `/tmp` is full, preventing adapter temp dirs (`ENOSPC: no space left on device, mkdtemp '/tmp/paperclip-opencode-...'`)

Diagnose with: `df -h && du -sh /tmp && journalctl --user -u paperclip.service -n 20 --no-pager`

### systemd user service auto-restarts
Paperclip is commonly run as a `systemctl --user` service with `Restart=always`. This means:
- `pkill -f paperclip` kills the SSH session (matches the tailscaled child) AND Paperclip auto-restarts
- Always use `systemctl --user stop paperclip.service` to halt it cleanly
- The service unit typically lives at `~/.config/systemd/user/paperclip.service`
- `--tailscale-auth` is now a legacy alias; use `--bind lan` in ExecStart

### `bind` enum validation
The config at `~/.paperclip/instances/default/config.json` validates `server.bind` against `['loopback', 'lan', 'tailnet', 'custom']`. Setting `"bind": "0.0.0.0"` (common from older docs) causes Paperclip to **refuse to start** with:
```
Invalid config at .../config.json: server.bind: Invalid enum value. Expected 'loopback' | 'lan' | 'tailnet' | 'custom', received '0.0.0.0'
```
Fix: set `"bind": "lan"` in the config file.

### `check-node-version-policy` fails on provider assets
`node scripts/check-node-version-policy.mjs` walks every `package.json` and requires `engines.node`. It also descends into `provider-assets/`, which holds pinned upstream distributions (`@github/copilot`) whose manifests legitimately lack `engines`. Fix at the checker's `skippedDirectories` set (add `provider-assets`), not by editing the vendor manifests — postinstall (`install-copilot-assets.mjs`) re-provisions and overwrites them. `node -v` being above the minimum does not silence the check; it is static manifest/docker/workflow lint, unrelated to the running server.

### Allowed hostname
If you get `Hostname 'X.X.X.X' is not allowed for this Paperclip instance`, add it via:
```sh
pnpm paperclipai allowed-hostname <TAILSCALE_IP>
```
Or edit `allowedHostnames` in `config.json` directly. Restart after changing.

## Verify
```sh
curl http://<TAILSCALE_IP>:3100/api/health
```

Expected: `{"status":"ok","deploymentMode":"authenticated","bootstrapStatus":"ready"}`

## Accessing via SSH Tunnel

If you are not using `--bind lan` or the server is bound to `127.0.0.1`, use an SSH tunnel:

```bash
ssh -L 3100:127.0.0.1:3100 user@<REMOTE_IP>
```

Then access at `http://localhost:3100`.

## Tailscale Configuration

These settings apply whether Paperclip runs on a local machine (laptop) or a remote host — both need `bind: "lan"` and the Tailscale IP in `allowedHostnames` for Tailscale reachability.

Update `~/.paperclip/instances/default/config.json`:
   - Set `"host": "0.0.0.0"`
   - Set `"bind": "lan"` (NOT `"0.0.0.0"` — that causes an enum validation error)
   - Set `"deploymentMode": "authenticated"`
   - Ensure `<TAILSCALE_IP>` is in `"allowedHostnames"` list

2. If running under systemd, update the unit file:
   ```ini
   ExecStart=/usr/bin/env LD_LIBRARY_PATH=%h/.local/lib pnpm dev:once -- --bind lan
   ```
   Then: `systemctl --user daemon-reload && systemctl --user restart paperclip.service`

### `--bind lan` flag
Use `pnpm dev:once -- --bind lan` to auto-detect the Tailscale IP and bind to `0.0.0.0:3100`. No socat required.

If you get a hostname error when accessing via Tailscale IP:
```bash
cd /path/to/paperclip && pnpm paperclipai allowed-hostname <TAILSCALE_IP>
# Then restart paperclip
```

**Do NOT use socat** — `--bind lan` handles binding natively.

## Notes
- Server listens on `0.0.0.0:3100` when started with `--tailscale-auth`
- Uses embedded PGlite in dev (no `DATABASE_URL` needed)
- Plugins load and UI serves when using `pnpm dev:once`
- For legacy socat-based exposure (not recommended), see `references/tailscale-expose-socat.md`

## Troubleshooting
- **systemd keeps restarting Paperclip:** Your `pkill` calls keep failing because a `systemctl --user` service auto-restarts the process. Check with `systemctl --user list-units --type=service | grep paperclip`. Stop with `systemctl --user stop paperclip.service`. The service unit is at `~/.config/systemd/user/paperclip.service`.
- **"Invalid config: server.bind: Invalid enum value":** The config at `~/.paperclip/instances/default/config.json` has `"bind": "0.0.0.0"` which is no longer valid. Change to `"bind": "lan"`.
- **"Hostname X is not allowed":** Add the Tailscale IP via `pnpm paperclipai allowed-hostname <IP>` or edit the `allowedHostnames` list in `config.json` directly. Restart after.
- **Missing binaries:** Ensure `opencode` and `codex` are in the `$PATH` of the execution environment. Append `/usr/local/bin` to `~/.bashrc` if necessary.
- **Heartbeat failures:** Check if `OPENAI_API_KEY` is bound to the agent in the Paperclip UI; use `resolveExecutionRunAdapterConfig` logs to debug secret resolution.
- **Database issues:** If the database shuts down, ensure the server has clean shutdown access; remove stale lock files (`*.lock`) in `~/.paperclip/instances/default/db/`.
- **Server Shutdowns:** When the DB crashes, it may leave behind stale lock files in the DB directory. Always check for `*.lock` and remove them before restarting the server.


On modern Ubuntu (24.04+), the bundled embedded PostgreSQL binary requires `libicui18n.so.60` which is not available. The system has `libicu74`. Extracting the .deb from Ubuntu 20.04 (focal) works:

```bash
wget http://archive.ubuntu.com/ubuntu/pool/main/i/icu/libicu60_60.2-3ubuntu3.2_amd64.deb
mkdir -p icu60-extract && dpkg-deb -x libicu60_60.2-3ubuntu3.2_amd64.deb icu60-extract/
mkdir -p ~/.local/lib
cp icu60-extract/usr/lib/x86_64-linux-gnu/libicu{data,i18n,uc,le,tu,io}.so.60.2 ~/.local/lib/
cd ~/.local/lib && for f in *.60.2; do ln -sf "$f" "${f%.60.2}.60"; done
```

Then start Paperclip with:
```bash
LD_LIBRARY_PATH=$HOME/.local/lib pnpm dev:once
```

Or set `LD_LIBRARY_PATH` permanently in the systemd service / screen session.