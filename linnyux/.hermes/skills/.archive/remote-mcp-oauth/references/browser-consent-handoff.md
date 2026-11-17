# Driving the Provider's Consent Screen From a Headless Agent Shell

Capturing the token is automatable; the consent click needs a human in a real browser. On a host
that has a desktop session, that browser lives in *their* session — launching it there and driving
it is the agent's job. Everything below assumes the listener is already bound
(`scripts/oauth_pkce_login.py <name>`): a stale page plus a dead listener is the most expensive
combination in this flow.

## 1. Find the session you have to launch into

An agent shell reports no display even while the user sits at a full desktop:

```bash
echo "$DISPLAY|$WAYLAND_DISPLAY|$XDG_SESSION_TYPE|$SSH_CLIENT"   # often '||tty|<ssh-client>'
who ; loginctl list-sessions ; ls /tmp/.X11-unix/ ; pgrep -a Xorg ; pgrep -a plasmashell
```

`tty` plus a live `Xorg`/`kwin_x11`/`plasmashell` on `:0` means the session exists and must be
reached explicitly. Hermes' own opener reads these same signals — with `SSH_CLIENT`/`SSH_TTY` set it
prints "Remote session detected" and deliberately opens nothing, so treat that prompt as a symptom
of your shell, not as proof the user is elsewhere.

## 2. Launch the page detached

```bash
setsid env DISPLAY=:0 XAUTHORITY=/home/<user>/.Xauthority \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus \
  google-chrome --new-window "$URL" </dev/null >/tmp/chrome-oauth.log 2>&1
```

- Run it via `background=true`; a foreground `xdg-open`/`google-chrome` never returns and burns the
  whole call.
- `XAUTHORITY` and the session bus are what make it *their* browser (their cookies, their signed-in
  sites). Without them the window may not appear at all.
- Prefer navigating a browser that is already running over launching a new one: activate the window
  (`xdotool search --name "Google Chrome"` → `windowactivate --sync`) then `ctrl+l` → `type` →
  `Return`. A profile that was started without the session env carries no usable login state.

## 3. Look before you click

```bash
ffmpeg -loglevel error -f x11grab -video_size "$(xdpyinfo | awk '/dimensions/{print $2}')" \
  -i :0 -frames:v 1 -y /tmp/screen.png
```

- `ffmpeg` is the portable one-frame capture — no extra packages beyond ffmpeg itself, unlike the
  ImageMagick route.
- Vision input is downscaled. Take coordinates from the image, then scale back up (a 1920x1080
  capture shown at 960x540 doubles them) before `xdotool mousemove X Y`.
- Re-capture after every state change; a consent page's permission list takes seconds to render.

## 4. Clicking through a consent screen

```bash
xdotool windowactivate --sync "$WIN"
xdotool mousemove X Y ; xdotool click 1
xdotool key --clearmodifiers Page_Down      # x8-12: the submit button sits below the fold
xdotool key --clearmodifiers ctrl+l ; xdotool type --delay 3 "$URL" ; xdotool key Return
```

- The submit control is almost always below a long permission list — scroll to the end before
  concluding the page is broken.
- A consent page that renders fully and then bounces to the provider's sign-in page on submit means
  the browser is not authenticated (see §5), not that the authorize request was malformed.
- Pick the permission template the task actually needs. Selecting read-only yields an install whose
  write tools fail later; grant what the work needs and tell the user how to re-scope
  (`hermes mcp reauth <name>`, or the provider's authorized-applications page).
- Clear stray modals first (keyring prompt, "restore pages" bubble); otherwise the click lands on
  the dialog instead of the page.

## 5. "Not logged in" when the cookies exist

A locked desktop keyring stops the browser decrypting its own cookie store, so every authenticated
site renders as a login page while the rows are intact on disk. Check before asking for a re-login:

```bash
cp ~/.config/google-chrome/Default/Cookies /tmp/c.json      # copy first: the live DB is locked
sqlite3 /tmp/c.json "select host_key, count(*) from cookies where host_key like '%<domain>%' group by host_key"
```

Rows present + browser logged out ⇒ the keyring, not the session. The prompt reads "did not get
unlocked when you logged into your computer" (typical with autologin, or when the keyring password
differs from the login password). Only the user can unlock it — that is their single step. Do not
clear the prompt for them: killing the prompter just makes the browser fall back to an unusable key.

## 6. Process hygiene

- **Never `pkill -f "<name>"` for an application or browser name.** `-f` matches full command lines,
  including the `bash -c` running your own command, so the pattern kills your own shell mid-call.
  Use `pgrep -x <exact-process-name>` and kill the pids it prints.
- Chrome refuses `--remote-debugging-port` against the default profile directory ("DevTools remote
  debugging requires a non-default data directory"). A CDP-driven instance needs
  `--user-data-dir=<copy>`, which is a different profile with fresh login state — so drive the
  user's live browser with `xdotool` and keep CDP for throwaway automation.
- Give the capture listener a long window (`oauth_pkce_login.py` uses 900s). `state` and
  `code_verifier` are per-run: a run that ended cannot be resumed, only repeated.
