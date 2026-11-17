# Monorepo APK Build: Metro Config for Workspace Packages

When building a React Native debug APK from a **pnpm/npm workspace monorepo**, Metro may fail to resolve `@workspace/*` packages even though they exist in the filesystem. This reference covers the fix patterns.

## Symptom

```
error Unable to resolve module @workspace/package from src/SomeFile.js:
@workspace/package could not be found within the project or in these directories:
  node_modules
  ../../node_modules
  node_modules
```

The app may work fine in Metro dev mode (since dev mode has different resolution) but fail during the `react-native bundle` step.

## Root Cause

Metro's module resolver looks for packages in a flat `node_modules/` directory or in the paths listed in `resolver.nodeModulesPaths`. In a pnpm workspace monorepo:
- Workspace packages (`@mealify/ui`, `@myorg/shared`, etc.) live in `packages/ui/` — not in `node_modules/` unless symlinked
- pnpm creates symlinks in the root `node_modules`, but the mobile app's Metro bundler may not traverse to the root

## Fix: Update `metro.config.js`

Add `extraNodeModules` to resolve workspace packages directly, and include the packages directory in watch folders.

```javascript
const { getDefaultConfig } = require('@expo/metro-config');  // or 'metro-config' for bare RN
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(__dirname, '../..');  // adjust to monorepo root

const config = getDefaultConfig(projectRoot);

// Watch the mobile app, the monorepo root, and the packages dir
config.watchFolders = [
  projectRoot,
  workspaceRoot,
  path.resolve(workspaceRoot, 'packages'),
];

// Include node_modules at project level, workspace root, and package-level
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'packages', 'ui', 'node_modules'),  // if ui has its own deps
];

// Resolve workspace packages by direct path
config.resolver.extraNodeModules = {
  ...config.resolver.extraNodeModules,
  '@mealify/ui': path.resolve(workspaceRoot, 'packages', 'ui'),
  // Add more workspace packages as needed:
  // '@mealify/config': path.resolve(workspaceRoot, 'packages', 'config'),
};

module.exports = config;
```

## Verification

After updating `metro.config.js`:

1. Run bundle with `--reset-cache`:
   ```bash
   npx react-native bundle --platform android --dev false \
     --entry-file index.js --reset-cache \
     --bundle-output android/app/src/main/assets/index.android.bundle \
     --assets-dest android/app/src/main/res/
   ```

2. Check the output ends with:
   ```
   info Writing bundle output to: android/app/src/main/assets/index.android.bundle
   info Done writing bundle output
   info Copying N asset files
   info Done copying assets
   ```

3. Proceed with `./gradlew assembleDebug` and `adb install -r`.

## Alternative: Manual Symlink (less reliable)

If Metro config is locked or you only need a one-off build:

```bash
cd apps/mobile
mkdir -p node_modules/@mealify
ln -sf ../../../../packages/ui node_modules/@mealify/ui
```

**Metro may not follow symlinks** depending on watchman configuration and Metro version. `extraNodeModules` is more reliable.

## Key references
- Metro docs: https://metrobundler.dev/docs/configuration/
- React Native monorepo guide: https://reactnative.dev/docs/monorepo
