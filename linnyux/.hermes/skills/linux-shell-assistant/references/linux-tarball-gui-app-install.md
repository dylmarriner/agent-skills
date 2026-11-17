# Installing self-contained Linux GUI apps from `.tar.gz`

Use this when a downloaded tarball contains a complete Electron/Chromium-style app directory rather than a distro package.

## Durable pattern

1. Discover candidate archives and inspect before extraction:
   - `file "$archive"`
   - `du -h "$archive"`
   - `tar -tzf "$archive" | sed -n '1,80p'`
2. Extract to a fresh temp dir first, verify the expected top-level executable exists, then atomically replace the user-local install directory.
3. Prefer user-local install paths:
   - app payload: `$HOME/.local/opt/<app-name>`
   - command wrappers: `$HOME/.local/bin/<command>`
   - launcher: `$HOME/.local/share/applications/<app-name>.desktop`
4. For Electron/Chromium tarballs, check bundled `chrome-sandbox` behavior. If the sandbox helper is not root-owned mode `4755`, a direct launch can abort with:
   - `The SUID sandbox helper binary was found, but is not configured correctly...`
   In user-local installs, create a wrapper in `$HOME/.local/bin` that executes the payload binary with `--no-sandbox` instead of trying to set root ownership.
5. Do not replace the payload executable with a wrapper. Put wrappers only under `$HOME/.local/bin`. Accidentally writing a wrapper over the installed binary creates recursive self-exec hangs.
6. Create a `.desktop` file whose `Exec=` points at the wrapper, not the raw payload binary.
7. Verify:
   - `command -v <command>` resolves to `$HOME/.local/bin/...`
   - `file "$install_dir/<binary>"` shows an ELF binary or expected script, not the wrapper accidentally copied over it
   - `ldd "$install_dir/<binary>" | awk '/not found/'` returns no missing shared libraries for ELF payloads
   - `desktop-file-validate ~/.local/share/applications/<app>.desktop` passes when available
   - a short launch/smoke command starts cleanly; GUI apps may not exit on `--version`, so use `timeout` and inspect stdout/stderr rather than assuming timeout is failure

## Minimal wrapper

```bash
#!/usr/bin/env bash
set -e
exec "$HOME/.local/opt/<app-name>/<payload-binary>" --no-sandbox "$@"
```

## Minimal desktop entry

```ini
[Desktop Entry]
Name=<App Name>
Comment=<short distinct description>
GenericName=Text Editor
Exec=/home/<user>/.local/bin/<command> %F
Icon=/home/<user>/.local/opt/<app-name>/<path-to-icon>
Type=Application
StartupNotify=true
StartupWMClass=<App Name>
Categories=Development;IDE;
MimeType=text/plain;inode/directory;
Keywords=<app>;code;editor;ide;
```

Avoid making `Comment` identical to `Name`; `desktop-file-validate` warns about that.
