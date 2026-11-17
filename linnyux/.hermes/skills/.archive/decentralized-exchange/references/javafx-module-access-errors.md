# JavaFX Module Access Errors (JFoenix)

Haveno uses JFoenix (a JavaFX Material Design library) which accesses internal JavaFX APIs.
Java 21+ enforces module access restrictions that JFoenix doesn't handle.

## Error Patterns and Fixes

### JFXSpinnerSkin → NodeHelper

```
class com.jfoenix.skins.JFXSpinnerSkin cannot access class com.sun.javafx.scene.NodeHelper
because module javafx.graphics does not export com.sun.javafx.scene to unnamed module
```

**Fix:** `--add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED`

### JFXTabPaneSkin → TabPaneBehavior

```
class com.jfoenix.skins.JFXTabPaneSkin cannot access class com.sun.javafx.scene.control.behavior.TabPaneBehavior
because module javafx.controls does not export com.sun.javafx.scene.control.behavior to unnamed module
```

**Fix:** `--add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED`

### JFXTabPaneSkin$TabHeaderContainer → LambdaMultiplePropertyChangeListenerHandler

```
class com.jfoenix.skins.JFXTabPaneSkin$TabHeaderContainer cannot access class
com.sun.javafx.scene.control.LambdaMultiplePropertyChangeListenerHandler
because module javafx.controls does not export com.sun.javafx.scene.control to unnamed module
```

**Fix:** Both `--add-exports` AND `--add-opens` are needed:
```
--add-exports javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED
--add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED
```

## Complete Flag Set

All known flags needed for Haveno v1.6.0 with Liberica FX 21.0.2:

```
--add-exports javafx.graphics/com.sun.javafx.scene=ALL-UNNAMED
--add-exports javafx.graphics/com.sun.javafx.stage=ALL-UNNAMED
--add-exports javafx.graphics/com.sun.javafx.util=ALL-UNNAMED
--add-exports javafx.base/com.sun.javafx.reflect=ALL-UNNAMED
--add-exports javafx.controls/com.sun.javafx.scene.control.behavior=ALL-UNNAMED
--add-exports javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED
--add-opens javafx.controls/com.sun.javafx.scene.control=ALL-UNNAMED
```

## Verification

After adding flags, verify they're active in the running process:

```bash
cat /proc/$(pgrep -f "desktop-1.6" | head -1)/cmdline | tr '\0' '\n' | grep add-exports
```

Should show 6 `--add-exports` lines and 1 `--add-opens` line.
