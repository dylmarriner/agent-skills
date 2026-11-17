# Routing an application’s downloads into an SMB/NAS folder

Use this when a user wants a downloader or media app to save directly into a directory that is also exported as an SMB share.

## Procedure

1. Identify the real application and runtime before editing anything. Check project documentation/config for its destination setting; inspect `systemctl --user list-units --all`, `systemctl --user list-unit-files`, `pgrep -af <app>`, and `docker compose ls -a`/`docker ps -a` as appropriate. A project called a “stack” is not necessarily running in Docker.
2. Confirm the destination mount and access as the service user: `findmnt -T <destination>` and `test -w <destination>` under the relevant user. Ensure the filesystem is mounted persistently when the service starts; a path under an unmounted drive can silently create data on the root filesystem.
3. Prefer the app’s documented runtime setting over changing application code or individual queued jobs. For a systemd user unit, create a drop-in under `~/.config/systemd/user/<unit>.service.d/` with the app’s environment variable, then `systemctl --user daemon-reload` and restart that unit. Preserve the base unit and other environment entries.
4. Verify the service is active, inspect its effective environment using `systemctl --user show <unit> -p Environment`, and confirm the app’s own startup log reports the selected destination. Check that the exact destination directory exists and is writable.
5. Verify the app-specific health endpoint or status command when available. If a CLI invocation fails due to inherited shell environment contamination, do not infer that the restarted daemon failed; inspect the service journal and its health endpoint independently.

## DLP example

DLP reads `DLP_DOWNLOAD_DIR` at daemon startup and defaults to `~/Videos/downloads`. To route it to a NAS share directory:

```sh
mkdir -p ~/.config/systemd/user/dlp-daemon.service.d
printf '[Service]\nEnvironment=DLP_DOWNLOAD_DIR=/absolute/path/to/share/folder\n' > ~/.config/systemd/user/dlp-daemon.service.d/download-dir.conf
systemctl --user daemon-reload
systemctl --user restart dlp-daemon.service
systemctl --user is-active dlp-daemon.service
systemctl --user show dlp-daemon.service -p Environment -p MainPID
journalctl --user -u dlp-daemon.service -n 30 --no-pager
curl -fsS http://127.0.0.1:8765/health
```

Check the DLP startup log for `worker starting ... dest=<path>`; this confirms the worker loaded the new destination, while `/health` confirms the API remains live. The CLI and daemon may use different environments, so an interactive CLI error does not by itself establish daemon failure.