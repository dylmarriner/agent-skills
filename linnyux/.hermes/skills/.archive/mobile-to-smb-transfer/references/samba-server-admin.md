# Samba Server Administration

Server-side fixes for SMB share accessibility issues.

## Common Error: NT_STATUS_BAD_NETWORK_NAME

This error means the share name is valid but the **underlying path doesn't exist**.

### Diagnosis
```bash
sudo testparm -s | grep -A2 '\[ShareName\]'
ls -la /path/from/config/
```

### Fix: Update share path
```bash
sudo sed -i 's|path = /old/path|path = /actual/path|' /etc/samba/smb.conf
sudo mkdir -p /srv/nas/main/media
sudo chown rabuntu:rabuntu /srv/nas/main/media
sudo smbcontrol smbd reload-config   # gracefu reload, no restart needed
```

### Verify
```bash
smbclient -U rabuntu%admin -c 'ls' //127.0.0.1/Main
smbclient -U rabuntu%admin -c 'put /tmp/test.txt test.txt; rm test.txt' //100.68.0.96/Main
```

## Common Error: NT_STATUS_LOGON_FAILURE
Samba password is separate from system password. Fix:
```bash
sudo pdbedit -L
sudo smbpasswd <username>
```

## Common Error: NT_STATUS_ACCESS_DENIED
Check `read only = No`, `valid users`, `force user`, and filesystem permissions:
```bash
sudo testparm -s | grep -A10 '\[ShareName\]'
ls -la /path/to/share/
```

## Config Reload (no client disconnect)
```bash
sudo smbcontrol smbd reload-config   # graceful
sudo systemctl restart smbd          # disconnects clients
```

## Hostname Resolution
Hostnames like `pi5-deflab` may not resolve. Use Tailscale IP:
```bash
smbclient //100.68.0.96/Main -U rabuntu%admin
```
