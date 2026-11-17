# OpenHuman Linux desktop install / launcher troubleshooting

Use this when `openhuman` exists but fails to start, when a Linux install mixes AppImage and distro packages, or when the launcher path is stale.

## Session-proven fix

1. Check what the launcher really is:
   - `file ~/.local/bin/openhuman`
   - `which -a openhuman`
   - `dpkg -s open-human`
   - `dpkg -L open-human | grep -E '(/usr/bin/OpenHuman|/usr/share/OpenHuman|OpenHuman.desktop)$'`

2. If the system package is installed, prefer it over the old AppImage launcher.
   - Debian/Ubuntu package ships the actual binary as `/usr/bin/OpenHuman`
   - `~/.local/bin/openhuman` should be a tiny shim that execs `/usr/bin/OpenHuman`
   - keep the old AppImage as `~/.local/bin/openhuman.AppImage` or similar backup

3. Rebuild the user launcher if it still points at the AppImage:
   - replace the wrapper contents
   - update the desktop file to point at the wrapper and use `Icon=OpenHuman`

4. Verify the install path:
   - `bash scripts/test_install.sh`
   - `timeout 10s openhuman --version` (expect startup logs, not a clean version-only exit)
   - `ps -eo pid,comm,args | grep -i '[O]penHuman\|[o]penhuman'`

## Common pitfall

`openhuman --version` is not a pure CLI version printer on this app path. It may launch the GUI process and then sit in startup. Use `timeout` when probing it from the shell.

## Notes

- The repo's installer path should prefer the `.deb` on Debian/Ubuntu so `apt` resolves runtime deps.
- If the user has an old AppImage launcher in `~/.local/bin/openhuman`, do not assume `openhuman` is broken globally. The fix may just be replacing the wrapper.
- Keep the launcher rewrite and the regression test in sync with `scripts/install.sh` and `scripts/test_install.sh`.
