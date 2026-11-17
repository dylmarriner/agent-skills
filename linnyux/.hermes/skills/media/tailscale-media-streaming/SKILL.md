---
name: tailscale-media-streaming
description: Serve SMB/NFS-mounted media folders over HTTP on Tailscale so mobile VLC (or other players) can stream. Workaround for VLC mobile's unreliable SMBv2/v3 support when SMB1 is disabled.
metadata:
  tags: tailscale, vlc, streaming, smb, cifs, http-server, mobile
---

# Tailscale Media Streaming

## When to use

- A network share (SMB/CIFS) is mounted locally and you want to stream its media files to a phone/tablet
- VLC mobile fails to connect via SMB (common when SMB1 is disabled on the server — most Samba 4.x installs have it off by default)
- Both devices are on the same Tailscale network
- You need a zero-config, no-install solution that works immediately

## Instructions

### Step 1: Get the local Tailscale IP

```bash
ip addr show tailscale0 2>/dev/null | grep inet
```

This machine's Tailscale IP is the one starting with `100.x.x.x`. Your phone needs to be on the same Tailscale network.

### Step 2: Start the HTTP server

Use Python's built-in `http.server` module — no install needed:

```bash
# Background it for persistent access
python3 -m http.server <port> --directory /path/to/media/folder &
```

Or run it as a background terminal process. The server binds to all interfaces automatically, including the Tailscale interface.

**Port choice:** 8080 is standard. Avoid 8000 if you have other services. Check the port is free first:

```bash
ss -tlnp | grep :<port>
```

### Step 3: Verify binding

```bash
ss -tlnp | grep :<port>
```

You should see both `127.0.0.1:<port>` and `100.x.x.x:<port>` in the listening addresses.

### Step 4: Connect from VLC mobile

1. Ensure **Tailscale is connected** on your phone
2. Open VLC → **Network** tab
3. Tap **Add Network Stream** (Android) or **Network Stream** (iOS)
4. Enter: `http://<tailscale-ip>:<port>`
5. VLC shows a directory listing — tap any file to stream

### Step 5: Stop the server when done

```bash
pkill -f "python3 -m http.server <port>"
```

## Pitfalls

- **Python http.server is single-threaded**: Fine for one streamer. If multiple people stream simultaneously, use `miniserve` or `caddy` instead.
- **No authentication**: Anyone on your Tailscale network can access the folder. Keep Tailscale ACLs tight for sensitive content.
- **Tailscale relay**: If your phone connects via a DERP relay instead of direct, streaming may be slow. Verify with `tailscale ping 100.x.x.x` from the phone side — you want a direct connection.
- **SMB root alternative**: If VLC mobile has a working SMB client, `smb://<host>/<share>` is simpler. But VLC Android/iOS has ongoing issues with SMBv2/v3 — if `smb://` fails, HTTP is the reliable fallback. SMB1 is insecure and should remain disabled on the server.
- **Server dies on terminal close**: If you started it in a foreground terminal that later closes, the process continues in background as long as the shell session lives. For permanence, wrap in a systemd user service or tmux session.
- **Directory serving**: Python's http.server only serves static file listings — it won't transcode, subtitle, or metadata. It serves raw files for the player to handle.
