# Disable Internal Laptop Keyboard

For laptops with faulty internal keyboards or when using an external keyboard exclusively.

## Quick Disable (Current Session)

```bash
# Find the internal keyboard device
xinput list | grep -i "AT Translated"   # Usually id=15

# Disable it
xinput set-prop <id> "Device Enabled" 0

# Re-enable
xinput set-prop <id> "Device Enabled" 1
```

The internal keyboard on most x86 laptops appears as `AT Translated Set 2 keyboard`.

## Permanent via systemd User Service

Creates a service that runs at every graphical session login:

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/disable-internal-kbd.service << 'EOF'
[Unit]
Description=Disable internal laptop keyboard
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/xinput set-prop 15 "Device Enabled" 0
RemainAfterExit=yes

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable disable-internal-kbd.service
systemctl --user start disable-internal-kbd.service
```

**To reverse:**
```bash
systemctl --user disable disable-internal-kbd.service
xinput set-prop 15 "Device Enabled" 1
```

## Notes

- The `xinput id` for `AT Translated Set 2 keyboard` can vary between machines — verify first with `xinput list | grep -i key`
- The service requires a running X/Wayland session (graphical-session.target), so it won't work in SSH or TTY sessions
- USB keyboards, touchpads, and other input devices are not affected
