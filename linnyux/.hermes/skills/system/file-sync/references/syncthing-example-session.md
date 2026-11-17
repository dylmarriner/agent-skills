# Worked Example: DEVELOPMENT1 ↔ Rabuntu 1.3TB Sync

## Machines
- **Kubuntux**: 100.93.75.87 — `/media/kubuntux/DEVELOPMENT1` (224G SSD, ext4, 108G used)
- **Rabuntu**: 100.68.0.96 — `/srv/nas/main/DEVELOPMENT1` (1.3T ext4 on `/dev/sdb2`, 327G used, 951G free)

## Device IDs
- Kubuntux: `4XJADNV-7I3ASOJ-HOPQVGZ-AFYUIGT-HFJEW5W-RJJMDWR-4G2WMSD-XG45RAP`
- Rabuntu: `N6FA6UH-FYQHPCZ-OPPI47Z-G5KLBML-MNO4YKN-RRSLKVN-HMMGW3D-7CRTVQH`

## API Keys
- Kubuntux: `pyQtg2gLobUkMFV5zdDta9tGGDSPb2CJ`
- Rabuntu: `orjHUREs6qAL9bKSjQMi4TF6qz7uRkey`

## Folder Config
- **Folder ID**: `development1`
- **Folder Label**: `DEVELOPMENT1`
- **Type**: `sendreceive` (bidirectional)
- **Devices**: both device IDs listed (self + peer)

## Verification Commands

```bash
# Check folder list on either machine
curl -s -H "X-API-Key: <key>" http://127.0.0.1:8384/rest/config/folders \
  | python3 -c "import sys,json; [print(f['id'],'->',f['path']) for f in json.load(sys.stdin)]"

# Check sync status
curl -s -H "X-API-Key: <key>" "http://127.0.0.1:8384/rest/db/status?folder=development1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('State:', d.get('state'), '| Global:', d.get('globalBytes'), '| Local:', d.get('localBytes'), '| Need:', d.get('needBytes'))"
```

## Current Status
- Initial scan completed, syncing ~108G
- Both services enabled for auto-start on boot
- No fstab entries needed (Syncthing manages folder paths natively)
