# CX File Explorer — Android to SMB Share

## Quick reference

Connect an Android phone to a Samba SMB share using **CX File Explorer** (free, Play Store).

## Steps

1. Open CX File Explorer
2. Tap **Network** tab (bottom of screen)
3. Tap the **+** icon (blue, top-right)
4. Tap **Remote** tab (at top)
5. Tap **Local network** → scans LAN for SMB servers
6. If the server doesn't appear: tap **Manual Input** (bottom-right) and enter:
   - **Host:** server IP (e.g. `192.168.1.x` or Tailscale `100.x.x.x`)
   - Leave port as default (445)
7. Enter **Username** and **Password** when prompted
8. After successful auth, the app shows a **list of available shares** — tap the desired one

## Key pitfall

**There is NO separate "Share name" or "Path" field on the add-server screen.**
The share selector appears **after** authenticating with username+password. Don't look for a share name field during initial server setup — it doesn't exist in CX File Explorer.

## Port

SMB uses port **445** (TCP) — CX File Explorer uses this by default. No need to specify.
Port **139** (NetBIOS) is legacy but also enabled on most servers.
