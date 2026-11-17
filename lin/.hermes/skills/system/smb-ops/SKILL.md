---
name: smb-ops
description: Diagnose, configure, and troubleshoot Samba SMB file shares. Covers auth patterns, config editing, password management, and connectivity checks.
trigger: User reports SMB share unavailable, connection denied, authentication failure, or "can't view" a share. Also triggered for setting up new shares or changing share permissions.
---

# SMB Ops

## Triggers
- "can't view / connect to SMB share"
- "SMB share not working"
- "setting up / changing SMB share"
- "SMB password / authentication"

## Diagnostic Workflow

### 1. Service health
```
systemctl status smbd --no-pager -l
```
Look for: active (running), no repeated restart loops.

### 2. Active connections
```
sudo smbstatus
```
Check: which clients are connected, as what user, to which share. If all connections show `nobody` / guest, the client isn't authenticating.

### 3. Config validity
```
sudo testparm -s
```
Shows the parsed effective config. Verify sections render with expected params.

### 4. Talk to the share directly
```
echo "exit" | smbclient "//<ip>/<share>" -U <user> 2>&1
echo "exit" | smbclient "//<ip>/<share>" -N 2>&1   # guest/anonymous
```
`-N` = no password (guest). `-U <user>` prompts for password.

### 5. SMB user database
```
sudo pdbedit -L -v
```
Shows Samba users and password last-set time. If `Bad password count` is climbing, wrong password.

### 6. Network
```
ss -tlnp | grep -E '(445|139)'
sudo ufw status | grep -E '(445|139)'
```
SMB must be listening on `0.0.0.0:445/139` (global) or the specific interface. UFW rules must allow it on the relevant interface.

## Share Auth Patterns

### Pattern A — Authenticated-only (like `[storage]`, `[videos]`)
```
[sharename]
   path = /some/path
   read only = no
   guest ok = no
   valid users = kubuntux
   force user = kubuntux
   force group = kubuntux
   create mask = 0755
   directory mask = 0755
```
- Client MUST provide `kubuntux` username + valid SMB password
- Guest connections (nobody) get NT_STATUS_ACCESS_DENIED
- Use this for private shares containing sensitive content

### Pattern B — Guest-allowed (like `[DEVELOPMENT1]`)
```
[sharename]
   path = /some/path
   read only = no
   guest ok = yes
   force user = kubuntux
   force group = kubuntux
   create mask = 0664
   directory mask = 0775
```
- No credentials needed — anonymous clients connect as `nobody`, Samba maps to `kubuntux` via `force user`
- Use this for media players, TVs, and devices that can't do SMB auth
- Drop `hosts allow = 100.64.0.0/10 127.0.0.1 ::1` to restrict to Tailscale + localhost

### How `map to guest = Bad User` interacts
- Global setting in `[global]` section
- When a client connects with an invalid/bad username → mapped to guest (nobody)
- If the share has `guest ok = no` + `valid users = kubuntux`, the guest-mapped nobody gets DENIED
- This is why clients that can't authenticate get "access denied" even though they can see the share name in the browse list

## Username Mapping (`smbusers`)

When a client connects with a username that doesn't match the Samba user (e.g., VLC sending `admin` instead of `kubuntux`), use a username map.

### File location
```
/etc/samba/smbusers
```

### Format — DIRECTION MATTERS
```
unix_user = client_alias
```
This line means: when a client connects as `client_alias`, treat them as Samba user `unix_user`.

**CORRECT** — map client `admin` to local user `kubuntux`:
```
kubuntux = admin
```

