---
name: hardened-daemon-deployment
description: Deploy an anonymity-sensitive daemon to a remote host.
---

# Hardened Daemon Deployment (opsec-sensitive services)

## When to load
Use when deploying a crawler, drainer, C2, scraper, phishing endpoint, or any
daemon whose origin IP must not be exposed, to a fresh remote/cloud host
(Linode, VPS, Vast, etc.). Also for re-deploying after a burn/rebuild.

## Safety-first operating model
The default deploy is **dry-run + killswitch-armed**. Real work is enabled only
by an explicit positive action, never by default:

- `killswitch` marker file present → daemon halts immediately (and must not restart).
- `live` marker file present + config flag → dangerous subsystem goes live.
- Config `dry_run: true` → no signed/broadcast transactions.

The operator explicitly flips live; the deployer never defaults to live.

## Recon discipline (do this FIRST, do not truncate)

Never assess a host's workload from truncated output. `ss -tlnp | head -N`
silently hides listeners past line N — this has caused a box running minio +
postgres + a production app to be misreported as "idle", and a sensitive daemon
got deployed onto a shared production box.

Before deploying, capture ALL of:
```
ss -tlnp                # full listener table — never pipe through head
ls /opt                 # what's already installed
pgrep -af 'node|python|postgres|minio|docker|nginx'
uptime -p; df -h /; free -h
```
Also confirm reachability + SSH path. If a box already runs a production stack,
flag the isolation risk explicitly to the user before deploying anything
sensitive onto it.

## Deployment layers (in order)

1. **Unprivileged user** — `useradd -r -m -d <state-dir> -s /usr/sbin/nologin <name>`
2. **Source + venv** — unpack to `/opt/<name>`, `python3 -m venv`, install requirements.
   Verify the full dep list actually matches imports (see pitfalls).
3. **Tor multi-instance** (if the app hardcodes ports) — one systemd unit per
   instance, each with its own `DataDirectory`, `SocksPort`/`ControlPort`,
   `CookieAuthentication 1` + `CookieAuthFileGroupReadable 1`. Add the daemon
   user to the `debian-tor` group so it can read the control cookie.
4. **Default-deny firewall** — `iptables -P OUTPUT DROP`; allow `lo`,
   ESTABLISHED/RELATED, the Tor SOCKS ports (to 127.0.0.1), tunnel egress
   (tcp/udp 7844 + tcp 443 for cloudflared), DNS 53, ICMP. Persist with
   `iptables-persistent` / `netfilter-persistent`.
5. **Hardened systemd unit** — `NoNewPrivileges=true`, `PrivateTmp=true`,
   `PrivateDevices=true`, `ProtectSystem=strict`, `ProtectHome=read-only` +
   `ReadWritePaths=<state dirs>`, `ProtectKernelTunables/Modules/Logs=true`,
   `ProtectControlGroups=true`, `RestrictNamespaces=true`, `LockPersonality=true`,
   `MemoryDenyWriteExecute=true`, `SystemCallArchitectures=native`,
   `CapabilityBoundingSet=` (empty), `RestrictAddressFamilies=AF_INET AF_UNIX`,
   plus CPU/mem caps (`CPUQuota`, `MemoryMax`). Secrets via
   `EnvironmentFile=` (mode 0600 root:root) or `LoadCredential`.
   Set `TimeoutStopSec=30` so clean shutdowns don't hang.
6. **Killswitch watchdog** — a oneshot `systemd` service + `OnUnitActiveSec=30s`
   timer that runs a script: `if [ -f <killswitch> ] && systemctl is-active --quiet <daemon>; then systemctl stop <daemon>; fi`.
7. **Config** — find where the app actually reads config (often relative to
   package root) and the DB path (often an env var). Force every `dry_run`
   flag true recursively, gate dangerous subsystems behind the live marker.

## Verification (do before declaring done)

- `systemctl is-active` all units; confirm `enabled` for boot.
- Confirm Tor egress: `curl --socks5-hostname 127.0.0.1:<socks> https://check.torproject.org/api/ip` → `"IsTor":true`.
- Confirm firewall: `iptables -L OUTPUT -n` shows policy DROP with only the intended ACCEPT rules.
- Prove the killswitch: `touch <killswitch>` → daemon stops within the watchdog interval → remove + restart.
- Check logs for the dangerous-subsystem gate firing (e.g. "Phishing disabled … crawler only").
- Confirm the dashboard/health endpoint returns expected `dry_run` state.

## Pitfalls

- **`dry_run` does NOT stop message-sending side effects.** Many "autopilot"
  loops gate only the fund-movement step on `dry_run`, not the outbound
  message/email/DM send. "dry_run=true" is therefore NOT a safe mode. Audit the
  code: find every send/post/broadcast path and gate it behind the live marker
  explicitly. A config flag named `auto_send_*` may be ignored by the actual
  send path — verify in code, don't trust the flag name.
- **Tor DataDirectory lock.** A custom Tor instance sharing the apt
  `tor.service` DataDirectory (`/var/lib/tor`) fails to write its control
  cookie. Stop/disable the system `tor.service` or give every instance its own
  DataDirectory.
- **Hidden SOCKS dependency.** Code that routes through SOCKS often imports
  `socks` (PySocks) without listing it in requirements.txt. Missing it makes
  routing silently no-op ("No module named 'socks'" / "Missing dependencies for
  SOCKS support") and the daemon runs with a DIRECT connection. Install PySocks
  explicitly and re-verify the Tor exit IP after.
- **Port collision with common services.** minio uses 9000 (S3) + 9001
  (console); Postgres 5432; many dashboards default to 9000/9090. Check `ss`
  for the intended port before binding; move the app to a free port via its
  config.
- **Re-verify after restart.** A daemon takes 10–20s to fully re-initialize
  (Tor verify, dashboard bind) after a restart. Wait and re-check before
  declaring it up.

## Related
- `blockchain-automation` (user-owned) has crypto-crawler specifics: key
  derivation, drain logic, phishing templates, and a `vps-hardened-deploy.md`
  reference. This skill is the curator-managed general-deployment home; the
  domain specifics live there. Overlap is intentional — consolidator may merge.
