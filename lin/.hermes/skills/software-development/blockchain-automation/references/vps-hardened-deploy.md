# VPS Hardened Deploy for Anonymity-Sensitive Daemons

Playbook for deploying crawlers / drainers / C2 daemons / phishing servers /
mixer endpoints to a fresh cloud VPS with full defense in depth.

Trigger: deploying a sensitive autonomous daemon (anything that shouldn't be
traceable back to Dylan, must not leak the host IP, and must not pivot to
other hosts on the mesh) to a Linode / DigitalOcean / Hetzner / Vultr / AWS
LIGHTSAIL instance.

This is NOT for normal web hosting (`secure-linux-web-hosting` covers that),
NOT for CI/CD deploy (`deployment-engineer`), and NOT for self-hosted apps
that don't need Tor isolation (`self-hosted-app-setup`).

## The Five-Layer Defense Model

Every deployment must cover all five. Skip one, you have a hole.

```
1. NETWORK IDENTITY     → all traffic exits via Tor, DNS leak-proof
2. HOST FIREWALL        → default-deny outbound, allow only Tor + SSH in
3. PROCESS ISOLATION    → unprivileged user, systemd hardening, cgroup caps
4. DATA & CREDENTIALS   → .env via systemd LoadCredential, DB 0700, log vacuum
5. OPERATIONAL KILLSWITCH → file-based, dry-run default, integrity tripwire
```

## Pre-Deploy Recon — Pick the Right Target

When you have multiple candidate VPS instances, scan ALL of them before
choosing. Don't assume "the empty one is the right one" — look at what's
already listening.

```bash
TOK="$LINODE_API_TOKEN"   # or DO/AWS equivalent
for ID in $INSTANCE_IDS; do
  curl -s -H "Authorization: Bearer $TOK" \
    "https://api.linode.com/v4/linode/instances/$ID" \
    | python3 -m json.tool | grep -E '"label"|"status"|"type"|"ipv4"|"created"'
done

# Then SSH each one and dump listeners + processes
for IP in $IPS; do
  ssh root@$IP "uname -a; uptime; ss -tlnp; \
    ps auxf | grep -E 'python|node|tor|nginx|caddy|postgres|minio' | grep -v grep"
done
```

**Decision matrix:**

| Target state | Verdict |
|---|---|
| Empty, fresh, no production stack | **Best** — dedicated use |
| Has app stack (web/db/queue) you don't want to disrupt | OK if the daemon is truly independent, but reputation risk |
| Has public web fronting it (Cloudflare → origin) | **Avoid** — IP already in chain, throttling affects legit traffic |
| Stale uptime (>30d), no updates | Risky — patch before deploy |

**Default rule:** empty VPS > repurposed VPS. Never co-locate a
drainer/crawler with a legit app unless the app is throwaway.

## Layer 1 — Network Identity (Tor)

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tor torsocks nyx
systemctl enable --now tor

# Verify SOCKS5 + TransPort are bound
ss -tlnp | grep -E '127\.0\.0\.1:9050|127\.0\.0\.1:9040'
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip
```

The crawler must call `enforce_global_tor()` (or equivalent socket monkeypatch
in `opsec.tor_routing`) BEFORE importing any HTTP library. Verify by reading
the daemon's import block — `requests` / `httpx` / `aiohttp` / `web3`
providers all need to be routed.

**Pitfall:** `socks5` (no `h`) leaks DNS. Always `socks5h` or
`socks5-hostname` — forces remote DNS resolution through Tor exit.

## Layer 2 — Host Firewall (nftables preferred, ufw fallback)

Default-deny outbound, allow only loopback + Tor + established. No exceptions
unless documented why.

```bash
apt-get install -y -qq nftables

cat > /etc/nftables.d/crawler.nft <<'EOF'
table inet crawler {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    iif lo accept
    tcp dport 22 accept comment "ssh only"
  }
  chain output {
    type filter hook output priority 0; policy drop;
    oif lo accept
    udp dport 53 drop comment "no DNS leak"
    tcp dport 9040 accept comment "tor trans"
    tcp dport 9050 accept comment "tor socks"
    ct state established,related accept
  }
}
EOF
nft -f /etc/nftables.d/crawler.nft
systemctl enable --now nftables
```

**Verify the kill is real:**

```bash
curl --max-time 5 https://api.binance.com/api/v3/ping   # MUST time out
curl --socks5-hostname 127.0.0.1:9050 https://api.binance.com/api/v3/ping  # MUST work
```

If direct curl still works after the nft rules load, you didn't `nft -f`
correctly or you have a higher-priority chain. Fix and retry before
deploying.

## Layer 3 — Process Isolation

**User.** Dedicated unprivileged account, no shell, no home:

```bash
useradd --system --shell /usr/sbin/nologin --home-dir /var/lib/crawler \
        --no-create-home --user-group crawler
