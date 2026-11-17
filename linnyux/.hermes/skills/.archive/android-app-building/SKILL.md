---
name: android-app-building
description: Clone, configure, and build Android apps from source — Gradle, AGP, Kotlin, product flavors, signing configs, and common build pitfalls on Linux.
trigger: user asks to build, compile, or assemble an Android application from source
---

# Android App Building

Build an Android application from a git repository.

## Steps

1. **Clone the repo** — `git clone <url> && cd <dir>`
2. **Check Android SDK** — verify `ANDROID_HOME` or `ANDROID_SDK_ROOT` is set and points to a valid SDK with matching platforms/build-tools
   - `ls $ANDROID_HOME/platforms/` — must have the `compileSdk` version (e.g. android-36)
   - `ls $ANDROID_HOME/build-tools/` — must have a matching build-tools version
   - If unset, export: `export ANDROID_HOME=~/Android/Sdk`
3. **Check Java** — `java -version` — must be at least Java 17 (AGP 8.x+ needs 17+, AGP 9.x needs 21+)
4. **Check the build system** — look for:
   - `gradlew` — use this, not system gradle
   - `settings.gradle.kts` — shows included modules
   - `build.gradle.kts` at root — shows AGP version, plugins
   - `gradle/libs.versions.toml` — version catalog with dependency versions
5. **Check signing** — scan `app/build.gradle.kts` for `signingConfigs` and `storeFile`. Debug builds need no signing. Release builds need keystore properties set in `~/.gradle/gradle.properties` (typically `OPENCLAW_ANDROID_STORE_FILE`, `OPENCLAW_ANDROID_STORE_PASSWORD`, `OPENCLAW_ANDROID_KEY_ALIAS`, `OPENCLAW_ANDROID_KEY_PASSWORD`)
6. **Check shared resources** — if the build references paths outside the module (e.g. `../../shared/`), verify they exist
7. **Run the build** — `cd <module-dir> && ./gradlew assembleDebug` (or `assembleRelease` for signed builds)
   - First build downloads dependencies — expect 2-5 minutes
8. **Locate APK** — `find app/build/outputs/apk -name "*.apk"`
   - Debug APKs are unsigned, ready to sideload
   - Release APKs need the flag `install -t` for test-only APKs
9. **Install on device** — `adb install <path-to-apk>`

## Product Flavors

Many apps use product flavors (e.g. `play` and `thirdParty`). Build a specific flavor with:
```
./gradlew assemble<Flavor>Debug   # e.g. assemblePlayDebug
./gradlew assemble<Flavor>Release
```

## Common Pitfalls

- **ANDROID_HOME not set** — the Gradle daemon won't find the SDK. Export it explicitly or set `local.properties` with `sdk.dir=/path/to/sdk`
- **compileSdk mismatch** — check `build.gradle.kts` `compileSdk = N`, then verify `platforms/android-N` exists in the SDK. Install it via `sdkmanager "platforms;android-N"` if missing
- **Java version mismatch** — AGP 9.x requires JDK 21+. `java -version` shows the current one. Use `sdk use java <version>` or update alternatives
- **Shared resources not found** — some projects reference resources from sibling directories (e.g. a shared Swift package). Create a symlink or verify the relative path resolves at build time
- **ktlint/check failures** — `warningsAsErrors = true` means lint warnings fail the build. For a quick debug APK, you can skip checks with `-x ktlintMainSourceSetCheck -x lint`
- **Minification errors** — release builds with `isMinifyEnabled = true` fail if ProGuard rules are incomplete. Run debug builds first to isolate

## Post-Build: Installing & Connecting

After building, install the APK on a connected device via:
```sh
adb install -r <path-to-apk>
adb reverse tcp:<gateway-port> tcp:<gateway-port>   # if gateway is loopback-bound
```

For connection setup details (gateway bind modes, Tailscale Serve, auth token, pairing approval), see `references/openclaw-android.md` — Gateway Connection section.

## References

See `references/` for per-project build details and connection setup.
