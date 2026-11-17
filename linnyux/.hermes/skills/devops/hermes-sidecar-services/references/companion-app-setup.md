# Hermes Android Companion — Setup Reference

Session-specific details from the Hermes Android Companion installation (July 2026).

## Quick Install (one-liner from README)

```bash
hermes plugins install HenWorks/Hermes-agent-android-PC-companion-app
```

## Systemd Unit (Tailscale / Cross-Network)

```bash
PLUGIN_DIR="$HOME/.hermes/plugins/Hermes-agent-android-PC-companion-app"
VENV="$HOME/.hermes/mesh/venv"
TS_IP=$(tailscale ip -4)
LABEL="com.hermesagent.mesh"

mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/$LABEL.service" << UNIT
[Unit]
Description=Hermes Mesh broker — phone↔desktop task dispatch + handoff
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=%h/.hermes/mesh/venv/bin/python3 -m handoff.mesh_broker --host $TS_IP
WorkingDirectory=%h/.hermes/plugins/Hermes-agent-android-PC-companion-app
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable --now "$LABEL.service"
```

## Verify

```bash
systemctl --user is-active com.hermesagent.mesh.service
ss -tlnp | grep 51379
journalctl --user -u com.hermesagent.mesh.service --no-pager | grep -E "(bound|Console|device|did)"
```

## Get Pairing Code (from daemon journal)

```bash
# Compact JSON text — paste into phone app
journalctl --user -u com.hermesagent.mesh.service --no-pager | grep -E '\{"v":1'

# Full output with console URL + QR art
journalctl --user -u com.hermesagent.mesh.service -n 30 --no-pager
```

## Typical Output (Tailscale)

```text
[companion] device c035df373001f0b5 bound to 100.93.75.87:51379 (collaboration + handoff; mDNS advertising, pairing window open 5 minutes)
Console: http://127.0.0.1:35071/ (opening the browser; scan the QR on the page to connect)
{"v":1,"did":"c035df373001f0b5","pk":"wDXfNzAB8LUd65nbN3c0ohEOZgh6d2ii5SwuM5g6oGk","host":"100.93.75.87","port":51379}
```

## Updating the Bind Address (e.g. LAN → Tailscale)

If the broker is already installed and running on a LAN IP but needs to switch to Tailscale:

```bash
# 1. Edit the systemd unit
sed -i 's|--host [0-9.]*|--host 100.XX.XX.XX|' ~/.config/systemd/user/com.hermesagent.mesh.service

# 2. Reload and restart
systemctl --user daemon-reload
systemctl --user restart com.hermesagent.mesh.service

# 3. Verify the new binding
journalctl --user -u com.hermesagent.mesh.service -n 10 --no-pager | grep bound
```

## Uninstall

```bash
systemctl --user disable --now com.hermesagent.mesh.service
rm -f "$HOME/.config/systemd/user/com.hermesagent.mesh.service"
systemctl --user daemon-reload
rm -rf "$HOME/.hermes/plugins/Hermes-agent-android-PC-companion-app"
rm -rf "$HOME/.hermes/mesh"
```
