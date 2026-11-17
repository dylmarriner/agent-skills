# Local Samba Server Troubleshooting

## When clients can't connect to a Samba server running on this machine

### Step 1 — Check daemon status

Both `smbd` (SMB protocol) and `nmbd` (NetBIOS name resolution) need to be running:

```bash
sudo systemctl status smbd nmbd --no-pager
```

If either is `inactive (dead)`:
```bash
sudo systemctl start smbd nmbd
sudo systemctl enable smbd nmbd   # persist across reboots
```

### Step 2 — Check NetBIOS name length (most common nmbd killer)

The NetBIOS name defaults to the system hostname, which is **capped at 15 characters**. Any hostname over 15 chars causes nmbd to fail silently — service says "active" briefly then dies.

```bash
hostname | wc -c       # count chars (+1 for newline)
hostname -s | wc -c    # count chars only
```

If > 15, set an explicit short NetBIOS name in `/etc/samba/smb.conf`:

```ini
[global]
    netbios name = KUBUNTUX   # or any name ≤ 15 chars
```

Validate config after editing:
```bash
sudo testparm -s       # check for warnings/errors
```

### Step 3 — Check /run/samba directory

Samba needs `/run/samba` to exist for its PID and lock files. If missing:
```bash
sudo mkdir -p /run/samba
```

This directory is created by tmpfiles.d on distros that configure it, but may not exist after fresh installs or container transitions.

### Step 4 — Verify config is loadable

```bash
sudo testparm -s       # shows parsed config, reports warnings
```

### Step 5 — Check firewall

SMB needs these ports open: 137/udp, 138/udp, 139/tcp, 445/tcp.

If using UFW:
```bash
sudo ufw status | grep -E '137|138|139|445'
```

**Tailscale-only access (default on this host):** SMB ports are restricted to the Tailscale interface — clients must connect via Tailscale IP (100.x.x.x):
```bash
sudo ufw allow in on tailscale0 to any port 137 proto udp comment 'samba-nb'
sudo ufw allow in on tailscale0 to any port 138 proto udp comment 'samba-dg'
sudo ufw allow in on tailscale0 to any port 139 proto tcp comment 'samba-sess'
sudo ufw allow in on tailscale0 to any port 445 proto tcp comment 'samba-smb'
```

**Adding LAN access for WiFi clients (Android phone, laptop on same subnet):** When a client on the local WiFi (e.g. 192.168.1.x) can't connect, add UFW rules for the LAN subnet. Same ports but without the `in on tailscale0` binding:
```bash
sudo ufw allow from 192.168.1.0/24 to any port 445 comment 'samba-smb-lan'
sudo ufw allow from 192.168.1.0/24 to any port 139 comment 'samba-nb-lan'
```
After adding LAN rules, re-add the server in the client app using the LAN IP (e.g. `192.168.1.225`) as host. Delete any cached failed connection first (long-press → delete).

**CX File Explorer SMB connection flow:** The app has NO separate "Share name" field on the add-server screen. After authenticating with username+password, it shows a list of available shares — tap the desired one. If the server doesn't appear in LAN scan, use Manual Input and enter the IP as Host.

### Step 6 — Verify with smbclient

List available shares (anonymous/guest):
```bash
smbclient -L //localhost -N
```

List shares authenticated:
```bash
smbclient -L //localhost -U <username>%<password>
```

Test guest access to a **specific share** (useful when the share appears in the browse list but guest connections are denied):
```bash
echo "ls" | smbclient //localhost/<share> -N
```
A working guest share drops you into an `smb: \>` prompt. A denied share returns `NT_STATUS_ACCESS_DENIED` or `NT_STATUS_LOGON_FAILURE`.

### Step 7 — Check Samba user database

Users must be in the Samba password DB, separate from system /etc/passwd:
```bash
sudo pdbedit -L       # list Samba users
```

If user is missing:
```bash
sudo smbpasswd -a <username>
```

### Step 8 — Diagnose share-level access issues

When a client can **see** the share name in the browse list but **can't open it**:

**8a — Check who's actually connected (user mapping)**

```bash
sudo smbstatus
```

Look at the `Username` column. If all clients show as `nobody` (guest), and the share has `valid users = <username>`, those guest connections are blocked even though the share is visible.

Common scenario: media players (TVs, Apple TV, Roku, Android boxes) connect as guest with no authentication. They can browse share names but get access denied on any share without `guest ok = yes`.

**8b — Compare working vs broken share config**

If one share (e.g. `[DEVELOPMENT1]`) works and another (`[videos]`) doesn't, compare them directly. The key difference is almost always:

| Setting | Working share | Broken share |
|---------|--------------|--------------|
| `guest ok` | `yes` | `no` or missing |
| `valid users` | absent (or inclusive) | `kubuntux` (or restrictive) |

```bash
sudo testparm -s 2>/dev/null | grep -A10 '\[share_name\]'
```

**8c — The `map to guest + valid users` interaction**

When `map to guest = Bad User` is set globally:
- A client that sends no credentials or bad credentials gets mapped to `nobody` (guest)
- If the share has `guest ok = no` (default), the guest user is denied
- If the share also has `valid users = kubuntux`, the guest user fails that check too
- Result: client sees the share name but gets access denied when trying to open it

**Fix**: Either add `guest ok = yes` to the share, or configure the client to authenticate with valid credentials.

### Step 9 — Gracefully reload config

After editing `smb.conf`, reload without dropping active connections:

```bash
sudo systemctl reload smbd
# or
sudo smbcontrol smbd reload-config
```

Then verify the change with `sudo testparm -s` before testing.

### Common pitfalls

- **nmbd dies silently** on hostname > 15 chars — always check this first if nmbd won't stay up
- **/run/samba missing** after fresh install or systemd tmpfiles purge — creates during package install but may not persist
- **smbd/nmbd disabled** after OS upgrades — verify with `systemctl is-enabled`
- **smbclient -L prompts for password** — use `-N` for guest/anon listing, or pass credentials with `-U user%pass`
- **Guest connections see the share but can't open it** — most likely missing `guest ok = yes` on that specific share. Check with `sudo smbclient //localhost/<share> -N`. Compare against a working guest-share config.
- **smbstatus shows nobody users on all connections** — those are guest connections. If the share needs auth, the client must send valid credentials or the share must allow guests.
- **Invalid `write cache size` parameter** — newer Samba (4.19+) dropped this option. Remove the line from smb.conf to silence the warning.
