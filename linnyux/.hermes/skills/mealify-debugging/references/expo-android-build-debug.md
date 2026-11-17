# Expo/RN Android Build & Debug for Mealify

End-to-end workflow for building a debug APK, installing on an OPPO/Android device, and diagnosing runtime errors.

## Prerequisites

- Android SDK at `$ANDROID_HOME` (this device: `/home/kubuntux/android-studio/sdk`)
- Device connected via ADB (OPPO A40 vendor ID `22d9`)
- pnpm workspace root at `/media/kubuntux/DEVELOPMENT1/Mealify`

## Step 0: Check backend is running first

Signup/login failures often show "network error" when the API server isn't running at all. Before building/debugging:

```bash
curl -s http://100.93.75.87:3000/health
```

If it fails (no response / exit code 7), start the backend:

```bash
# Start in background (long-lived)
cd /media/kubuntux/DEVELOPMENT1/Mealify
pnpm --filter @mealify/api dev
```

Wait ~5s then verify with `curl` before testing the app.

**Pitfall:** The app targets `100.93.75.87:3000` (Tailscale IP), not `localhost`. If testing from a separate device connected via Tailscale, that IP works. If testing on the same machine, it also works since Tailscale routes locally. Don't change the API URL in the app — the server needs to bind to `0.0.0.0` (which `startServer` does) and the device needs to reach that IP.

**Pitfall:** `pnpm --filter @mealify/api dev` must run in the background (`background=true` in terminal tool) because ts-node blocks the foreground. After starting, verify with a separate health-check call before proceeding.

## Step 1: Prebuild native code (first time or after expo version bump)

```bash
cd apps/mobile
ANDROID_HOME=/home/kubuntux/android-studio/sdk npx expo prebuild --platform android
```

This generates the `android/` directory. Re-run if changing `app.json` or Expo SDK versions.

## Step 2: Bundle the JS

```bash
cd apps/mobile
ANDROID_HOME=/home/kubuntux/android-studio/sdk npx react-native bundle \
  --platform android \
  --dev false \
  --entry-file index.js \
  --bundle-output android/app/src/main/assets/index.android.bundle \
  --assets-dest android/app/src/main/res
```

The entry file is `index.js` (not `expo-router/entry`) because the app uses the classic `App.js` + `NavigationContainer` pattern, not Expo Router.

**Pitfall:** If you run `npx expo run:android` it spawns the Metro bundler and hangs in CLI mode. The manual two-step (`bundle` then `gradlew assembleDebug`) is more reliable for headless builds.

## Step 3: Build the APK

```bash
cd apps/mobile/android
ANDROID_HOME=/home/kubuntux/android-studio/sdk ./gradlew assembleDebug
```

APK lands at: `apps/mobile/android/app/build/outputs/apk/debug/app-debug.apk`

## Step 4: Install and launch

```bash
adb install -r apps/mobile/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.dylanmarriner.mealify/.MainActivity
```

## Step 5: Read logs

Clear and check for React Native JS errors:

```bash
adb logcat -c
# wait a few seconds
adb logcat -d | grep -E "ReactNativeJS|CRASH|FATAL|Error|Unable to load|QueryClient"
```

## Local HTTPS Setup (for dev)

When the API URL points to `https://100.93.75.87:8443`, the app needs to trust the dev cert.

### mkcert on headless Linux

```bash
# Install mkcert (Go required)
go install filippo.io/mkcert@latest

# Generate certs (keytool errors are harmless on headless)
cd infra/
CAROOT=$PWD/mkcert-ca MKCERT_DISABLE_KEYTOOL=1 ~/go/bin/mkcert \
  -cert-file mealify-local.pem \
  -key-file mealify-local-key.pem \
  localhost 100.93.75.87 192.168.1.11 mealify.local
```

### network_security_config.xml

For debug builds, user-installed CAs are trusted via:

```xml
<!-- android/app/src/main/res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">100.93.75.87</domain>
        <domain includeSubdomains="true">mealify.local</domain>
    </domain-config>
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>
</network-security-config>
```

Reference this in `AndroidManifest.xml`:
```xml
<application ... android:networkSecurityConfig="@xml/network_security_config">
```

Push the mkcert root CA to the device for user installation (optional — `debug-overrides` trusts user CAs automatically):
```bash
adb push infra/mkcert-ca/rootCA.pem /sdcard/Download/mealify-local-ca.pem
```

### Caddy config

Run Caddy in Docker (port 8443 → 443 for HTTPS) with the mkcert certs. Caddyfile snippet:
```
mealify.local, localhost, 100.93.75.87 {
  tls /etc/caddy/certs/mealify-local.pem /etc/caddy/certs/mealify-local-key.pem
  reverse_proxy /auth/* gotrue:9999
  reverse_proxy /api/* api:3000
}
```

**Pitfall:** Tailscale owns port 443. Use port 8443 externally on dev. Port 80 may be free for HTTP redirect.

