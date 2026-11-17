---
name: java-modern-jdk-compat
description: "Fix Java module-access errors when running older JavaFX / Swing apps (JFoenix, JFoenix, etc.) on JDK 21+, OpenHuman, Haveno, Bisq, or any JFoenix-based JavaFX desktop app."
version: 1.0.0
author: Hermes Agent
platforms: [linux]
---

# Java Modern JDK Compatibility

Fix `IllegalAccessError` crashes when running JavaFX desktop apps built with **JFoenix** (or other libraries using internal JDK APIs) on JDK 21+ with the module system.

## When to Use

When any Java desktop application (Haveno, Bisq, OpenHuman, or similar) crashes at startup with:
```
java.lang.IllegalAccessError: class com.jfoenix.skins.JFXSpinnerSkin
cannot access class com.sun.javafx.scene.NodeHelper
```

Or similar errors referencing `com.sun.javafx.*` packages from JFoenix skin classes.

## The Fix: `--add-exports` + `--add-opens` JVM flags

Older libraries (notably JFoenix, used by Haveno and Bisq) access internal JDK APIs that are no longer exported by default in JDK 21+. Add these flags before `-jar`:

```bash
java \
    --add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED \
    --add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED \
    --add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED \
    --add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED \
    --add-exports javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED \
    --add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED \
    -jar app.jar
```

## JFoenix Error → Flag Mapping

| Error pattern | Required flag |
|---------------|---------------|
| `JFXSpinnerSkin` cannot access `NodeHelper` | `--add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED` |
| `JFXTabPaneSkin` cannot access `TabPaneBehavior` | `--add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED` |
| `JFXTabPaneSkin$TabHeaderContainer` cannot access `LambdaMultiplePropertyChangeListenerHandler` | `--add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED` |
| `JFXSpinnerSkin` cannot access `javafx.util` | `--add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED` |

Apply ALL flags proactively — JFoenix will hit multiple errors as each one is fixed. Add the full set from the start.

## JDK Selection

Use a JDK with JavaFX bundled (Liberica FX, BellSoft FX, or Gluon). SDKMan:
```bash
sdk install java 21.0.2.fx-librca
```
The `fx` variant includes JavaFX modules — standard OpenJDK does not.

## Verifying

```bash
# Check the flags are present
ps aux | grep java | tr ' ' '\n' | grep add-exports
# Should show 6+ flags
```

## Common Pitfalls

- **Apply all flags at once** — JFoenix will error out on different internal APIs one by one. Don't fix iteratively; the full set above covers all known JFoenix+v21 internal API accesses.
- **`--add-exports` vs `--add-opens`** — `--add-exports` allows compile-time access; `--add-opens` allows runtime reflective access. JFoenix needs both for different packages.
- **Liberica FX vs standard JDK** — Standard OpenJDK 21 does NOT include JavaFX. The `fx-librca` build from BellSoft/Liberica bundles javafx modules. Install via SDKMan with the `.fx` variant.
- **Extracting .deb without sudo** — When the app's .deb can't be installed via `dpkg -i` (no sudo), extract with `dpkg -x package.deb ~/extract-dir` and run the binary from `extract-dir/opt/<app>/bin/<AppName>` or `extract-dir/usr/bin/<app>`.
