---
name: remote-desktop-access
description: "Set up or fix RustDesk remote desktop access to a machine."
version: 1.0.2
author: Hermes Agent
license: MIT
platforms: [linux]
tags: [rustdesk, remote-desktop, vnc, wayland, fleet, ssh, devops]
trigger: When the user asks to install/set up RustDesk (or another remote-desktop tool) or to "make me able to connect to <machine>", "remote into <machine>", "set up remote desktop on <machine>".
metadata:
  hermes:
    tags: [rustdesk, remote-desktop, vnc, wayland, fleet, ssh, devops]
    related_skills: [multi-host-remote-config, tailscale, remote-windows-admin]
---

# Remote Desktop Access (RustDesk)

## When to Use

- "install RustDesk" / "set up remote desktop on <machine>" / "make me able to connect to <machine>"
- The user can reach a machine over SSH but wants its **screen** (GUI control, not a shell)
- RustDesk connects but shows a black screen, input is ignored, or pointer coordinates are offset/misaligned
- The peer's permanent password is unknown, or is weak and needs rotating

Class of work: make machine A controllable from machine B. The deliverable is
not "installed" — it is a working credential pair plus a proven path. Installing
is usually already done; the real work is the serve side being alive, the
credentials being known, and the path being proven.

## 1. Recon first, install second

One SSH round trip per machine decides everything. On a fleet that has been
around a while, the tool is usually already installed **and the daemon already
running** — then there is nothing to download. Never announce "installing"
before this returns.

```bash
# local (controller) machine
hostname; whoami; tailscale status | head -20; grep -A4 '^Host ' ~/.ssh/config
which rustdesk; rustdesk --version; systemctl is-enabled rustdesk; systemctl is-active rustdesk

# target machine — SSH by the ~/.ssh/config alias, not a raw IP
ssh <alias> 'bash -lc "hostname; whoami; . /etc/os-release; echo \$PRETTY_NAME; \
  rustdesk --version; systemctl is-enabled rustdesk; systemctl is-active rustdesk; \
  rustdesk --get-id; pgrep -a rustdesk; sudo -n true && echo SUDO_NOPASS || echo SUDO_NEEDS_PW"'
```

`rustdesk --get-id` is the peer ID and works headless. Probe `sudo -n true`
before designing a step that needs elevation — it is per-machine, not a fleet
constant.

## 2. The serve side must be actually serving

```bash
sudo systemctl enable --now rustdesk     # only if is-enabled/is-active say otherwise
pgrep -a rustdesk
```

The process set is the health check: root `/usr/bin/rustdesk --service` plus,
**per logged-in desktop user**, `/usr/share/rustdesk/rustdesk --server` and
`--tray`. A listening port with no `--server` child means nobody is logged in on
that desktop (or the user instance died) and the peer will not accept you —
restart the service and confirm the children reappear. Input injection depends on
this root service too, including on Wayland.

## 3. Credentials: read the real one, never guess

`RustDesk.toml` stores `password` (permanent password) and `enc_id` as
`"00" + base64(secretbox(plaintext, nonce = 24 zero bytes, key = machine-uid[:32]
zero-padded))`.

```bash
sudo apt-get install -y python3-nacl          # if pynacl is missing on the target
ssh <alias> 'python3 -' < scripts/rd_toml_secrets.py
```

The script prints the decrypted `enc_id` first: it must equal `rustdesk --get-id`.
That equality is the test vector for the whole scheme — if it matches, the
password printed underneath is the real permanent password, character for
character. If `enc_id` does not decrypt with machine-id, the same file's
`key_pair` Ed25519 public key is the documented fallback (the script tries both).

**The raw field is never the password.** It is always ciphertext, and its length
is the trap: a 29–30 character `00…` string reads like a plausible password but
decodes to five characters. Cross-check the arithmetic before trusting any
result — decoded bytes minus 16 (the Poly1305 tag) is the plaintext length, and
the base64 is unpadded, so add `=` padding before decoding or the decode
truncates silently and looks like an empty/failed password.

**Rotating a password** (the user wants one they chose, or the existing one is
weak like a dictionary word): `rustdesk --password <pw>` run as the desktop user
over SSH refuses with `Installation and administrative privileges required!`, so
write the `00`-encoded value into `RustDesk.toml` yourself with the same scheme,
then **re-run the script to confirm it decrypts back to exactly what you set**,
and only then `sudo systemctl restart rustdesk`. Never leave a rotated password
unverified, and never restart over a config whose round trip failed. Deliver the
password only in the handoff — not into world-readable temp files, shell history,
or a command line that lands in `ps`.

## 4. Prove the path before handing over

```bash
# from the controller: direct-IP access port and the rendezvous server
timeout 8 bash -c 'cat </dev/null >/dev/tcp/<peer-ip>/21118' && echo DIRECT_OPEN
timeout 8 bash -c 'cat </dev/null >/dev/tcp/rs-ny.rustdesk.com/21116' && echo RELAY_OPEN

# on the peer: socket present right now (positive-only signal — see note)
ssh <alias> 'ss -tunp | grep 21116'
```