**Pitfall:** The API Docker build fails due to pnpm `workspace:*` dependencies — don't include the `api` service in docker-compose up. Run the API locally via `pnpm --filter @mealify/api dev` and start Caddy with `--no-deps`.

## Common Fix Patterns

### "No QueryClient set, use QueryClientProvider to set one"

**Root cause:** `App.js` doesn't wrap the component tree with `<QueryClientProvider>`. The `src/api/hooks/useAuth.ts` hooks call `useAppMutation` from `src/api/client.ts`, which calls `useMutation` from `@tanstack/react-query`. If `QueryClientProvider` is missing from the React tree at render time, these hooks throw this error.

**Fix:** Import `QueryClient` and `QueryClientProvider` in `App.js` and wrap:

```jsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <StatusBar ... />
          <NavigationContainer>
            <AppNavigator />
          </NavigationContainer>
        </AuthProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
```

**Why it fails with Expo Router layouts:** The `_layout.js` may have `QueryClientProvider` wrapping `Stack.Screen` routes, but the entry point (`index.js` → `App.js`) bypasses Expo Router entirely when using classic RN navigation with `NavigationContainer`.

### "Unable to load script" / bundle not found

**Root cause:** JS bundle hasn't been generated into `android/app/src/main/assets/index.android.bundle`. The Gradle build compiles native code but doesn't bundle the JS — that's a separate step.

**Fix:** Run Step 2 (react-native bundle) before Step 3 (gradle assembleDebug). After generating the bundle, rebuild the APK.

### playwright in devDependencies doesn't belong

The scraper worker at `apps/api/workers/` uses `playwright` as a production dependency. The mobile app has `playwright` in its `devDependencies` — remove it since it's not used there and can cause confusion about which packages belong where.

### "invalid value provided to securestore" on signup

**Root cause:** The API wraps all responses with `success()` → `{ ok: true, data: { ... } }`. The `useAuth.ts` hooks destructure `const { accessToken, refreshToken } = response.data`, but:
- `response.data` is the full wrapper object, so the tokens are actually at `response.data.data.token` and `response.data.data.refreshToken`
- The field is `token` (not `accessToken`)

Passing `undefined` to `SecureStore.setItemAsync(key, undefined)` throws "values must be strings".

**Fix in the hook:**
```typescript
const body = response.data?.data || response.data;
const token = body.token;
const refreshToken = body.refreshToken;
if (token) await setAccessToken(String(token));
if (refreshToken) await setRefreshToken(String(refreshToken));
```

Also check callers of `login.mutateAsync` — if they access `result.householdId` directly, that's also nested under `result.user.householdId`.

#### AuthScreen fix example:
```javascript
const result = await login.mutateAsync({ email, password });
if (result.user?.householdId && result.user?.householdName) {
  setSelectedHousehold(result.user.householdId, result.user.householdName);
}
```

### 409 Conflict on signup

**Root cause:** The email address already exists in the database. The backend returns `status 409`.

**Fix:** Query the database to confirm:
```bash
psql -U kubuntux -d mealify -c 'SELECT id, email, "displayName", "createdAt" FROM "User";'
```
If the email belongs to the user, sign in instead of signing up. If they lost the password, delete the row via:
```sql
DELETE FROM "User" WHERE email = 'user@example.com';
```
Then retry signup (this re-creates the user + household).

#### UX: make error messages user-facing, not developer-facing

The API error message matters: `{ message: 'User already exists' }` becomes a raw Axios error text on the device. The fix is two-sided:

**Backend** (`apps/api/src/modules/auth/routes.ts`):
```typescript
// Bad: developer-oriented
return reply.status(409).send({ message: 'User already exists' });

// Good: user-oriented
return reply.status(409).send({ message: 'This email is already registered. Please sign in instead.' });
```

**Mobile** (`apps/mobile/src/screens/AuthScreen.js`):
```javascript
// Bad: shows "Request failed with status code 409"
Alert.alert("Error", error.message || "Authentication failed");

// Good: extracts the actual API message
Alert.alert("Error", error.response?.data?.message || error.message || "Authentication failed");
```

**Principle:** Every API error message should read like something a user could see in a dialog. Don't leak HTTP semantics (status codes, "Conflict", "Bad Request") to the UI layer.

**Pitfall:** Prisma table names are capitalized (`"User"`, `"Household"`, etc.). Raw SQL queries must quote them with double quotes in psql. The `_prisma_migrations` table tracks migration history — if a table is missing, run migrations first.

**Pitfall:** 409 is the only conflict error from the auth routes. A 400 means a required field was missing (`email, password, firstName, and lastName are required`).

## OPPO-Specific Quirks

- The phone shows `vendor.oplus.hardware.charger-V6-service` and `OplusQConfigSetting` errors in logcat — these are normal OPPO system messages, not app issues.
- `no permissions (missing udev rules?)` requires udev rule with vendor ID `22d9`.
- After install, notification shade may obscure the app. Use `adb shell am start` with `--activity-clear-task` to bring it to front.
