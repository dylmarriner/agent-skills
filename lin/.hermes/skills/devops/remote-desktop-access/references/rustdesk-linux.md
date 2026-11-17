# RustDesk on Linux — config, processes, ports, credentials

Depth for `remote-desktop-access`. Distilled facts, not a walkthrough.

## Config file map

Linux: `~/.config/rustdesk/` (Windows: `%APPDATA%\rustdesk\config\`).

| File | Holds |
|---|---|
| `RustDesk.toml` | `enc_id` (peer ID, encrypted), `password` (permanent password, encrypted), `key_pair` (Ed25519 pub/priv), `[keys_confirmed]` |
| `RustDesk2.toml` | `rendezvous_server`, `nat_type`, `trusted_devices`, `[options]`: `verification-method`, `direct-server`, `direct-access-port`, `local-ip-addr`, `allow-remote-config-modification` |
| `RustDesk_local.toml` | UI state only: `fav`, theme, `wayland-restore-token`, `remote_id` (last used) — machine-local, safe to delete |
| `peers.toml`, `peers/` | client-side address book / saved peers |

The peer ID and password live in the **serve**-side config. File permissions are
`0600` and the config belongs to the desktop user, not root.

## Credential scheme

```
stored = "00" + base64( secretbox(plaintext, nonce = 0x00 * 24, key = machine_uid[:32].ljust(32, 0x00)) )
```

- XSalsa20-Poly1305 (libsodium secretbox) → ciphertext is plaintext length + 16.
  A 30-character field is a 5-character password; a 4-character decode is a
  problem, not a short password.
- Machine UID on Linux is `/etc/machine-id` (32 ASCII chars → exactly 32 bytes).
- Deterministic: same key + same zero nonce. No salt, no KDF, so anyone holding
  the config file plus the machine-id can read the password offline.
- Desktop fallback when the UID key fails: the Ed25519 public key from
  `key_pair` in the same file.
- Consequence: **the config is machine-bound.** Copying the TOML to another host
  neither moves the ID nor the password.
- `RustDesk2.toml:unlock_pin` is a separate credential (auto-unlock on connect to
  the peer's own account) with its own encoding.

## Processes and ports

```
root        /usr/bin/rustdesk --service              <- systemd unit rustdesk.service
  └─ <user> /usr/share/rustdesk/rustdesk --server    <- the peer; without this nobody can connect
  └─ <user> /usr/share/rustdesk/rustdesk --tray      <- tray icon / UI logic
```

The service is `enabled` by the .deb/.rpm install. It spawns the per-user
`--server` with the desktop session env injected by the service itself
(`XDG_RUNTIME_DIR`, `DISPLAY`, `XAUTHORITY`, `WAYLAND_DISPLAY`); this is why
running `rustdesk` from a bare SSH shell behaves differently.

| Port | Role |
|---|---|
| 21115 | NAT type test |
| 21116 | ID / rendezvous, TCP + UDP |
| 21117 | Relay |
| 21118 | Direct IP access (`direct-access-port` default) |
| 21119 | WebSocket |

`direct-server = 'Y'` lets a client put the peer's IP (optionally `:port`) in the
ID box and skip the relay entirely — the useful path on a Tailscale/WireGuard
mesh, and the fallback when the public rendezvous server is unreachable.

## CLI facts

- `rustdesk --get-id` → prints the decrypted peer ID. Works headless over SSH.
- `rustdesk --help` → `cannot open display` over SSH (GUI-first binary, GTK init
  happens even for help). Export the desktop session env to run it.
- `rustdesk --password <pw>` → refuses as the desktop user over SSH
  (`Installation and administrative privileges required!`). Set the password from
  the GUI, or write the `00`-encoded value into `RustDesk.toml` and verify the
  round trip before restarting the service.
- The wrapper at `/usr/bin/rustdesk` is the service/launcher; the real UI+server
  binary is `/usr/share/rustdesk/rustdesk`.

## Wayland

- Capture uses the xdg-desktop-portal ScreenCast session (PipeWire). Needed:
  `xdg-desktop-portal` plus the desktop's backend (`-kde` for Plasma, `-gnome`
  for GNOME) installed **and running** (`systemctl --user list-units | grep portal`).
- `wayland-restore-token` in `RustDesk_local.toml` = a ScreenCast grant exists;
  treat it as the readiness signal. No token + incoming connection = black screen.
- Input injection does not use the portal: the root `rustdesk.service` injects via
  uinput. A peer that shows the screen but ignores input usually means the service
  is not running or the user `--server` child died.
- `loginctl show-session <id> -p Type -p Desktop -p Active` to confirm the session
  is Wayland vs X11 and which desktop is running.

## Troubleshooting quick table

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Peer never answers by ID | no user `--server` child, rendezvous unreachable, or firewall | `pgrep -a rustdesk`, `systemctl is-active rustdesk`, revive the `--server` child. Do **not** judge this from `ss`: the UDP heartbeat leaves no socket most of the time, so an empty `ss -tunp \| grep 21116` proves nothing |
| Timeout on direct IP | wrong port, or peer's firewall | `cat </dev/null >/dev/tcp/<ip>/21118`, read `direct-access-port` |
| Connected, black screen | Wayland portal missing / no restore token | install + start the portal backend, reconnect |
| Screen visible, no input | root service not running (uinput), or X11 vs Wayland mismatch | `systemctl is-active rustdesk`, `pgrep -a rustdesk` |
| Asks for approval on every connect | `verification-method` not `use-permanent-password`, or no permanent password set | set a permanent password, set the option |
| ID changed | config regenerated (reinstall / wiped home dir) | re-read `rustdesk --get-id`, hand out the new ID |
