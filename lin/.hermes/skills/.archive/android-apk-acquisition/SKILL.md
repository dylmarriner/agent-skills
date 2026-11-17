---
name: android-apk-acquisition
description: Verify a delisted Play app and obtain its APK.
---

# Android APK acquisition (delisted / sideloaded apps)

## 1. Establish ground truth before claiming anything is 'gone'
Never assert an app is delisted from partial data. Confirm it headless, no login:

    curl -o /dev/null -w "%{http_code}" "https://play.google.com/store/apps/details?id=<package>"

- `200` = still listed -> tell the user to install from Play; do NOT hunt an APK.
- `404` = delisted -> only now look for the APK.

Get the package name from the Play URL (`id=...`) or the app's appbrain page.

## 2. Delisted vs abandonware + exact version/removal date -> AppBrain
An app still returning 200 may be abandonware, not removed (e.g. updated years ago but still installable). AppBrain app pages (appbrain.com/app/...) state the precise "removed from Google Play <date>" line, latest version, APK size, and download count. Use it to (a) confirm the app really was removed and (b) learn the last version + size to sanity-check any file you later find.

## 3. Mirror landscape (what actually works)
The major archives all gate raw files behind Cloudflare/JS/interstitial downloaders. Plan for this; do not promise a curl-able file.
- APKMirror: most trustworthy (keeps the developer's original signature + SHA), but hosts only a SUBSET of apps (many old ones 404 there) and is Cloudflare-challenged from datacenter IPs.
- APKCombo / APKPure: route downloads through a server-side downloader and often return an XAPK/APKS bundle that needs an installer app, behind an interstitial.
- uptodown / softonic / apk.watch: frequently 404 older apps entirely.
- soft112: does NOT host delisted apps. Its download button lands on an explicit "this app was removed from Google Play and we do not have an alternate APK available" + alternatives list — never a file. Skip it for delisted apps.
- APKPure: returns HTTP **410 Gone** (not 404) for removed apps.
- Small SEO shells (andro.io, androidblip, aapks.app, apk.watch per-app pages): download buttons JS-loop back to the same page or a QR of it — no raw file exists behind them. Confirmed by grepping the href of the download button == the page you are on.
- CNET download pages return 0 bytes to curl from a server IP (aggressive bot block).
- The Cloudflare "Attention Required" challenge also hits the real-browser tool from a datacenter box, not just curl — do not burn the session driving a browser at APKMirror expecting it to bypass.
- Workable route from a blocked host: hand over the exact archive page URL for the user to click. Their residential IP passes the Cloudflare/JS challenge where a datacenter IP does not. APKs here are small (0.5-5 MB); a manual click is seconds.

## 4. Verify ANY downloaded file is a real APK before trusting it
First two bytes must be zip magic `PK`:

    head -c2 file.bin | od -An -c      # expect ` P K `

HTML error/redirect/JS-challenge pages return `<!`/`<h`/`HTTP` instead. Also cross-check byte size against the published APK size (AppBrain lists it) before treating the file as good. Check the bytes of what you DID get before retrying a different mirror.

## 5. License-checked paid apps: getting the APK is not making it work
Delisted PAID apps (and feature/plugin apps like Torque PID packs, $9.99 'plugins') do a Google-Play license validation on first run — the developer's own install notes say "be sure to have an active internet connection for purchase authorization" / "purchases are validated". A clean sideload with no valid Play purchase record fails that check, so the injected feature never appears — the exact 'installed but PIDs show brown / nothing returns' complaints in the reviews.
- So the only copies that "just work" are license-patched builds circulating on the piracy aggregate mirrors (apkdone / happymod / apkhome), not reputable archives. Flag that the user is trusting an unknown patcher with the APK.
- BEFORE recommending the relic: check whether the feature is a thin config/definition layer (a small APK = just PID/plugin definitions) whose data is publicly documented and can be typed straight into the HOST app's own editor. That route is free, no license check, and survives host-app updates. Do not fabricate the config values from memory — offer to pull the documented table (forum/guide) instead.

## 6. Install a prebuilt APK
    adb install -r file.apk          # adb install -r -d file.apk to allow downgrade
    # or adb push file.apk /sdcard/ then use the target's package installer for head units without adb-over-Play

## Pitfalls
- curl-scraping the JS-gated mirrors for a raw .apk burns cycles and returns an HTML challenge page, not a file. Detect it with the `PK` check and pivot to a real-browser click instead of grinding mirrors.
- Don't mistake 'still on Play' (200) for 'removed' — the user's phrasing 'no longer on the store' is often wrong for abandonware that merely stopped updating.
- APKCombo returning an XAPK is not a bug in the fetch; it is their normal delivery. You need an XAPK/APKS installer or must split the bundle.
