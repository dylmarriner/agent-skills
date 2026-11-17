# Syncthing REST API — Call Patterns & Quirks

## Base URL
```
http://127.0.0.1:8384/rest/
```

## Authentication
Use the `X-API-Key` header. Get the key from config:
```bash
grep -oP '<apikey>\K[^<]+' ~/.config/syncthing/config.xml
```

## Common Endpoints

### Get device list
```bash
curl -s -H "X-API-Key: $AK" http://127.0.0.1:8384/rest/config/devices
  | python3 -c "import sys,json; [print(d['name'],d['deviceID'][:16]) for d in json.load(sys.stdin)]"
```

### Add a device
```bash
curl -s -X POST \
  -H "X-API-Key: $AK" \
  -H "Content-Type: application/json" \
  -d '{"deviceID":"<52-char-id>","name":"<hostname>","address":"tcp://100.x.x.x:22000","compression":"metadata","introducer":false,"autoAcceptFolders":false,"paused":false}' \
  http://127.0.0.1:8384/rest/config/devices
```

### List folders
```bash
curl -s -H "X-API-Key: $AK" http://127.0.0.1:8384/rest/config/folders
```

### Add a folder
```bash
curl -s -X POST \
  -H "X-API-Key: $AK" \
  -H "Content-Type: application/json" \
  -d '{"id":"myfolder","label":"My Folder","path":"/path/to/dir","type":"sendreceive","devices":[{"deviceID":"<id1>"},{"deviceID":"<id2>"}],"rescanIntervalS":60,"fsWatcherEnabled":true,"order":"random","paused":false,"markerName":".stfolder","minDiskFree":{"value":0,"unit":"%"}}' \
  http://127.0.0.1:8384/rest/config/folders
```

### Check folder sync status
```bash
curl -s -H "X-API-Key: $AK" "http://127.0.0.1:8384/rest/db/status?folder=<id>"
```

Expected states: `scanning`, `syncing`, `idle`.

### Get connection status
```bash
curl -s -H "X-API-Key: $AK" http://127.0.0.1:8384/rest/system/connections
```

## Quirks & Traps

1. **minDiskFree expects an object, not a string.** Pass `{"value": 0, "unit": "%"}`. A bare string `"0"` causes:
   ```
   json: cannot unmarshal string into Go struct field FolderConfiguration.minDiskFree of type config.Size
   ```

2. **No explicit commit needed.** The `/rest/config/commit` endpoint may return 404 on Syncthing 1.27+. Changes via POST to `/rest/config/folders` or `/rest/config/devices` are applied immediately.

3. **.stfolder marker must exist** before the folder is added. Syncthing scans for this marker to confirm the directory is under its management.

4. **autoAcceptFolders=false (default)** means you must add the folder on both machines manually with the same folder ID. The remote machine won't auto-accept.

5. **Device pairing is not folder sharing.** Pairing devices (Step 4) just establishes trust. You must explicitly add folders on both sides with the remote device ID listed.

## Python One-liner for Status
```bash
curl -s -H "X-API-Key: $AK" "http://127.0.0.1:8384/rest/db/status?folder=<id>" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('State:', d.get('state'), '| Global:', d.get('globalBytes'), '| Local:', d.get('localBytes'), '| Need:', d.get('needBytes'))"
```
