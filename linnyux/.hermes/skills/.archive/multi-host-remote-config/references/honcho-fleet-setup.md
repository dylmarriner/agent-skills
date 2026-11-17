# Honcho Cloud Memory — Fleet Setup Walkthrough

Configuring Honcho cloud memory on 3 machines (macuntu, kubuntux, rabuntu) via SSH.

## Task Summary

Each machine needed:
- `~/.honcho/config.json` with API key + base URL
- Hermes `memory.provider` set to `honcho`
- `HONCHO_API_KEY` env var in `~/.hermes/.env`
- Gateway restart if running

## The Script

```bash
#!/usr/bin/env bash
# Usage: honcho-setup.sh <user> <host>
USER="$1"
HOST="$2"
API_KEY="hch-v3-ae8j60u5f7zp9ock3vbfocy5xu7l97zgaz8t1tkf8h6rw84fulww479phbhkr275"
BASE_URL="https://api.honcho.dev"

# Step 1: Create ~/.honcho directory
ssh "$USER@$HOST" "mkdir -p ~/.honcho"

# Step 2: Write config.json via base64 to avoid quoting issues
CONFIG_B64=$(printf '{"api_key":"%s","base_url":"%s"}' "$API_KEY" "$BASE_URL" | base64 -w0)
ssh "$USER@$HOST" "echo '$CONFIG_B64' | base64 -d > ~/.honcho/config.json"

# Step 3: Verify config
ssh "$USER@$HOST" "cat ~/.honcho/config.json"

# Step 4: Update Hermes config
HAS_HERMES=$(ssh "$USER@$HOST" "test -f ~/.hermes/config.yaml && echo yes || echo no")
if [ "$HAS_HERMES" = "yes" ]; then
  ssh "$USER@$HOST" "hermes config set memory.provider honcho"
  ssh "$USER@$HOST" "hermes config set HONCHO_API_KEY '$API_KEY'"
fi

# Step 5: Restart gateway if running
if ssh "$USER@$HOST" "systemctl --user status hermes-gateway 2>/dev/null >/dev/null"; then
  ssh "$USER@$HOST" "systemctl --user restart hermes-gateway"
fi
```

## Edge Cases Encountered

### 1. macuntu — `hermes` CLI not on PATH

**Symptom:** Script ran but `hermes config set` silently failed ("bash: line 1: hermes: command not found").

**Root cause:** Hermes installed as an editable pip package at `~/.hermes/hermes-agent/` but no `hermes` binary in PATH.

**Fix:** Edit config.yaml + .env directly via Python/SSH rather than relying on the CLI:

```bash
ssh macuntu@host 'python3 -c "
import yaml
with open(\"/home/macuntu/.hermes/config.yaml\") as f:
    cfg = yaml.safe_load(f)
cfg[\"memory\"][\"provider\"] = \"honcho\"
with open(\"/home/macuntu/.hermes/config.yaml\", \"w\") as f:
    yaml.dump(cfg, f)
"'
echo 'HONCHO_API_KEY=<key>' >> /home/macuntu/.hermes/.env
```

Then restart gateway via `systemctl --user restart hermes-gateway`.

### 2. macuntu — Pre-existing stale HONCHO_API_KEY

**Symptom:** `.env` already had `HONCHO_API_KEY` with a different value. The append (`echo >>`) said "already set" and skipped the write.

**Fix:** Overwrite with `sed`:
```bash
sed -i 's|^HONCHO_API_KEY=.*|HONCHO_API_KEY=<correct-key>|' ~/.hermes/.env
```

### 3. rabuntu — Config written to wrong directory

**Symptom:** Script claimed to write `/root/.honcho/config.json` and verified its content, but a subsequent SSH check showed the directory didn't exist.

**Root cause:** The script ran as root but the `~` expansion in the heredoc or base64 pipeline may have resolved differently depending on how the shell was invoked (login vs non-login, su vs direct SSH).

**Fix:** Re-create explicitly targeting `/root/.honcho/`:
```bash
ssh root@host 'mkdir -p /root/.honcho'
ssh root@host 'printf '"'"'{"key":"value"}'"'"' > /root/.honcho/config.json'
```

### 4. rabuntu — Broken Python editable install

**Symptom:** `hermes` CLI crashed with `PermissionError: [Errno 13] Permission denied` on `hermes_cli/__init__.py`.

**Root cause:** Files under `/root/.hermes/hermes-agent/` had incorrect ownership/permissions for the editable install finder.

**Fix:** `chown -R root:root /root/.hermes/hermes-agent/` — restored readability, then `hermes config set` worked.

### 5. kubuntux — YAML grep showed no `provider` line

**Symptom:** `grep -A5 "^memory:" ~/.hermes/config.yaml` showed the memory section but no `provider` line. Yet Python yaml parser showed `provider: honcho`.

**Root cause:** The `hermes config set` command appended the `provider` key to the memory section but in a position later in the file. `grep -A5` only captured the first 5 lines after the first `memory:` match. The YAML parser merged both the early and late sections.

**Lesson:** Always use Python yaml parser for verification, not grep:
```python
import yaml
with open("config.yaml") as f:
    cfg = yaml.safe_load(f)
print(cfg.get("memory", {}).get("provider", "NOT SET"))
```

## Verification Commands

```bash
# Check all three nodes from one place
for host in macuntu kubuntux rabuntu; do
  echo "=== $host ==="
  ssh "$host" 'grep -A3 "^memory:" ~/.hermes/config.yaml | grep provider'
  ssh "$host" 'grep HONCHO_API_KEY ~/.hermes/.env'
  ssh "$host" 'cat ~/.honcho/config.json'
done
```