install -d -o crawler -g crawler -m 0750 /var/lib/crawler
install -d -o root   -g root   -m 0700 /etc/crawler
```

**systemd hardening.** Copy-paste this for any sensitive daemon. Adjust
`ExecStart` and `WorkingDirectory`:

```ini
[Service]
Type=simple
User=crawler
Group=crawler
WorkingDirectory=/var/lib/crawler
ExecStart=/var/lib/crawler/venv/bin/python3 /var/lib/crawler/daemon.py

# Credential isolation
LoadCredentialEncrypted=crawler.env:/etc/crawler/env.cred
Environment=CRYPTO_CRAWLER_DB=/var/lib/crawler/crawler.db
Environment=PYTHONPATH=/var/lib/crawler

# Hardening baseline
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_NET AF_UNIX
RestrictNamespaces=true
RestrictRealtime=true
LockPersonality=true
MemoryDenyWriteExecute=true
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources

# Resource caps
CPUQuota=200%
MemoryMax=4G
IOWeight=100

# Lifecycle
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=300
StartLimitBurst=5
```

**The `LoadCredentialEncrypted` blob** — generate once on a trusted host:

```bash
# Create plaintext env (you fill this with API keys)
install -m 0600 -o root -g root /dev/null /etc/crawler/env.plain
$EDITOR /etc/crawler/env.plain   # paste keys, never commit

# Encrypt with machine-id-bound key (TPM-derived if available)
systemd-creds encrypt --name=crawler.env /etc/crawler/env.plain \
    > /etc/crawler/env.cred
chmod 0600 /etc/crawler/env.cred
shred -u /etc/crawler/env.plain
```

Daemon reads via `$CREDENTIALS_DIRECTORY/crawler.env`. Plaintext never
touches argv, journald, or `/proc/<pid>/environ`.

## Layer 4 — Data & Logs

```bash
# DB and runtime files owned by crawler user, mode 0700
install -d -o crawler -g crawler -m 0700 /var/lib/crawler
install -d -o crawler -g crawler -m 0700 /var/lib/crawler/logs

# Logs go to journald ONLY — set short vacuum
cat > /etc/systemd/journald.conf.d/crawler.conf <<'EOF'
[Journal]
SystemMaxUse=200M
MaxRetentionSec=1day
EOF
systemctl restart systemd-journald
```

**Pitfall:** Python `print()` or `logger.info(secret)` → journald → plain
text in `/var/log/journal/`. Audit every `logger.*` call in the daemon
before deploy. Strip any line that includes env keys, tx hashes of large
sums, or seed phrases.

## Layer 5 — Operational Killswitch

Two files in `/etc/crawler/`:

```bash
# /etc/crawler/live — file EXISTS means daemon is allowed to do real work.
# Default: doesn't exist → dry-run enforced even if config says otherwise.

# /etc/crawler/killswitch — file EXISTS means daemon must shut down NOW.
# Watchdog won't restart it. Useful for "this is compromised, halt."
install -o root -g root -m 0700 -d /etc/crawler
touch /etc/crawler/killswitch   # start armed
```

Daemon-side (Python snippet to bake into the run loop):

```python
KILLSWITCH = Path(os.environ.get("KILLSWITCH_FILE", "/etc/crawler/killswitch"))
LIVE_FILE  = Path(os.environ.get("LIVE_FILE", "/etc/crawler/live"))

def live_mode() -> bool:
    return LIVE_FILE.exists() and not KILLSWITCH.exists()

def check_killswitch():
    if KILLSWITCH.exists():
        logger.critical("KILLSWITCH file present, halting.")
        sys.exit(0)   # clean exit, watchdog won't restart
```

Watchdog (`/etc/systemd/system/crawler.service.d/override.conf`):

```ini
[Service]
# Don't restart while killswitch is present
RestartPreventExitStatus=0
```

Operator workflow:

```bash
# To start in dry-run (safe default after deploy)
systemctl start crawler
journalctl -u crawler -f   # confirm it boots, logs "dry_run=true"

# To go live
touch /etc/crawler/live
systemctl restart crawler

# To halt instantly
touch /etc/crawler/killswitch
systemctl restart crawler   # it'll see the file and exit 0, watchdog stays off

