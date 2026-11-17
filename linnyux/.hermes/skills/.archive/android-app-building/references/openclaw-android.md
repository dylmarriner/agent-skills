# OpenClaw Android Build

**Repo:** `github.com/openclaw/openclaw` — the only official OpenClaw repo.
  Community forks (AidanPark/openclaw-android, etc.) are unofficial — always use the source of truth.

**Module:** `apps/android/`
**Min SDK:** 31 | **Target/Compile SDK:** 36
**AGP:** 9.2.0 | **Kotlin:** 2.3.21
**Java:** JDK 21+

## Flavors

| Flavor | Description |
|--------|-------------|
| `play` | Google Play Store variant (includes Play Services code scanner) |
| `thirdParty` | Side-load / other stores (no Play Services dependency, full permissions) |

## Build Commands

```sh
cd apps/android
export ANDROID_HOME=~/Android/Sdk
./gradlew assembleThirdPartyDebug          # debug APK, no signing needed
./gradlew assemblePlayDebug                 # debug APK with Play Services
./gradlew assembleThirdPartyRelease         # requires signing config
```

## APK Outputs

```
app/build/outputs/apk/thirdParty/debug/openclaw-{version}-thirdParty-debug.apk
app/build/outputs/apk/play/debug/openclaw-{version}-play-debug.apk
```

## Shared Resources

The Android app references `../../shared/OpenClawKit/Sources/OpenClawKit/Resources/`. This is a Swift package shared with the iOS app — Android only uses the `Resources/` subdirectory (certificates, tool display configs). The `Sources/` Swift source files are not compiled into the Android APK.

## Signing for Release

Set these in `~/.gradle/gradle.properties`:

```
OPENCLAW_ANDROID_STORE_FILE=/path/to/keystore
OPENCLAW_ANDROID_STORE_PASSWORD=...
OPENCLAW_ANDROID_KEY_ALIAS=...
OPENCLAW_ANDROID_KEY_PASSWORD=...
```

The build script will error at configuration time if release tasks are requested without all four properties set.

## Version Catalog

`gradle/libs.versions.toml` — key versions:

- `androidx-compose-bom = "2026.04.01"`
- `okhttp = "5.3.2"`
- `kotlinx-serialization-json = "1.11.0"`
- `coroutines = "1.10.2"`

## Debug vs Release

- Debug: `isMinifyEnabled = false`, no ProGuard, builds fast, no signing required
- Release: `isMinifyEnabled = true`, `isShrinkResources = true`, ProGuard active, requires keystore

---

# Gateway Connection

The Android app is a **remote client** — it connects to your desktop's OpenClaw gateway over WebSocket. It does NOT run the AI agent on-device.

## Architecture

| Component | Runs On |
|-----------|---------|
| AI agent / inference | Desktop OpenClaw gateway |
| Android-specific hardware | Phone (camera, mic, SMS, contacts, location, notifications, motion) |
| Chat UI / Voice / Screen | Phone |
| Canvas / A2UI | Phone |

## Gateway Bind Modes

The gateway's `bind` config determines how it listens:

| Mode | Effect | When to Use |
|------|--------|-------------|
| `loopback` | 127.0.0.1 only, not reachable from network | Tailscale Serve / funnel (required by tailscale) |
| `lan` | 0.0.0.0 (all interfaces) | Direct LAN access, no Tailscale |
| `tailnet` | Binds to Tailscale interface only | Tailscale-only access |
| `auto` | Auto-detect best mode | General use |

```sh
openclaw gateway --port 18789 --bind lan --force
openclaw gateway --port 18789 --bind loopback --force   # needed for tailscale serve
openclaw gateway --port 18789 --bind tailnet --force
```

## Tailscale Serve Setup (Global Access)

If your gateway uses `bind: loopback` and you have Tailscale, expose it via Tailscale Serve:

```sh
# Start gateway on loopback
openclaw gateway --port 18789 --bind loopback --force

# Expose via Tailscale
sudo tailscale serve --bg --https=443 18789
```

This creates a URL like `https://<hostname>.tail<XXX>.ts.net/` -> `http://127.0.0.1:18789`.

**Pitfall:** If `openclaw.json` has `gateway.tailscale.resetOnExit: true`, the serve config is wiped when OpenClaw exits. Re-apply `tailscale serve` after restarting.

### Check Tailscale Serve Status

```sh
tailscale serve status
```

## Connection Methods

### Method 1: Manual Connection (App Connect Tab)

In the Android app: **Connect → Manual**

| Field | Value |
|-------|-------|
| Host | Tailscale hostname (e.g. `lin-host.tail2c15c8.ts.net`) or LAN IP |
| Port | `443` (via Tailscale Serve) or `18789` (direct LAN) |
| TLS | On when using Tailscale Serve (`wss://`), Off for direct LAN (`ws://`) |
| Auth Token | From `openclaw config get gateway.auth.token` or read from `~/.openclaw/openclaw.json` in the `gateway.auth.token` field |

### Method 2: USB Tunneling (adb reverse)

For testing when the device is connected via USB:

```sh
# Terminal A — start gateway
openclaw gateway --port 18789 --bind loopback --verbose

# Terminal B — tunnel
adb reverse tcp:18789 tcp:18789
```

Then in the app: **Connect → Manual** — host `127.0.0.1`, port `18789`, TLS off.

### Method 3: Auto-Discovery (Bonjour/mDNS)

The app discovers gateways on the LAN via Bonjour (`_openclaw-gw._tcp.`). Only works when the gateway is bound to `lan` mode and the phone is on the same WiFi subnet.

## First-Time Pairing

After the app connects, the gateway requires approval:

```sh
# List pending devices
openclaw devices list

# Approve
openclaw devices approve <requestId>
```

Alternatively, approve the most recent request:
```sh
openclaw devices approve --latest   # preview only
openclaw devices approve <requestId>
```

## Pitfalls

- **loopback-bound gateway is invisible to Bonjour discovery** — the app won't auto-discover it. Use manual connection or `adb reverse`.
- **`resetOnExit: true` clears Tailscale Serve** — re-apply `sudo tailscale serve --bg --https=443 18789` after restarting the gateway.
- **Auth token is redacted in `openclaw config get`** — read the raw file at `~/.openclaw/openclaw.json` to get the actual token.
- **App shows "gateway unreachable"** — verify the gateway is running (`ss -tnlp | grep <port>`), the bind mode exposes it on the right interface, and TLS setting matches (WSS for Tailscale, WS for direct).
- **Debug APKs are 90MB** — release builds with `isMinifyEnabled = true` shrink to ~30MB.
- **`--bind lan` conflicts with `tailscale.mode: serve`** — the gateway errors at startup. Set bind to `loopback` when using Tailscale Serve.