That check is positive-only. Rendezvous registration is a periodic UDP heartbeat,
so the mapping is normally absent from `ss` between beats — **an empty result is
not evidence the peer is unregistered**, and treating it as failure sends you off
repairing a peer that was fine all along. Only a real connect attempt proves
reachability; use `ss` to confirm a suspicion, never to disqualify a peer.

Read the confirmations out of `~/.config/rustdesk/RustDesk2.toml`:
`verification-method = 'use-permanent-password'` (no Accept popup on the far end),
`direct-server = 'Y'`, `direct-access-port`, `local-ip-addr`. An open 21118 alone
proves nothing — the port is bound whether or not the user `--server` is alive.

## 5. Diagnose pointer-coordinate offsets

When the remote cursor is consistently displaced from the local pointer, treat it as a coordinate-space mismatch until tested; do not infer the cause from a saved desktop scale setting alone.

1. Compare the controller window's displayed remote resolution/aspect ratio with the target's active output resolution. Test RustDesk's original-size versus fit/scaled view and resize the window; note whether the offset changes.
2. Inspect the active graphical session on the target, not a bare SSH shell. Determine its session type, output geometry, and desktop scaling using the desktop session's environment. For KDE, `~/.config/kdeglobals` can show configured `ScreenScaleFactors`, but confirm the active session/output before treating that value as decisive.
3. Check RustDesk client and serve-side versions, then compare pointer alignment at 100% display scaling and with any client-side display scaling disabled. Change one factor at a time and reconnect to verify.
4. If the target runs an outdated RustDesk release and upstream release notes/issues document pointer-coordinate fixes relevant to its session type, update from the official release source before changing desktop settings. Check for active package-manager transactions first; wait for the package lock to clear rather than interrupting an upgrade. After installation, verify the installed version, service, and per-user `--server`/`--tray` processes.
5. Ask the user to reconnect and test actual pointer alignment; an upgrade is only a candidate fix until tested in the GUI. If it remains misaligned, capture client/host versions, both resolutions, session type, scale, and whether window resizing changes the offset before changing display configuration or switching session type. Switching Wayland/X11 ends the active graphical session and must be treated as a disruptive workaround.

Pitfall: Do not declare scaling ruled out from `gsettings` or a config file read over SSH; the active session may be KDE/Wayland and its display environment is not inherited by the SSH shell.

## 6. Handoff format

Dylan wants the answer, not the journey: a `##` heading, then the connect-from
device and how to open the client, the ID, the password, the direct-IP fallback
(peer's mesh IP + port, same password), then one small code block of the checked
facts (versions, service state, port results, the `--get-id` match). Nothing
about the reconnaissance. Disclose any package you installed on the peer inside that fact block (what,
where, why it stays) — you modified a machine that is not yours, and silence
about it reads as sloppy rather than tidy. Close with at most two one-line offers — realistically
"password is weak, say the word and I'll rotate it" and "if the session opens
black, it's the Wayland portal, tell me". No options menus, no narration.

## Pitfalls

- **`rustdesk --help` fails over SSH with `cannot open display`** — the binary is
  GUI-first and even help initialises GTK. `--get-id` runs headless. For anything
  else, export the desktop user's session env first:
  `XDG_RUNTIME_DIR=/run/user/1000 DISPLAY=:0 XAUTHORITY=$(ls /run/user/1000/xauth_*|head -1) WAYLAND_DISPLAY=wayland-0`.
- **Wayland peers need the portal, not just X11.** Capture goes through the
  xdg-desktop-portal ScreenCast session: `xdg-desktop-portal-kde` (Plasma) or
  `-gnome` must be installed and running, and a `wayland-restore-token` in
  `RustDesk_local.toml` means the grant was made at least once — its presence is
  the cheapest signal that Wayland capture is set up. Missing portal or missing
  token is the black-screen / no-input failure; the fix is on the portal side,
  not in RustDesk's config.
- **The config is machine-bound.** `password`/`enc_id` are keyed to the machine
  UID, so copying `RustDesk.toml` to another host (or after a reinstall) does not
  move the identity — the peer gets a new ID and an undecryptable password field.
  Recover or re-set credentials on the host that owns the config.
- **Verify on the machine that owns the file.** The decrypt needs that host's
  `/etc/machine-id`; running it against a copied config gives a silent `None`,
  which looks like "no password set" rather than "wrong key".
- **Don't hand over a password you did not verify.** A decryptable `password`
  field plus `verification-method = 'use-permanent-password'` are the two facts
  that mean "the user can connect"; anything else is a guess dressed up as a
  setup.

## Files

- `scripts/rd_toml_secrets.py` — read-only decrypt of `enc_id` + `password` from
  `RustDesk.toml`, machine-id key with `key_pair` fallback, prints the `--get-id`
  cross-check first. Pipe it to the target: `ssh <host> 'python3 -' < script`.
- `references/rustdesk-linux.md` — config file map, process/port model, CLI facts,
  credential scheme detail, troubleshooting table.
