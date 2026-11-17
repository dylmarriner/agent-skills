---
name: hermes-install-troubleshooting
description: "Fix Hermes install: editable path, PEP 668, permissions."
version: 1.0.0
---

# Hermes Install Troubleshooting

Diagnose and repair Hermes CLI when `hermes` command fails at launch — import errors, permission denied, broken editable installs, or Python environment mismatches.

**PREFERENCE**: User Dylan prefers a CLEAN REINSTALL over patching an editable install. When fixing Hermes on a remote machine, do a full uninstall + fresh pip install + config transfer. Do NOT patch the editable finder unless the user explicitly greenlights that approach.

---

## Trigger

Use when:
- `hermes` crashes immediately with `Permission denied`, `ModuleNotFoundError`, or `ImportError`
- `hermes version` hangs or fails
- User says "hermes is broken on <host>" or "fix hermes on <machine>"
- An editable pip install's source path is inaccessible (e.g. installed as root, running as user)

## Diagnosis Steps

### 1. Check which hermes is running

```bash
which hermes
head -1 /usr/local/bin/hermes      # shebang — which Python?
pip3 show hermes-agent 2>&1
```

Key field: **`Editable project location`** — if present, this is an editable install. If the path is inaccessible to the current user, every import fails.

### 2. Check permissions on the source

```bash
ls -la /root/.hermes/hermes-agent/ 2>&1  # Expected failure for non-root: Permission denied
```

### 3. Check Python environment

```bash
which python3 && python3 --version
python3 -c "import sys; print(sys.path)"
```

### 4. Check PEP 668 (externally-managed-environment)

```bash
pip3 install --dry-run hermes-agent 2>&1 | grep -i "externally-managed\|PEP 668\|break-system"
```

---

## Fix: Editable Install Path/Permission Error

**Symptom**: `hermes version` → `Permission denied: '/root/.hermes/hermes-agent/hermes_cli/__init__.py'`

Root cause: Hermes installed with `pip install -e` — the editable finder records absolute paths. If the running user can't read those paths, imports fail.

1. **Copy source to user-readable location**
```bash
sudo cp -a /root/.hermes/hermes-agent /home/<user>/.local/share/hermes-agent
sudo chown -R <user>:<user> /home/<user>/.local/share/hermes-agent
```

2. **Patch the editable finder**
```bash
sudo sed -i 's|/root/\.hermes/hermes-agent/|/home/<user>/.local/share/hermes-agent/|g' \
  /usr/local/lib/python3.11/dist-packages/__editable___hermes_agent_*_finder.py
```

3. **Verify**
```bash
hermes version
timeout 15 hermes help 2>&1 | head -5
```

---

## Fix: PEP 668 (externally-managed-environment)

**Symptom**: `pip install` → `error: externally-managed-environment`

| Option | Command | Use Case |
|--------|---------|----------|
| --break-system-packages | `sudo pip3 install --break-system-packages hermes-agent` | Quick system-wide fix |
| --user | `pip3 install --user hermes-agent` | Avoids PEP 668 entirely |
| venv | `python3 -m venv ~/hermes-venv && ~/hermes-venv/bin/pip install hermes-agent` | Cleanest isolation |

**Pitfall: ~/.local/bin not on PATH**. On Debian/Pi OS, pip installs CLI entry points to `~/.local/bin/` which is not in the default PATH. Fix:

```bash
sudo ln -sf ~/.local/bin/hermes /usr/local/bin/hermes
sudo ln -sf ~/.local/bin/hermes-acp /usr/local/bin/hermes-acp
# Also add to .bashrc:
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
```

SSH caveat: non-interactive SSH doesn't source .bashrc. Always prefix remote cmds with `export PATH=$HOME/.local/bin:$PATH && hermes`

---

## Fix: After Fresh Git Clone

```bash
cd /path/to/hermes-agent
pip install -e .   # editable install — verify path is readable
```

---

## Fix: Clean Reinstall + Full Config Transfer to Remote Machine

Preferred over patching an editable install. Use when setting up Hermes on a new remote machine or recovering a broken install on one.

### 1. Clean removal of old install

```bash
# Remove old binary
sudo rm -f /usr/local/bin/hermes

# Remove editable-install debris
sudo rm -rf /usr/local/lib/python3.11/dist-packages/hermes_agent*
sudo rm -rf /usr/local/lib/python3.11/dist-packages/__editable__*
sudo find /usr/local/lib/python3.11/dist-packages -name "*hermes*" -delete 2>/dev/null
```

### 2. Fresh install

```bash
pip3 install --force-reinstall --break-system-packages hermes-agent
```

On Pi OS/aarch64: may pull wheels from piwheels.org. Add `--no-deps` if the dependency resolver starts pin-battling, then let it resolve fresh.

### 3. Symlink to PATH

```bash
sudo ln -sf ~/.local/bin/hermes /usr/local/bin/hermes
sudo ln -sf ~/.local/bin/hermes-acp /usr/local/bin/hermes-acp
```

### 4. Transfer config from source machine (e.g. lin)

On the source machine, pack the essential Hermes profile:

```bash
cd ~/.hermes
tar czf /tmp/hermes-config.tar.gz \
  --exclude=sessions --exclude=image_cache --exclude=audio_cache \
  --exclude=cache --exclude=checkpoints --exclude=codegraph \
  --exclude=sandboxes --exclude=lsp --exclude=logs \
  --exclude=learning --exclude=mesh --exclude=kanban \
  --exclude=tokenjuice --exclude=hermes-agent \
  --exclude=state.db --exclude=state.db-shm --exclude=state.db-wal \
  --exclude=node_modules --exclude='*.sync-conflict-*' \
  config.yaml .env auth.json SOUL.md AGENTS.md USER.md \
  skills plugins cron memories scripts auth bin pairing hooks
```

SCP it over:

```bash
scp /tmp/hermes-config.tar.gz <user>@<host>:/tmp/
```

### 5. Extract on remote

```bash
# Backup existing first
mv ~/.hermes ~/.hermes.bak-$(date +%Y%m%d_%H%M%S)
mkdir -p ~/.hermes
cd ~/.hermes
tar xzf /tmp/hermes-config.tar.gz
```

### 6. Fix stale paths in config.yaml

If config was copied from a different machine (e.g. lin → rabuntu), replace old home paths:

```bash
sed -i 's|/home/lin/|/home/<remote-user>/|g' ~/.hermes/config.yaml
```

Check for remaining stale refs:
```bash
grep -n "home/lin\|/old-machine-name/" ~/.hermes/config.yaml
```

### 7. Verify

```bash
hermes version
hermes help 2>&1 | head -5
hermes config get tools 2>&1 | head -3
```

## Common Pitfalls

| Situation | Problem | Fix |
|-----------|---------|-----|
| Installed as root, run as user | Editable finder points to /root/ — Permission denied | Copy source + patch finder |
| Multiple Python versions | pip3 installs to wrong Python | Use `python3 -m pip install` to match versions |
| SSH PATH differs | `hermes: command not found` | `export PATH=$HOME/.local/bin:$PATH && hermes` |
| Editable source deleted | ImportError | Reinstall: `pip install hermes-agent` |
| PEP 668 blocks | `externally-managed-environment` | --break-system-packages or --user or venv |
| Corrupt metadata | Non-editable install still broken | `pip3 install --force-reinstall --no-deps hermes-agent` |

## Verification

```bash
hermes version
timeout 15 hermes help 2>&1 | head -5
pip3 show hermes-agent 2>&1 | grep -E "Location|Editable|Version"
