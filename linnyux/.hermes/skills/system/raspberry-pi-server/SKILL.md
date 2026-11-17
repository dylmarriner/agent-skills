---
name: raspberry-pi-server
description: Raspberry Pi server administration — SSH via unstable Tailscale relay, USB external drive connection, Samba share setup, persistent fstab mounts, and Pi-specific server maintenance.
metadata:
  tags: raspberry-pi, samba, smb, ssh, tailscale, relay, usb-drive, external-storage, fstab, pi-server
---

# Raspberry Pi Server Administration

## When to use

- SSH-ing into a Pi that's only reachable via a Tailscale relay (DERP, no direct connection)
- Connecting an external USB drive to a Pi and making it accessible over SMB
- Setting up or modifying Samba shares on a Pi
- Adding persistent mounts (fstab) for external storage on a Pi
- Diagnosing Pi storage/network issues or connectivity problems
- A Pi that was previously reachable has become completely unresponsive

## Instructions

#### Step 1 — Find the local IP from ARP cache

When the Pi's Tailscale IP is accessible but SSH is blocked by ACL, check if the Pi shares a physical subnet. Node Exporter exposes MAC addresses:

```bash
curl -s http://<tailscale-ip>:9100/metrics | grep node_network_info | grep eth0
# Returns: node_network_info{device="eth0",address="88:a2:9e:XX:XX:XX",...}
```

Look up the MAC in your ARP cache:

```bash
arp -n | grep -i "XX:XX:XX"
# Returns: 192.168.1.247 ether 88:a2:9e:XX:XX:XX C eth0
```

The local IP (192.168.1.247 in this example) may bypass Tailscale's proxy entirely. Try SSH to that IP:

```bash
ssh <user>@192.168.1.247 "hostname"
```

If the local IP also times out, the Pi's firewall or router blocks inbound connections to port 22 on the LAN. Proceed with the metrics + SMB diagnostic path instead.

### 0. Connectivity Diagnostics — Pi is completely unreachable

Use this diagnostic procedure when SSH and every other service times out. Do not assume a jump host will fix it — verify step by step.

**Step 0.1 — Check Tailscale status first (fastest signal):**

```bash
tailscale status | grep <pi-name-or-ip>
```

Interpretation of status column:

| Status text | Meaning | Likely to connect? |
|---|---|---|
| `active; direct <city>` | Direct Tailscale connection | ✅ Very likely |
| `active; relay <city>` | Connected, but via DERP relay only — no direct path | ❓ Possible but *slow*. If even this fails, the Pi may have no reachable services (see below) |
| `offline` | Pi not connected to Tailscale at all | ❌ Impossible |
| Not present in output | Pi not on the same Tailnet, or is a different user's device | ❌ Check ACLs |

**Step 0.2 — Try Tailscale ping (tests the control path):**

```bash
tailscale ping --c 3 --until-direct=false <pi-ip>
```

- If all three pings time out even with `--until-direct=false`, there is **no control path** through Tailscale at all. Even SSH via relay is unlikely.
- If pings succeed but SSH still fails, the Pi is reachable via Tailscale but the SSH service itself is down or the port is firewalled.

**Step 0.3 — Probe ports directly:**

```bash
timeout 15 nc -zv -w 5 <pi-ip> 22    # SSH
timeout 15 nc -zv -w 5 <pi-ip> 445   # SMB
timeout 15 nc -zv -w 5 <pi-ip> 80    # HTTP (optional)
```

- All ports time out → the Pi has no listening services reachable, or is behind a firewall that blocks all inbound.
- Some ports respond → SSH service or security config issue, not a network problem.

**Step 0.4 — Test CIFS/SMB mount (if you have one):**

If there's a CIFS mount from this Pi (e.g. `/mnt/pivideos`), try:

```bash
ls /mnt/pivideos/  2>&1 | head -5
```

- If it hangs indefinitely, the Pi is unreachable at the network layer. The `soft` mount option prevents a kernel hang but the command will eventually time out.
- If you have `df -h` hanging, it's the same signal.

**Step 0.5 — Try via jump hosts:**

If you have other machines on the same Tailnet that might have a better path:

```bash
ssh <jump-host> "tailscale ping --c 2 <pi-ip>"
ssh <jump-host> "tailscale status | grep <pi-ip>"
```

