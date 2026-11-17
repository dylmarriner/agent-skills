# Haveno Build Reference (June 2026)

Built from official repo `https://github.com/haveno-dex/haveno.git` at tag v1.6.0.

## Java Setup
- JDK: Liberica 21.0.2.fx-librca (includes JavaFX for desktop UI)
- SDKMan manages the Java version
- The system-packaged `openjdk-21-jdk` does NOT include JavaFX — must use Liberica

## Build Output
```
desktop/build/libs/desktop-1.6.0-SNAPSHOT-all.jar    186MB  (fat jar, use this)
desktop/build/libs/desktop-1.6.0-SNAPSHOT.jar          4MB   (needs classpath)
daemon/build/libs/daemon.jar                          107KB
cli/build/libs/cli.jar
seednode/build/libs/seednode-all.jar
```

## Mainnet Launch

Haveno uses JFoenix JavaFX components that require module access flags on JDK 21+. Without these flags, the splash screen spinner and tab pane will throw `IllegalAccessError` and the GUI window won't render — the process appears to hang with CPU at 100%.

```bash
cd ~/Documents/haveno
source ~/.sdkman/bin/sdkman-init.sh
java \
  --add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED \
  --add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED \
  --add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED \
  --add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED \
  --add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED \
  --add-exports javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED \
  --add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED \
  -jar desktop/build/libs/desktop-1.6.0-SNAPSHOT-all.jar \
  --baseCurrencyNetwork=XMR_MAINNET \
  --useLocalhostForP2P=false \
  --useDevPrivilegeKeys=false \
  --nodePort=9999 \
  --appName=Haveno \
  --apiPassword=apitest \
  --apiPort=1201 \
  --useNativeXmrWallet=false \
  --ignoreLocalXmrNode=false
```

## JFX Error Reference

If you see:
- `JFXSpinnerSkin cannot access NodeHelper` — missing `--add-exports javafx.graphics/com.sun.javafx.scene`
- `JFXTabPaneSkin cannot access TabPaneBehavior` — missing `--add-exports javafx.controls/com.sun.javafx.scene.control.behavior`
- `JFXTabPaneSkin$TabHeaderContainer cannot access LambdaMultiplePropertyChangeListenerHandler` — missing `--add-exports javafx.controls/com.sun.javafx.scene.control` AND `--add-opens javafx.controls/com.sun.javafx.scene.control`

Apply all flags above to fix all three at once.

## Built-in Tor
Haveno bundles its own Tor binary (the `tor-binary-linux64-*.jar` dependency). It starts its own Tor daemon internally — no need for proxychains or system Tor.

## Update
```bash
cd ~/Documents/haveno
git pull
source ~/.sdkman/bin/sdkman-init.sh
make skip-tests
```

## API
Haveno exposes a JSON-RPC API on the configured `--apiPort`. Use `--apiPassword` for auth.
