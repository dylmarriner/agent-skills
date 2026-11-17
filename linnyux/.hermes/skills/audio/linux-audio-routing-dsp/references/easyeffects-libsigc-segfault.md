# Easy Effects v7.1.6 libsigc-3.0 segfault — diagnostic and workaround

## Symptoms

Easy Effects (`com.github.wwmm.easyeffects` 7.1.6-1ubuntu0.24.04.1) reliably segfaults
on Ubuntu 24.04 with `libsigc++-3.0-0` 3.6.0-2. Same package works on 24.04 with
older libsigc 3.4.x. Caused by an ABI/behavior change in libsigc++ 3.6.0 that the
7.1.6 source is not built against.

## What crashes look like

```
$ easyeffects --version
ATTENTION: default value of option vblank_mode overridden by environment.
(easyeffects:4078442): Adwaita-WARNING **: Using GtkSettings:gtk-application-prefer-dark-theme
with libadwaita is unsupported. Please use AdwStyleManager:color-scheme instead.
```

Then process dies. `--load-preset` always crashes. `--gapplication-service` mode
appears on D-Bus for ~1s then disappears.

## dmesg confirmation

```
[971040.583887] easyeffects[4077812]: segfault at e8 ip 00007ea0246367cb sp 00007fffce539170 error 4 in libsigc-3.0.so.0.0.0[7ea024634000+4000] likely on CPU 6 (core 2, socket 0)
[971040.866490] easyeffects[4077840]: segfault at e8 ip 00007e9bc484c7cb sp 00007fffb0be50a0 error 4 in libsigc-3.0.so.0.0.0[7e9bc484a000+4000] likely on CPU 3 (core 3, socket 0)
[971041.152695] easyeffects[4077864]: segfault at e8 ip 000079268cf667cb sp 00007ffed0752340 error 4 in libsigc-3.0.so.0.0.0[79268cf64000+4000] likely on CPU 5 (core 1, socket 0)
[971041.432014] easyeffects[4077912]: segfault at e8 ip 00007bf9e02687cb sp 00007ffefbdbf340 error 4 in libsigc-3.0.so.0.0.0[7bf9e0266000+4000] likely on CPU 4 (core 0, socket 0)
```

Multiple child PIDs all die in the same libsigc function. The faulting address (`e8`)
is a fixed offset into the library, so it's the same codepath each time.

## journalctl

```
$ journalctl --user -u app-easyeffects\\x2dservice@autostart.service -n 20
Jul 03 18:19:32 ... systemd[1892]: Starting app-easyeffects\x2dservice@autostart.service...
Jul 03 18:19:32 ... systemd[1892]: Started app-easyeffects\x2dservice@autostart.service.
Jul 03 18:19:32 ... easyeffects[4071726]: ATTENTION: default value of option vblank_mode overridden by environment.
Jul 03 18:19:32 ... easyeffects[4071726]: Using GtkSettings:gtk-application-prefer-dark-theme with libadwaita is unsupported.
Jul 03 18:19:32 ... systemd[1892]: app-easyeffects\x2dservice@autostart.service: Main process exited, code=killed, status=11/SEGV
```

`code=killed, status=11/SEGV` = signal 11 (SIGSEGV).

## Workarounds

### 1. Flathub build (recommended)

The Flathub package bundles its own libsigc, sidestepping the system conflict.

```bash
flatpak install -y flathub com.github.wwmm.easyeffects
flatpak run com.github.wwmm.easyeffects

# Verified: installs as com.github.wwmm.easyeffects//stable (Flathub's current
# release branch). The `//master` ref is NOT what `flatpak install` deploys
# by default. The bare `flatpak run` with no ref is the correct command.
# Using `//master` after a `stable` install gives:
#   error: app/com.github.wwmm.easyeffects/x86_64/master not installed
```

**Updated**: Flathub serves EE under the `stable` branch by default (not
`master` as older forum posts claim). The bare `flatpak run` command above
works. If you have a stale `master` install from older instructions, remove
it first: `flatpak uninstall com.github.wwmm.easyeffects` then re-install.

**Flatpak config isolation**: the flatpak EE reads/writes its own config
under `~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/`, NOT
`~/.config/easyeffects/`. Presets, autoload entries, and live state
written to the native path are invisible to the flatpak build. If you
switched between native and flatpak, copy your files across:
`cp -r ~/.config/easyeffects/* ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/`

Confirm installed refs:

```bash
flatpak list --columns=app,branch,ref | grep easyeffects
```

If the only entry is `com.github.wwmm.easyeffects.Locale` (translations only),
the main app didn't deploy. Re-run `flatpak install -y flathub com.github.wwmm.easyeffects`
and wait for the download to complete (53.5 MB; install can take a minute on slow links).

### 2. Pin libsigc to 3.4.x

If you must use the native package:

```bash
# Add a source for older libsigc, or download a .deb from noble's previous version
sudo apt install libsigc++-3.0-0=3.4.0-1
sudo apt-mark hold libsigc++-3.0-0
```

This may break other packages that need 3.6.x.

### 3. Build from source

```bash
git clone --depth=1 --branch=7.2.0 https://github.com/wwmm/easyeffects.git
cd easyeffects
meson setup build --prefix=/usr/local
meson compile -C build
sudo meson install -C build
```

7.2.0+ should be built against newer libsigc and not have the crash.

## Why this is hard to debug from the agent side

- Process dies before logging anything useful
- D-Bus name appears briefly then disappears, so `gdbus call` returns success but the
  process is actually a ghost
- Multiple crashed child PIDs in strace suggest a signal-handler-spawning pattern
  in EE that amplifies the crash into a loop