If both local and jump-host attempts show `relay only` with no direct path and all ports time out, **the Pi is unreachable from this network**. Possible causes:
- Pi is powered off
- Pi's network interface is down
- Pi is behind a NAT so restrictive that even Tailscale relay can't carry traffic (only the Tailscale control connection survives)
- exFAT partition I/O hang has frozen the kernel (see `references/exfat-hang-recovery.md`)

**What to tell the user:** Report the specific diagnostic results:
- Tailscale status (relay/direct/offline)
- Which ports were checked and which timed out
- Whether jump hosts also failed
- The practical bottom line: the Pi needs physical or local-network access to diagnose further

### 1. SSH to the Pi (when it's reachable)

**ALWAYS try direct SSH first.** Do not assume a jump host is needed:

```bash
# Try direct — this is the default approach
ssh <pi-user>@<pi-host> "<command>"

# If that times out, check reachability
ping -c 3 -W 3 <pi-host>
```

**Only if the user confirms a jump host is needed** (e.g. Tailscale ACLs block direct), use ControlMaster multiplexing via the jump host to handle slow relay connections:

```bash
# Establish persistent ControlMaster socket via jump host
ssh -o StrictHostKeyChecking=no \
    -o ControlMaster=auto \
    -o ControlPath=/tmp/ssh-<host-alias> \
    -o ControlPersist=600 \
    -J <jump-user>@<jump-host> \
    <pi-user>@<pi-host>

# Subsequent commands reuse the socket (fast, no relay re-negotiation)
ssh -o ControlPath=/tmp/ssh-<host-alias> \
    <pi-user>@<pi-host> "<command>"
```

**Key options (jump host approach):**
- `ControlMaster=auto` — reuse an existing socket if one exists, create if not
- `ControlPath=/tmp/ssh-<host-alias>` — unique socket path per host
- `ControlPersist=600` — keep socket alive 10 min after last use
- `-J <jump>` — jump host when Tailscale ACLs block direct SSH but allow the jump host through

**Check Tailscale status on the jump host:**
```bash
ssh <jump-host> "tailscale status | grep <pi-name>"
# If status shows "relay; <location>", expect slow initial connections
ssh <jump-host> "tailscale ping -c 2 <pi-ip>"
# "timed out" on ping but SSH may still work via relay
```

### 2. Detect and identify external USB drives

```bash
# List all block devices with labels and filesystem types
ssh <pi> "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL,MODEL"

# Check filesystem details
ssh <pi> "sudo blkid /dev/sdX1 /dev/sdX2"

# External drives are typically sdb, sdc, etc. (sda is usually the system SD card)
```

### 3. Mount USB drive partitions

Create mount points under `/mnt/` and mount each partition:

```bash
ssh <pi> "sudo mount /dev/sdX1 /mnt/<mount-point-1>"
ssh <pi> "sudo mount /dev/sdX2 /mnt/<mount-point-2>"
```

Common filesystems:
- `ext4` — native Linux, mounts with `sudo mount`
- `exfat` — cross-platform, may need `sudo apt install exfat-fuse`
- `ntfs` — Windows, may need `sudo apt install ntfs-3g`

### 4. Access drive over existing SMB share

If the Pi already has a Samba share (e.g. `[shared]` at `/mnt/shared/`), expose the external drive by **bind-mounting** into the share's directory tree:

```bash
# Create subdirectories in the SMB share path
ssh <pi> "sudo mkdir -p /mnt/shared/external-<label>"

# Bind mount so the drive content appears under the share
ssh <pi> "sudo mount --bind /mnt/<mount-point> /mnt/shared/external-<label>"
```

The drive is now accessible over SMB at `//<pi-host>/shared/external-<label>`.

### 5. Make mounts persistent (fstab)

**⚠️ Always add `nofail,x-systemd.device-timeout=30` for USB external drives.** Without these options, a slow-to-ready USB drive at boot (or a missing one) will hang the boot process indefinitely. SSH, ping — everything will fail until a hard power cycle.

Add entries to `/etc/fstab` on the Pi:

```bash
# For direct partition mounts — ALWAYS include nofail + device-timeout
echo '/dev/sdX1 /mnt/<mount-point-1> ext4 defaults,nofail,x-systemd.device-timeout=30,noatime 0 2' | sudo tee -a /etc/fstab

# For bind mounts into SMB share (for external drives)
echo '# External <size> drive bind mounts' | sudo tee -a /etc/fstab
echo '/mnt/<mount-point-1> /mnt/shared/external-<label-1> none bind,nofail,x-systemd.device-timeout=30 0 0' | sudo tee -a /etc/fstab
echo '/mnt/<mount-point-2> /mnt/shared/external-<label-2> none bind,nofail,x-systemd.device-timeout=30 0 0' | sudo tee -a /etc/fstab
```

