---
name: two-way-folder-sync
description: Set up real-time bidirectional folder sync between two machines using Syncthing. Covers install, service management, REST API configuration, device pairing, folder sharing, and verification across Tailscale or LAN.
trigger: User asks to link, sync, mirror, or keep files on two machines, or mentions keeping drives in sync between Linux hosts.
---

# Two-Way Folder Sync (Syncthing)

Set up real-time bidirectional file synchronization between two Linux machines. Syncthing is the tool — no cloud, peer-to-peer over Tailscale or LAN.

## Quickstart

```
sudo apt-get install -y syncthing
sudo systemctl enable --now syncthing@<username>
```

## Architecture

- **Syncthing** — peer-to-peer sync daemon. Each machine is a device with its own device ID.
- **REST API** — configure folders programmatically (avoids GUI dependency).
- **Systemd user service** — runs on boot, survives reboots.

## Setup Steps

### 1. Install on Both Machines

```bash
sudo apt-get install -y syncthing
```

### 2. Start the Service

```bash
sudo systemctl enable --now syncthing@$(whoami)
# Check it's running:
systemctl --user status syncthing
```

Wait a few seconds for initialisation, then verify the REST API is listening:

```bash
curl -s http://localhost:8384/rest/system/status
```

### 3. Get Device IDs

From each machine's syncthing config:

```bash
# From the .xml config
grep -oP '<device id="\K[^"]+' ~/.config/syncthing/config.xml | head -1

# Or from the logs
journalctl --user -u syncthing -n 20 --no-pager | grep 'My name is\|Device.*is.*at'
```

### 4. Check / Establish Pairing

Syncthing auto-discovers peers on the same LAN via multicast. For Tailscale, ensure:
- Port 22000 (TCP+QUIC) is reachable between machines
- Add explicit addresses for reliable connections:

```xml
<device id="REMOTE_DEVICE_ID" name="remote-name" ...>
    <address>tcp://<tailscale-ip>:22000</address>
</device>
```

Verify pairing in logs:
```
Established secure connection to <DEVICE_ID> at <ip>:22000
```

### 5. Get the API Key

```bash
grep -oP '<apikey>\K[^<]+' ~/.config/syncthing/config.xml
```

Use this for all REST API calls.

### 6. Add a Shared Folder via REST API

**On machine A** (source): create `.stfolder` marker, then POST the folder config.

```bash
mkdir -p /path/to/folder/.stfolder

FOLDER_JSON='{
  "id": "folder-id",
  "label": "Friendly Label",
  "path": "/path/to/folder",
  "type": "sendreceive",
  "devices": [
    {"deviceID": "LOCAL_DEVICE_ID"},
    {"deviceID": "REMOTE_DEVICE_ID"}
  ],
  "rescanIntervalS": 60,
  "fsWatcherEnabled": true,
  "order": "random",
  "paused": false,
  "markerName": ".stfolder",
  "minDiskFree": {"value": 0, "unit": "%"}
}'

curl -s -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$FOLDER_JSON" \
  http://localhost:8384/rest/config/folders
```

**On machine B** (target): create the destination directory with `.stfolder`, then repeat the same `POST` with the destination path and device IDs swapped.

```bash
mkdir -p /destination/path/.stfolder
# POST same JSON but with path changed and device IDs swapped
```

### 7. Verify

```bash
# Check folder is registered
curl -s -H "X-API-Key: YOUR_API_KEY" http://localhost:8384/rest/config/folders \
  | python3 -c "import sys,json; [print(f['id'],'->',f['path']) for f in json.load(sys.stdin)]"

# Check sync status
curl -s -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8384/rest/db/status?folder=folder-id" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('State:', d.get('state'), 'Need:', d.get('needBytes'), 'Global:', d.get('globalBytes'))"
```

Initial states: `scanning` → `idle` (synced) or `syncing` (actively transferring).

## Pitfalls

- **NFS ≠ sync.** If the user says "link" or "files on both", they mean two-way sync (Syncthing), not remote mount (NFS/SSHFS). Always clarify before installing NFS.
- **REST API timing.** Syncthing needs a few seconds after starting before the REST API responds. Use `sleep 3` after `systemctl start`.
- **API key required.** All REST calls need `X-API-Key` header. The web UI also uses this.
- **Marker file.** The `.stfolder` marker directory must exist before adding a folder, otherwise Syncthing refuses the path.
- **Heavy load on initial sync.** A large folder (100GB+) on a Pi-class machine will peg CPU/I/O during the initial scan. This is normal. Load drops once scanning completes.
- **autoAcceptFolders** defaults to `false`. To auto-accept folders pushed from a paired device, set `<autoAcceptFolders>true</autoAcceptFolders>` on the device entry in config.xml. Without this, both sides must be configured manually.
- **User service vs system service.** On Debian/Ubuntu: `sudo systemctl enable --now syncthing@<username>`. On systems where user services aren't available, use `syncthing serve --no-browser` directly in a user crontab or init script.
- **Ports.** Syncthing uses TCP/UDP 22000 (sync) and UDP 21027 (discovery). Ensure these are open between machines on Tailscale (they are by default).
- **QUIC vs TCP.** Syncthing prefers QUIC but falls back to TCP. For Tailscale, TCP is usually more reliable. Explicit addresses like `tcp://100.x.x.x:22000` force TCP.

## References

See `references/` for session-specific examples and output.
