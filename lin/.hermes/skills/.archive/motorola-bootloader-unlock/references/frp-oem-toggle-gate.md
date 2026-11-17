# The FRP → OEM-toggle → unlock knot

## Why it's circular

```
FRP screen        → can't reach Settings
Settings          → the only place the OEM-unlocking toggle lives
OEM toggle ON     → checked by abl before it will evaluate the unlock code
bootloader unlock → the operation that wipes /data and clears FRP
```

Each link is deliberate. There is no supported command that sets the toggle from fastboot, so the knot has to be broken on the Android side.

**The goal is small: reach `Settings → Developer options` once.** Full FRP removal is not needed, and is a much harder problem than this actually requires.

## What does NOT break it

- **A factory reset.** FRP survives a wipe by definition. `fdr-allowed: yes` only means recovery will co-operate — using it costs the user their data and changes nothing. Do not recommend it as a step.
- **EDL / blankflash.** See `qualcomm-edl.md`: the programmer Motorola ships is restricted and partition writes are refused on a locked bootloader.
- **Changing the system clock / "wait 7 days" tricks.** The greyed-out toggle waiting period is a server-side gate about the *toggle*, not FRP.
- **Paid FRP-removal services.** Rebundled tools, frequently malware, and they do not address the toggle gate.

## Route 1 — recover the Google account (only guaranteed path)

Ask, once, and early: *whose* account is on the device — an old one of the user's, or a reachable previous owner? If either, the user signs in at the FRP screen, setup completes, and the toggle unlocks immediately. This beats every technical route and costs minutes.

If it's an old account of the user's own, account recovery is its own task and still cheaper than anything below.

## Route 2 — setup-wizard escape (reach Settings once)

**Status: documented for the fogos/G45 platform, NOT verified in-house.** Treat as a starting point to work through on the device, not a guaranteed sequence. Android 14 setup wizards are actively hardened against these, so expect to hunt for a live link rather than follow a fixed path.

The class of chain is: find any in-wizard surface that opens a browser or an app, then climb from app → system accessibility → a launcher shortcut that can reach Settings. The shape that has been published for this platform family:

```
FRP screen → an in-page link (OEM contact / privacy-policy page)
  → a browser opens → its own settings → accessibility sub-page
  → "use device settings" to hand off to the SYSTEM accessibility menu
  → enable the accessibility menu shortcut (gives a persistent on-screen menu)
  → an app-settings surface → open a bundled OEM app
  → that app's gesture/sidebar feature → add "Back to Home" + "switch to last app"
  → real navigation → Settings
```

The transferable idea is the *last* step: reach a launcher or "go home" affordance, because that turns a single lucky escape into normal navigation.

Other surfaces worth probing when the above is patched:
- emergency dialer → `*#*#4636#*#*` or `*#*#0*#*#` → hardware-test menu → look for a back door into Settings
- enable TalkBack from the accessibility shortcut, then gesture-navigate toward Settings
- "Copy apps & data" / file-picker steps that open a documents UI

## The caveat that can invalidate Route 2

OEMs may keep the OEM-unlocking toggle **greyed out until setup has fully completed** — and setup completion is exactly what FRP is blocking. If you reach Settings and the toggle is dead rather than merely off, Route 2 achieved nothing and Route 1 is the only remaining path. Check the toggle the moment Settings opens, before investing more time in the escape.
