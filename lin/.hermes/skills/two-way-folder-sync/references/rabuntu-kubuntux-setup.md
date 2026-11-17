# Rabuntu ↔ Kubuntux Syncthing Setup (worked example)

## Hosts

| Machine | Hostname | IP | Device ID |
|---------|----------|-----|-----------|
| Kubuntux | kubuntux-To-be-filled-by-O-E-M | 100.93.75.87 | 4XJADNV-7I3ASOJ-HOPQVGZ-AFYUIGT-HFJEW5W-RJJMDWR-4G2WMSD-XG45RAP |
| Rabuntu | pi5-deflab | 100.68.0.96 | N6FA6UH-FYQHPCZ-OPPI47Z-G5KLBML-MNO4YKN-RRSLKVN-HMMGW3D-7CRTVQH |

## Folder Shared

| Side | Path | Drive |
|------|------|-------|
| Kubuntux | `/media/kubuntux/DEVELOPMENT1/` | 224G SSD, 108G used |
| Rabuntu | `/srv/nas/main/DEVELOPMENT1/` | 1.3TB ext4 partition, 327G used |

## API Keys

- Kubuntux: `pyQtg2gLobUkMFV5zdDta9tGGDSPb2CJ`
- Rabuntu: `orjHUREs6qAL9bKSjQMi4TF6qz7uRkey`

## Config Notes

- Both machines already paired via auto-discovery over Tailscale LAN
- `<autoAcceptFolders>` set to `false` — manual folder configuration on both sides
- `<globalAnnounceEnabled>` set to `false` — LAN/Tailscale only, no relay
- `<relaysEnabled>` set to `false`
- Both run Syncthing as systemd user service (`syncthing@username.service`)
- Load average on Pi peaked at ~17 during initial scan of 108G data