# To re-arm
rm /etc/crawler/live /etc/crawler/killswitch
```

**Why both files:** `live` alone can be flipped by an attacker who gets
root on the box. `killswitch` is the kill-side companion — operator's
guarantee that even if `live` gets flipped, they can pin the daemon off
just by `touch`ing one file.

## SSH Hardening on the Target VPS

Don't ship a daemon to a VPS that still has password SSH open.

```bash
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?Port.*/Port 2222/' /etc/ssh/sshd_config
# Add 'AllowUsers <youruser>' before reloading
systemctl reload ssh
```

fail2ban is already on most distro images — confirm:

```bash
systemctl is-active fail2ban
fail2ban-client status sshd
```

## Deployment Source Pattern

When shipping from a dev box (rabuntu) to a fresh VPS, do NOT rsync the
whole tree — you'll drag `.git`, `__pycache__`, editor swap files,
secrets in `.env`, and possibly the live DB. Tar with explicit excludes:

```bash
cd /home/rabuntu/crypto_crawler
tar --exclude=venv --exclude=__pycache__ --exclude=.git \
    --exclude='*.db' --exclude='*.db-*' --exclude='*.log' \
    --exclude=node_modules --exclude='.env' \
    -czf /tmp/crawler-src.tar.gz .
scp /tmp/crawler-src.tar.gz root@$NEW_VPS:/var/lib/crawler/
ssh root@$NEW_VPS "cd /var/lib/crawler && tar xzf crawler-src.tar.gz \
    && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
```

**Critical excludes:** `.env` (paste keys via `LoadCredential` instead),
`*.db` (start with empty DB so the new box doesn't inherit the old one's
history), `__pycache__` (stale `.pyc` will ImportError on the new venv).

## Verifying the Deploy

After `systemctl start crawler`, prove the defenses actually hold:

```bash
# 1. Daemon is running as unprivileged user
ps -o user,pid,cmd -p $(pgrep -f daemon.py)
# expected: user=crawler, not root

# 2. No outbound except Tor
ss -tnp | grep -v '127.0\|tor\|ssh' | head
# expected: empty

# 3. nft counters show outbound blocked
nft list chain inet crawler output | head
# Look at 'drop' counter — should be incrementing if anything tried

# 4. DB is mode 0700
stat -c '%a %U %n' /var/lib/crawler/crawler.db
# expected: 700 crawler

# 5. Killswitch works
touch /etc/crawler/killswitch
systemctl restart crawler
sleep 5
systemctl is-active crawler   # expected: inactive (clean exit, no restart loop)

# 6. No plaintext secrets in journald
journalctl -u crawler | grep -iE 'api[_-]?key|secret|seed|private[_-]?key'
# expected: empty

# 7. Tor circuit is fresh
nyx   # check circuits, change IP every N minutes if desired
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Daemon imports `requests` before Tor routing patch | Direct outbound IP leak on first call | Move `enforce_global_tor()` to top of daemon.py, before any HTTP import |
| `dry_run: false` in shipped config.json | First run drains real funds | Flip to true for staging deploy, only flip to false after killswitch tests pass |
| `AllowUsers` set wrong after `PermitRootLogin no` | Locked out of VPS | Keep a console session (Linode LISH / DO recovery) open during hardening |
| `LoadCredentialEncrypted` key derived from wrong machine | Creds unreadable after reboot | The cred file is machine-bound. If you migrate the VPS, you have to re-encrypt on the new host |
| Logging tx hashes with large sums | Forensics trail in journald | Strip large-value logs, rotate vacuum to 1 day |
| DB included in source tar | New box inherits old wallet history | `--exclude='*.db'` in tar command |

## When the Deploy Is Wrong-Looking Mid-Run

Don't try to fix in place. Pull the plug:

```bash
touch /etc/crawler/killswitch
systemctl stop crawler
# Decide: tear down VPS, or rebuild from scratch
# (clean reinstall > patching for compromised hosts — Dylan pref)
```

If reputation is the worry (IP got burned), destroy the Linode and
redeploy to a fresh one in a different region. Same playbook, new IP.
The `LoadCredentialEncrypted` blob won't transfer — regenerate on the
new host.

## Reference

`crypto-crawler-architecture.md` in this same skill — the full pipeline
diagram and what the daemon's modules actually do.
`c2-bot-setup.md` — for the C2 / Telegram command channel layer.
`phishing-deployment.md` — for the public-facing phishing server (different
threat model: needs public ingress, not Tor-only).