**WRONG** — `admin = kubuntux` means "map client `kubuntux` to local user `admin`" (which doesn't exist), causing `NT_STATUS_NO_SUCH_USER`:
```
admin = kubuntux   # backwards — will fail
```

### Enable in smb.conf
```
[global]
   username map = /etc/samba/smbusers
```

### Debugging username map issues
The log will show the mapping in auth events. Look for `mapped to`:
```
sudo sed -i '/^\\[global\\]/a\\   log level = 3' /etc/samba/smb.conf
sudo systemctl reload smbd
# test connection, then check:
sudo tail /var/log/samba/log.<client-ip>
# Look for: "mapped to [WORKGROUP]\\[mapped_user]"
```
After debugging, remove the log level line and reload:
```
sudo sed -i '/log level = 3/d' /etc/samba/smb.conf
sudo systemctl reload smbd
```

### Typical client usernames
| Client | Default Username |
|--------|-----------------|
| VLC for Android/desktop | Often `admin`, sometimes `kubuntux` |
| Kodi | Depends on SMB client config |
| Windows File Explorer | Current Windows login username |
| TVs / streaming sticks | Usually guest (no username sent) |

### DON'T use broad sed substitutions on smb.conf
```
# BAD — will match EVERY section in the file:
sudo sed -i 's/guest ok = no/guest ok = yes/' /etc/samba/smb.conf

# BAD — 'a' append after match adds the line after EVERY occurrence:
sudo sed -i '/guest ok = no/a\   valid users = kubuntux' /etc/samba/smb.conf
```
Both create duplicate lines and corrupt other sections.

### DO use full section rewrites
Use `sudo tee /etc/samba/smb.conf << 'EOF' ... EOF` to rewrite the entire file when changing share definitions. The file is small enough that this is safer than surgical sed.

### DO use reload, not restart
```
sudo systemctl reload smbd
```
Reload picks up config changes without dropping existing connections. Full restart is only needed if smbd itself crashed.

## Password Management

### SMB passwords are separate from system passwords
- Setting system `passwd` only syncs to SMB if `unix password sync = yes` AND the password was changed via `passwd` (not set via root)
- To set/reset SMB password interactively: `sudo smbpasswd <user>`
- To set non-interactively (pipe): `printf 'newpass\\nnewpass\\n' | sudo smbpasswd -s <user>`
- To check status: `sudo pdbedit -L -v` (shows `Password last set` and `Bad password count`)

### Inline password testing with smbclient
Pass username and password together to avoid prompts:
```
echo "exit" | smbclient "//<ip>/<share>" -U <user>%<password> 2>&1
```
- `NT_STATUS_LOGON_FAILURE` = bad password or user doesn't exist
- `NT_STATUS_ACCESS_DENIED` after apparently successful auth = username is being mapped to a non-existent user (check username map)
- `NT_STATUS_NO_SUCH_USER` = the effective user (after mapping) doesn't exist in Samba passdb

### When `NT_STATUS_LOGON_FAILURE` appears
1. Check `pdbedit -L -v` — is the password set at all?
2. Did the user enter the SMB password (not the system password)?
3. Reset with `sudo smbpasswd <user>` if needed

## Client-Side Mount (from another Tailscale/network machine)

When the SMB server is on a different machine (e.g. kubuntux) and you're mounting from another host (e.g. lin, macuntu):

### 1. Install CIFS utils on the client (first time)
```sh
sudo apt install -y cifs-utils
```

### 2. Create mount point
```sh
sudo mkdir -p /mnt/development1
```

### 3. Mount the share

**Guest access** (when `guest ok = yes` on the server):
```sh
sudo mount -t cifs //<server-tailscale-ip>/<share> /mnt/<mountpoint> \
  -o guest,uid=$(whoami),gid=$(whoami),iocharset=utf8,file_mode=0644,dir_mode=0755,noperm
```

**Authenticated access** (when `guest ok = no`):
```sh
sudo mount -t cifs //<server-ip>/<share> /mnt/<mountpoint> \
  -o username=kubuntux,uid=$(whoami),gid=$(whoami),iocharset=utf8,file_mode=0644,dir_mode=0755,noperm
```
This prompts for the SMB password. Use `password=<pass>` inline (in the option string) for automation — be careful not to leave it in shell history.

### 4. Verify
```sh
mount | grep cifs
ls /mnt/<mountpoint>
```

### 5. Persistent mount via fstab (optional)
Add to `/etc/fstab`:
```
//100.93.75.87/DEVELOPMENT1 /mnt/development1 cifs guest,uid=lin,gid=lin,iocharset=utf8,file_mode=0644,dir_mode=0755,noperm 0 0
```
Then `sudo mount -a` to test. For authenticated shares, use a credentials file:
```
//100.93.75.87/storage /mnt/storage cifs credentials=/etc/samba/credentials,uid=lin,gid=lin,iocharset=utf8,file_mode=0644,dir_mode=0755,noperm 0 0
```
With `/etc/samba/credentials` containing:
```
username=kubuntux
password=<smb-password>
```
And locked down: `sudo chmod 600 /etc/samba/credentials`

### Key CIFS mount options explained
| Option | Purpose |
|--------|---------|
| `guest` | No password (anonymous auth) — only works if `guest ok = yes` on server |
| `uid=<user>`, `gid=<user>` | Maps all remote files to this local user/group (avoids permission issues) |
| `file_mode=0644`, `dir_mode=0755` | Sets visible permissions for all files/dirs |
| `noperm` | Disables client-side permission checking (delegates all to server) |
| `iocharset=utf8` | Proper UTF-8 filename handling |
| `vers=3.1.1` | SMB protocol version (auto-negotiated if omitted) |

## Common Failure Modes

See also: `references/auth-debug-log-patterns.md` for annotated log examples from real debugging sessions.

| Symptom | Likely Cause |
|---------|-------------|
| See share in browse list, can't open it | `guest ok = no` + `valid users` — client is connecting as guest |
| `NT_STATUS_LOGON_FAILURE` | Wrong SMB password or user doesn't exist in Samba passdb |
| smbd keeps restarting | Config error (check `testparm`, look for "Unknown parameter" warnings) |
| Can't connect from Tailscale IP but works on LAN | UFW rule allows SMB on `tailscale0` specifically; check `ufw status` |
| "Anonymous login successful" but can't list | Share has `browseable = no` or `valid users` blocking guest |
| Connection works, files show but can't play on TV | Check file permissions on disk — need world-readable or `force user` mapping |
| VLC: `NT_STATUS_ACCESS_DENIED` after entering correct password | VLC may be sending a different username than expected — check smbstatus to see what username the client is actually sending, then add a `username map` entry |