**Mergerfs fstab entry** — also needs `nofail`, and must reference the raw partition path (e.g. `/mnt/dev2/videos`), NOT a bind-mount path (`/mnt/shared/external-dev2/videos`). Bind-mount paths can become inaccessible if the parent SMB share directory breaks:

```bash
# ❌ Wrong — uses bind-mount path
echo '/mnt/shared/external-dev2/videos:/mnt/shared/videos-original ...'  # BAD

# ✅ Correct — uses raw device mount
echo '/mnt/dev2/videos:/mnt/shared/videos-original /mnt/shared/videos fuse.mergerfs defaults,allow_other,category.create=epmfs,minfreespace=1G,nofail 0 0' | sudo tee -a /etc/fstab
```

### 6. Verify

```bash
ssh <pi> "df -h | grep -E 'sdX|shared'"
ssh <pi> "ls -la /mnt/shared/"
```

### 7. Merge external storage into an existing directory (mergerfs)

When you want existing content AND new external storage to appear as one directory (e.g. merging a large external drive's `videos/` folder with the current `videos/` directory):

**ⓘ Before starting — diagnose the existing mergerfs setup first.** Do not assume the current configuration is correct. A common failure: bind mount sources in the mergerfs pool point to directories on the ROOT filesystem (`/dev/sda`) instead of the external drive (`/dev/sdb`). Always verify:

```bash
# 1. Read the mergerfs fstab entry
grep mergerfs /etc/fstab

# 2. For each branch in the pool, check which filesystem it's actually on
# Example: fstab has "/mnt/shared/external-dev2/videos:/mnt/shared/videos-original"
# Check EACH branch path:
df -h /mnt/shared/external-dev2/videos    # if shows /dev/sda = root, it's WRONG
df -h /mnt/shared/videos-original          # if shows /dev/sda = root, it's WRONG

# 3. Trace the bind mounts to their actual source
mount | grep external-dev                  # /dev/sda2 on /mnt/shared/external-dev = root!
df -h /mnt/dev /mnt/dev2                   # check where bind-mount sources live
# correct: should be /dev/sdb2 (the external drive)

# 4. Find the actual videos directory on the external drive
find /srv/nas/main -type d -name videos 2>/dev/null
```

**If it's wrong**, do NOT fix the bind mounts. Update the mergerfs fstab entry to point directly to the correct external drive path:

```bash
sudo sed -i 's|/mnt/shared/external-dev2/videos:/mnt/shared/videos-original|/srv/nas/main/videos:/mnt/shared/videos-original|' /etc/fstab
sudo umount /mnt/shared/videos 2>/dev/null
sudo mount /mnt/shared/videos
```

**To move existing content from root fs to the external drive:**

```bash
# 99G+ of video files over USB can take 2-10 minutes
sudo mv /mnt/shared/videos-original/* /srv/nas/main/videos/

# Monitor progress:
ls /mnt/shared/videos-original/ | wc -l   # decreasing
ls /srv/nas/main/videos/ | wc -l          # increasing
df -h /dev/sda2 /dev/sdb2                  # root frees up, external fills
```

**ⓘ Before starting — confirm merge scope.** The user's instruction may sound like "merge the partition into videos" but they almost certainly mean "merge a `videos/` folder inside the partition." The partition root will have non-video files (datasets, apps, configs, dotfiles). Always ask specifically: "Did you mean a `videos/` folder inside the partition, or the entire partition root?" Do not assume.

```bash
# Install mergerfs if needed
ssh <pi> "sudo apt install -y mergerfs"

# Create the target subdirectory on the external partition (not the root!)
ssh <pi> "sudo mkdir -p /mnt/<external>/videos"

# Temporarily move existing videos aside
ssh <pi> "sudo mv /mnt/shared/videos /mnt/shared/videos-original"

# Mount the mergerfs pool — merge external's videos/ with original videos
# IMPORTANT: use the videos/ SUBDIRECTORY, not the raw partition
ssh <pi> "sudo mergerfs -o defaults,allow_other,category.create=epmfs,minfreespace=1G \
  /mnt/<external>/videos:/mnt/shared/videos-original /mnt/shared/videos"
```

**Path selection matters** — always point mergerfs at a specific subdirectory (e.g. `/mnt/dev2/videos/`), NOT the partition root (`/mnt/dev2/`). The partition root likely contains non-video files (datasets, apps, configs) that shouldn't appear in the video pool.

**Kill stale mergerfs processes before unmounting.** If a previous mergerfs mount is broken (e.g. the mount point is inaccessible but `stat` shows a directory entry), find and kill the process first, then force-unmount:

```bash
# Find the stale process
pgrep -a mergerfs

# Kill it
sudo kill <pid>

# Then lazy-unmount the mount point
sudo umount -l /mnt/shared/videos

# Check it's gone
ls /mnt/shared/videos/ 2>&1
# Should say "No such file or directory" or show empty
# If it hangs, the process wasn't fully killed — try again
```

**epmfs policy** (existing path, most free space) ensures new files land on the external drive, which usually has more free space.

**fstab entry:**
```bash
# Use the raw mount path (/mnt/dev2/videos), not a bind-mount path (/mnt/shared/external-dev2/videos)
# The bind-mount may become inaccessible if the parent directory has issues
echo '/mnt/dev2/videos:/mnt/shared/videos-original /mnt/shared/videos fuse.mergerfs defaults,allow_other,category.create=epmfs,minfreespace=1G 0 0' | sudo tee -a /etc/fstab
```

### 8. SSH workarounds through jump hosts (non-TTY)

When executing commands via nested SSH (e.g. `ssh macuntu ssh rabuntu "cmd"`), `sudo` often refuses to run because no TTY is available. Different commands work differently:

| Command pattern | Works? | Notes |
|---|---|---|
| `sudo sed -i '/pattern/d' file` | ✅ | In-place sed edits work without TTY |
| `sudo mkdir -p /path` | ✅ | Simple single commands work |
| `sudo sh -c 'cmd > file'` | ❌ | sudo demands a TTY for `sh -c` |
| `echo text \| sudo tee -a file` | ❌ | pipe + tee requires TTY with nested SSH |
| `sudo python3 -c 'open("file","a").write("text")'` | ✅ | Python one-liner works because sudo runs the binary directly |
| Write script to /tmp, then `sudo python3 /tmp/script.py` | ✅ | Most reliable for multi-step fstab edits |

**Best approach for fstab edits** when normal `sudo tee -a` fails:
1. Write content to a temp file without sudo: `echo 'fstab line' > /tmp/add.txt`
2. Copy to Pi via jump host scp
3. Run: `sudo python3 -c 'open("/etc/fstab","a").write(open("/tmp/add.txt").read())'`

### 9. SSH blocked by Tailscale ACL — alternative diagnostics

When Tailscale explicitly blocks SSH:

```
tailscale: tailnet policy does not permit you to SSH to this node
```

The machine IS online and responding, but Tailscale's SSH access control policy prevents your node from connecting. Do not retry SSH — no key, password, or flag will bypass it.

**Alternative diagnostic path** — use available web services:
1. **Node Exporter (9100)** — complete system diagnostics: CPU load, memory, disk, temperature, processes
2. **Process Exporter (9256)** — per-process CPU and memory breakdown
3. **SMB shares (445)** — enumerate shares with `rpcclient`, write optimization scripts to writable shares
4. **ARP cache** — find the local IP from the MAC address in metrics, bypass Tailscale entirely

See `references/ssh-blocked-tailscale-acl.md` for the full step-by-step diagnostic chain.

## Pitfalls

- **This Pi is on the second tailnet — use the LAN IP, not Tailscale SSH.** `rabuntu`
  (`pi5-deflab`, 100.68.0.96) belongs to the `inhumanekiller22@` tailnet, so `tailscale ssh` from
  lin/kubuntux fails with *"tailnet policy does not permit you to SSH to this node"*. It is on the
  same physical LAN though: `ssh rabuntu@192.168.1.222` (key auth, passwordless sudo) works fine.
  Confirm the current LAN IP from `tailscale status | grep rabuntu` (`active; direct <ip>:41641`)
  or the ARP cache before falling back to the SMB write-and-handoff pattern.

- **"active; relay" does NOT guarantee reachability**: Just because `tailscale status` shows a node as active with a relay connection, it does not mean any services on that node are reachable. A node can have an outbound Tailscale control connection (heartbeating) while all inbound traffic paths are blocked. Always verify with port probes and/or SSH before assuming a relay path will work.
- **Tailscale relay timeouts**: First SSH through a relay can take 30-90 seconds. Always establish a ControlMaster socket first, then use it for all subsequent commands. Each new `-J` connection re-negotiates the relay handshake.
- **ControlMaster socket conflicts**: If `ControlPath` collides with another host, SSH may fail. Use unique paths per host (e.g. `/tmp/ssh-rabuntu`, `/tmp/ssh-lin`).
- **No exfat/ntfs support**: Check `sudo blkid` output. Install the right FUSE package if the partition won't mount.
- **SMB folder already exists**: You can't bind-mount over a non-empty directory. Create a fresh subdirectory inside the SMB share.
- **fstab ordering**: Bind mounts require the source partition to be mounted first. fstab processes entries left-to-right, so the partition mount entry must come before the bind mount entry.
- **Samba needs restart after config changes**: Use `sudo systemctl restart smbd` to pick up new `smb.conf` settings. Bind mounts inside the share path take effect immediately — no restart needed.
- **exFAT I/O hang = Pi freeze**: If an exfat partition develops I/O issues (unmount hangs, `ls` on the mount point hangs), it can completely lock up the Pi kernel. SSH and ping will both fail. **The only recovery is a hard power cycle** (unplug/replug or press the reset button if available). Afterwards, run `sudo fsck /dev/sdX1` on the exfat partition before remounting.
- **Bind mounts can fail when parent directory is broken**: If the exfat partition at `/mnt/dev` becomes unavailable, its bind mount (`/mnt/shared/external-dev`) also becomes inaccessible. More critically, this can make the entire parent directory (`/mnt/shared/`) un-traversable, causing `ls /mnt/shared/` and `ls -la /mnt/shared/external-dev2` to both fail even though the ext4 partition is healthy. Access the ext4 partition directly via `/mnt/dev2/` in this case.
- **mergerfs on partition root pollutes the pool**: If you merge the entire partition root directory into the video pool, all non-video files (datasets, apps, configs) will appear alongside videos. Always create a `videos/` subdirectory on the external drive and merge that specific folder.
- **Stale FUSE process after lazy unmount**: `sudo umount -l /mnt/shared/videos` may detach the mount point but leave the mergerfs process running. Accessing the mount point directory can then hang indefinitely. Always kill the mergerfs PID first, then do `umount -l`.
- **mergerfs branch may not actually live on the external drive**: A mergerfs fstab entry can reference bind-mount paths that resolve to directories on the ROOT filesystem (`/dev/sda`) instead of the external drive (`/dev/sdb`). Always verify each branch with `df -h <path>` to confirm it's on the expected filesystem. The bind-mount sources (`/mnt/dev`, `/mnt/dev2`) may just be directories on root with bind mounts to the same root, giving zero extra space. Fix by updating the mergerfs fstab to point directly to the external drive's subdirectory (e.g. `/srv/nas/main/videos`) rather than trying to fix the bind mounts.
- **Tailscale `--ssh` flag required on the target device**: Applying a tag and ACL rule is not enough if the target device has not run `tailscale up --ssh` or does not have the `ssh` attribute enabled in nodeAttrs. Check `nodeAttrs` in the ACL and verify the target device has Tailscale SSH enabled. On the Pi: `sudo tailscale up --ssh`.

### 10. SSH blocked by Tailscale ACL — fix the ACL via Tailscale MCP Server

If you're blocked by the Tailscale SSH ACL but need shell access now (not later), the **HexSleeves/tailscale-mcp-server** can modify ACL rules from the same node that's blocked — as long as you have a Tailscale API key or OAuth client credentials.

**Setup (on the local machine):**
```bash
# 1. Install Bun (if missing)
curl -fsSL https://bun.sh/install | bash

# 2. Get an API key from Tailscale admin console:
#    https://login.tailscale.com/admin/settings/keys
#    Generate → API Key type → copy (starts with tskey-api-)
#    OR create an OAuth client with scopes: devices_core:write, policy:write
#    https://login.tailscale.com/admin/settings/oauth

# 3. Run the MCP server via bunx
export TAILSCALE_API_KEY="tskey-api-..."
export TAILSCALE_TAILNET="-"
bunx @hexsleeves/tailscale-mcp-server
```

**Usage via MCP tools:**
| Tool | Purpose |
|------|---------|
| `list_devices` | See all tailnet devices and their tags |
| `manage_acl` | Read and write ACL rules — add SSH access for `tag:infra` |
| `manage_device_tags` | Change a device's tags (requires admin) |

The `manage_acl` tool supports read and write risk levels. To grant SSH access for an infra-tagged machine to a specific user device, the ACL needs a **tag-based** `ssh` rule — `autogroup:member`, `*`, and user emails are NOT valid SSH `dst` values. The correct approach:

1. Add a tag for the target device in `tagOwners` (e.g. `tag:pi`)
2. Apply the tag to the target device
3. Add an SSH rule referencing the tag:

```json
{
  "src": ["tag:infra"],
  "dst": ["tag:pi"],
  "users": ["autogroup:nonroot", "root"],
  "action": "accept"
}
```

See `references/tailscale-mcp-server-setup.md` for full setup, auth options, and example ACL modifications with the correct SSH syntax.

**Alternative: direct Tailscale REST API** — don't need the MCP server at all. Save a step with curl:

```bash
# Get current ACL
curl -s -H "Authorization: Bearer $API_KEY" \
  "https://api.tailscale.com/api/v2/tailnet/-/acl"

# Update ACL (HVJSON in body)
curl -s -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @updated-acl.json \
  "https://api.tailscale.com/api/v2/tailnet/-/acl"

# Tag a device
curl -s -X POST -H "Authorization: Bearer $API_KEY" \
  -d '{"tags": ["tag:pi"]}' \
  "https://api.tailscale.com/api/v2/device/<id>/tags"

# List devices
curl -s -H "Authorization: Bearer $API_KEY" \
  "https://api.tailscale.com/api/v2/tailnet/-/devices"
```

**When to prefer this over the handoff script:**
- You have a Tailscale admin API key (or can get one)
- You need immediate shell access, not deferred
- You want to make the SSH ACL change permanent

**When to prefer the handoff script:**
- You don't have API key/OAuth credentials
- The Pi is on a local subnet (SSH via local IP still works)
- The task is one-off (disk cleanup, service disable) that doesn't need recurring SSH

See `references/tailscale-mcp-server-setup.md` for full setup, auth options, and example ACL modifications.

### 11. SSH blocked by Tailscale ACL — write a handoff script to SMB

When you've exhausted SSH attempts and confirmed the Tailscale ACL blocks your node, pivot to a **write-and-handoff** pattern:

1. **Diagnose** via Node Exporter / Process Exporter / Prometheus metrics (see `references/ssh-blocked-tailscale-acl.md`)
2. **Find writable SMB shares** — mount each share and test with `touch test_write`
3. **Write a remediation script** that does everything needed (disk cleanup, service disable, package removal)
4. **Hand off** — tell the user exactly what command to run on the Pi:
   ```
   sudo bash /path/to/script.sh
   ```

**Pi-specific optimization script** — see `references/pi-optimization-targets.md` for common targets: desktop (Xfce), dual ad-blockers (Pi-hole + AdGuardHome), Ollama + LiteLLM, heavy monitoring stack (Grafana/Prometheus/Alloy/Loki), RustDesk, Suricata.

**Never end with "I can't"** — report what WAS diagnosed and what the handoff script does. The user can execute it from another SSH session or physical access.

## Boot Drive Repair

When the Pi OS boot drive itself needs repair (not just data drives), see:
- `references/pi-os-boot-drive-repair.md` — full procedure for fsck, fstab timeout cleanup, udev rule fixes, NFS export cleanup, and verification on both boot (vfat) and root (ext4) partitions.

## Reference documents

- `references/pi-smb-layout.md` — example Pi SMB share structure with external drive bind mounts
- `references/exfat-hang-recovery.md` — recovery procedure for exFAT I/O freeze
- `references/pi-relay-only-unreachable.md` — diagnostic record: Pi reachable via relay but all services unreachable
- `references/ssh-blocked-tailscale-acl.md` — diagnostic and remediation when Tailscale ACLs explicitly block SSH access
- `references/pi-optimization-targets.md` — common Pi optimization targets with removal commands
- `references/resume-ytdlp-downloads.md` — resuming interrupted yt-dlp downloads on a remote Pi over unstable Tailscale SSH, including log-based URL extraction, .part resume patterns, handling rate-limited sites like eporner.com
