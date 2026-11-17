---
name: file-sync
description: Configure bidirectional file synchronization between machines over Tailscale using Syncthing. Covers installation, pairing, folder configuration via REST API, and verification.
metadata:
  tags: syncthing, sync, replication, tailscale, file-sync, bidirectional
---

# File Sync (Syncthing)

## When to use

- User says "link" or "sync" two drives/machines together
- User wants files to exist on both machines in real time
- Setting up bidirectional replication between a Linux desktop and a remote server/Pi
- Replacing NFS mounts with real-time sync (files survive independently on both sides)
- Migrating from one-time rsync to continuous sync

**Key distinction:** If the user says "link" or "connect" two drives, clarify whether they want:
- A remote mount (NFS/CIFS — one machine accesses the other's files remotely) → use `system/network-mounts`
- File sync (files exist on both machines independently) → use this skill

## Instructions

### Step 1: Install Syncthing on both machines

```bash
# Ubuntu/Debian
sudo apt-get install -y syncthing

# Verify
syncthing --version
```

### Step 2: Start the service

Syncthing runs as a user service. On most systems:

```bash
# Enable and start (system service variant)
sudo systemctl enable --now syncthing@$USER

# Or as user service (user must be logged in for this to work)
systemctl --user enable --now syncthing
```

Wait a few seconds for it to initialise, then verify:

```bash
systemctl status syncthing 2>&1 | head -10
```

Look for: `"GUI and API listening on 127.0.0.1:8384"` and the device ID in the logs.

### Step 3: Get device IDs from both machines

From the service logs:

```bash
# Method 1: From journal
journalctl -u syncthing@$USER --no-pager | grep "My name is"
# Output: [XXXXX] INFO: My name is "hostname"

# Method 2: From config file
grep -oP '<device id="\K[^"]+' /home/$USER/.config/syncthing/config.xml | head -1
```

The device ID is a 52-character string with hyphens (e.g. `N6FA6UH-FYQHPCZ-OPPI47Z-G5KLBML-MNO4YKN-RRSLKVN-HMMGW3D-7CRTVQH`).

### Step 4: Pair devices

On machine A, add machine B as a device via the REST API:

```bash
# Get the API key from config
API_KEY=$(grep -oP '<apikey>\K[^<]+' /home/$USER/.config/syncthing/config.xml)

# Get this machine's own device ID
MY_ID=$(grep -oP '<device id="\K[^"]+' /home/$USER/.config/syncthing/config.xml | head -1)

# Add remote device
curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"deviceID\": \"<remote_device_id>\",
    \"name\": \"<remote_hostname>\",
    \"address\": \"tcp://<remote_tailscale_ip>:22000\",
    \"compression\": \"metadata\",
    \"introducer\": false,
    \"autoAcceptFolders\": false,
    \"paused\": false
  }" \
  http://127.0.0.1:8384/rest/config/devices

# Verify
curl -s -H "X-API-Key: $API_KEY" http://127.0.0.1:8384/rest/config/devices \
  | python3 -c "import sys,json; [print(d['name'],'->',d['deviceID'][:16]+'...') for d in json.load(sys.stdin)]"

# Repeat on machine B with machine A's device ID
```

If Syncthing is installed on both machines on the same Tailscale network, they may auto-discover each other via local discovery. Verify with:

```bash
journalctl -u syncthing@$USER --no-pager | grep "Established secure connection"
```

### Step 5: Create the shared folder on both machines

Create the `.stfolder` marker on each machine. This marker tells Syncthing the directory is under its management:

```bash
mkdir -p /path/to/shared/folder/.stfolder
```

**Important:** The path will differ on each machine (different drives, different mount points). The folder ID must be the same on both sides.

### Step 6: Add the folder via REST API

On machine A (path on this machine's filesystem):

```bash
FOLDER_JSON=$(cat <<'FOLDER'
{
  "id": "<folder_id>",
  "label": "<human_readable_label>",
  "path": "/absolute/path/on/this/machine",
  "type": "sendreceive",
  "devices": [
    {"deviceID": "<this_machine_id>"},
    {"deviceID": "<remote_machine_id>"}
  ],
  "rescanIntervalS": 60,
  "fsWatcherEnabled": true,
  "order": "random",
  "paused": false,
  "markerName": ".stfolder",
  "minDiskFree": {"value": 0, "unit": "%"},
  "versioning": {"type": "simple", "params": {"keep": "5"}}
}
FOLDER
)

curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$FOLDER_JSON" \
  http://127.0.0.1:8384/rest/config/folders

# Verify
curl -s -H "X-API-Key: $API_KEY" http://127.0.0.1:8384/rest/config/folders \
  | python3 -c "import sys,json; [print(f['id'],'->',f['path']) for f in json.load(sys.stdin)]"
```

**Repeat on machine B** with the same folder ID but the path on machine B's filesystem.

### Step 7: Verify sync status

```bash
# Check folder sync state
curl -s -H "X-API-Key: $API_KEY" \
  http://127.0.0.1:8384/rest/db/status?folder=<folder_id> \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('State:', d.get('state'))
print('Global:', d.get('globalBytes','?'), '| Local:', d.get('localBytes','?'))
print('Need:', d.get('needBytes','?'))
"

# Expected states:
#   "scanning" — initial index build (normal for first run)
#   "syncing" — actively transferring files
#   "idle" — all in sync (no pending changes)
```

## Pitfalls

- **'link' ≠ 'mount'**: When a user says "link drive X with Y", confirm if they want sync (files on both) or mount (remote access). This skill covers sync; use `system/network-mounts` for mounts.
- **minDiskFree format**: The REST API expects `{"value": N, "unit": "%"}` — passing a plain string `"0"` causes `json: cannot unmarshal string into Go struct field FolderConfiguration.minDiskFree of type config.Size`.
- **.stfolder marker required**: Syncthing won't adopt a folder without the `.stfolder` marker directory inside it. Create it before adding the folder via the API.
- **autoAcceptFolders**: If set to `false` (default), the remote machine won't auto-accept folders shared by its peer. You must add the folder on both machines manually with the same folder ID.
- **No explicit commit needed**: On modern Syncthing (1.27+), config changes via REST API are applied immediately. The `/rest/config/commit` endpoint may return 404 — that's fine, the change stuck.
- **Tailscale addresses**: Use Tailscale IPs (100.x.x.x) for the device address. LAN IPs may fail across subnets.
- **First sync is slow for large dirs**: The initial scan indexes all files. For a 100G+ directory with many files, this can take several minutes. The folder will show state `scanning` during this time. Be patient.
- **Reboot persistence**: Syncthing is managed via systemd. `sudo systemctl enable --now syncthing@$USER` ensures it starts on boot. Verify with `systemctl is-enabled syncthing@$USER`.

## Related reference documents

- `references/syncthing-rest-api-notes.md` — REST API call patterns, response formats, and common errors
- `references/syncthing-example-session.md` — worked example: setting up Development1 ↔ rabuntu-1.3tb sync
