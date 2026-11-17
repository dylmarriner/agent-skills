# Finding Remote Machines on the Tailnet

When the user references a machine by nickname (e.g. "lin", "server", "gpu", "work") and you need to access it, use this discovery pipeline.

## Step 1: List All Tailscale Nodes

```bash
tailscale status
```

Sample output:
```
100.91.55.113    lin-hp-pavilion-laptop-15-cs0xxx-1  tagged-devices    linux  active; direct 118.148.153.166:6699
100.83.46.118    lin-hp-pavilion-laptop-15-cs0xxx    inhumanekiller22@ linux  offline, last seen 67d ago
100.75.23.127    macuntu                             inhumanekiller22@ linux  active; relay "syd"
```

## Step 2: Match Hostname to Nickname

- `tailscale status | grep -i <nickname>` — matches any machine containing the substring
- Multiple matches are common (e.g., two "lin-hp-pavilion-..." entries). Pick the **active** one.
- Look for the `active` keyword vs `offline, last seen X ago`
- Active nodes with `direct` connections are fastest; `relay` connections work but are slower

## Step 3: Try SSH with Different Usernames

The local username often differs from the remote one. Try systematically:

```bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes <ip> "hostname && whoami"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes <user>@<ip> "hostname && whoami"
```

The `tailscale status` third column shows the owner email — the part before `@` is a good username guess.

## Step 4: Check What's on the Remote

```bash
ssh user@ip "ls -la /home/<user>/Downloads/"
ssh user@ip "unzip -l /path/to/archive.zip | head -30"
ssh user@ip "du -sh /path/to/files/*"
```

## Step 5: Transfer Files

```bash
scp user@ip:/remote/path /local/path                    # Small files
rsync -avP --partial user@ip:/remote/path /local/path/   # Large files with resume
rsync -avP --partial -e ssh user@ip:/remote/dir/ /local/dir/  # Directories
```

## Pitfalls

- **Machine nicknames are arbitrary** — the user may call a machine by a name that doesn't appear verbatim in tailscale status. Try partial matches.
- **Two machines, same owner** — One is often tagged (`tagged-devices`) and one user-owned. The tagged one may have different SSH permissions.
- **Direct vs Relay** — Relay transfers are slow. Retry or wait for a direct connection.
- **ssh-add may be needed** — If `ssh-add -l` shows no identities, run `ssh-add ~/.ssh/id_ed25519` first.
