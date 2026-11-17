---
name: expo-mobile-verification
description: Verify a React Native/Expo mobile app after dependency installation, including lint-only projects, Expo web startup, port-conflict handling, browser/process checks, and auth/session debugging when the web UI appears stuck on the login screen.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# Expo Mobile Verification

Use this skill when you need to install dependencies and run a real verification pass for an Expo / React Native app.

## When to trigger
- The user asks to install dependencies and verify the app
- The mobile app has lint/test scripts but no build script
- Expo web start is used as a smoke test
- The web server starts but the browser looks empty or non-rendering

## Workflow

1. Install dependencies
   - Run the package install command in the mobile app directory.
   - Prefer the app package prefix if the repo is a monorepo.
   - Verify the install succeeded before moving on.

2. Discover the real supported verification commands
   - Run `npm run` (or equivalent) for the app package.
   - Do not assume a `build` script exists.
   - Use the scripts that are actually present, usually `lint`, `test`, `web`, `android`, or `ios`.

3. Run the supported verification command first
   - If `lint` exists, run it.
   - If `lint` fails, fix real syntax errors before chasing warnings.
   - Warnings are useful, but parse/runtime errors are the blockers.

4. Start Expo web as a smoke test if appropriate
   - Use `expo start --web` or `npx expo start --web`.
   - If port 8081 is busy, start on another port instead of stopping early.
   - Example: `npx expo start --web --port 8082`

5. Confirm the web server is actually reachable
   - Poll the process if started in the background.
   - Use a browser session or local HTTP check to confirm the page is reachable.
   - If the page is blank, check the browser console before concluding it failed.
   - For auth flows, check the visible route/title/body after successful login or signup; if the app still shows the auth shell on a fresh navigation, treat it as a web runtime/session issue until proven otherwise.

6. Handle empty-page or blank-render cases
   - A reachable Expo web server with a blank page may indicate a runtime or bundling issue.
   - Check browser console output for errors.
   - Check the process logs for Metro/Expo warnings.
   - Only call it a successful web smoke test if the app renders or console is clean.

## Common pitfalls
- Assuming there is a `build` script when only `lint` and `web` exist
- Treating lint warnings as hard failures
- Ignoring a port conflict prompt in non-interactive mode
- Starting Expo web on 8081 when another process already owns it
- Declaring success from a running process without checking browser reachability
- Forgetting that monorepo workspaces can make Metro watch the repo root instead of the app root
- Fix: add an explicit mobile `metro.config.js` that pins `projectRoot`, `watchFolders`, and `resolver.nodeModulesPaths`
- Leaving Expo Router enabled in config while the app still uses `App.js` / `registerRootComponent`
- Fix: either adopt a real `app/` router tree or remove router assumptions from the config/entrypoint path
- If Expo Router is present in the dependency tree, the generated web HTML may still reference `transform.routerRoot=app` even when the app is App.js-based
- Fix: ensure the entry strategy and Expo config agree; otherwise add a minimal `app/index.js` shim or remove router assumptions consistently
- Importing native-only modules at top level in code paths that must bundle for web
- Fix: guard the import with `try/catch` + `require(...)`, or lazy-load the module only in platform-specific execution paths
- Throwing at module import time for missing web config values; prefer safe defaults or lazy access
- Fix: return a local dev default or defer resolution until the client is configured
- A blank browser page can still be a successful server state; verify the bundle response body first to distinguish blank DOM from Metro failures.
- Fix: inspect the bundle response body first; Metro often returns the real resolver error in JSON.
- If Expo web renders the static shell but never mounts React, inspect the bundle for unresolved imports or router/runtime mismatches before changing app code.
- Expo Router can keep influencing web output even in an App.js-based app. If the HTML still shows `transform.routerRoot=app` and the page stays empty, treat that as a build/runtime mismatch and remove or neutralize the router dependency/config, then reinstall/restart before retesting.
- After removing an influencing package like expo-router, re-run the web bundle and watch for secondary resolver failures from transitive dependencies (for example React Navigation requiring `fast-deep-equal`). Fix the next missing package before assuming the app itself is broken.
- In a browser test session, a stale tab or about:blank can hide a working app; retry with a fresh navigation or cache-busting URL before concluding the render is broken.
- When the page renders only after a fresh navigation, report the browser/session issue separately from code/build health.
- React Native Web touchables may not show up as directly clickable refs in browser snapshots; add `accessibilityRole`, `accessibilityLabel`, or `testID` to make key controls visible to browser automation.
- If a browser page seems stuck after submit even though the backend request succeeds, force a fresh navigation/cache-busting URL before concluding the app is broken; the visual state can lag behind a working request.
- When a submit control does not appear as a snapshot ref, verify the exact browser-side API call with the same payload before changing backend code; the issue may be automation visibility rather than app logic.
- If auth or sign-up succeeds at the backend but the web app does not visually transition, check for stale browser state and also confirm the post-auth route name exists in the navigator; a bad route alias can make a working request look like a dead screen.
- If Expo web still renders the auth shell after a successful login even though auth state code looks correct, add an explicit post-auth navigation reset (e.g. `navigation.reset({ routes: [{ name: 'Main' }] })`) in the auth screen temporarily to distinguish a rendering/session issue from a state propagation issue.
- In browser automation, document-level storage access can be restricted; if `localStorage` inspection throws a security error, rely on the app’s visible route/title/body, backend responses, and explicit navigation state rather than assuming token persistence is broken.
- For Expo web + React Navigation, a fresh browser load that still lands on the auth shell with the correct title/route often means the web runtime/session is the blocker, not the backend auth API or missing tab routes.
- Before changing navigation code, verify the backend auth contract directly (register/login responses, token field names, and live server restart state). A stale backend process or an old token contract can produce the same “stuck on auth screen” symptom as a frontend bug.
- If a backend auth fix is made but live requests still show the old failure, cleanly restart the running server process before retesting. A stale process can keep serving the pre-fix code even when the files and tests are already green.
- When the browser remains on the auth shell after successful sign-in/sign-up, re-open the app with a fresh navigation or cache-busting URL before blaming the UI. Expo web/browser sessions can preserve stale visual state even when the auth API is working.
- Always verify the exact live backend responses first: register should return 201 and login should return 200 with accessToken/refreshToken before investigating navigator behavior.
- If the browser title changes but the React tree never mounts and the root stays empty, assume a web bootstrap/runtime mismatch before rewriting auth or tab logic.
- A missing React hook import can produce a blank web render instead of an obvious red screen; check the first screen and navigator imports if the app appears black/empty after a seemingly harmless edit.

## Verification checklist
- Dependencies installed successfully
- The actual package scripts were inspected
- Real verification command passed (or the exact blocker was identified)
- Expo web was started on an available port if needed
- Browser/process checks were used to confirm the server was reachable
- Any syntax errors were fixed and lint rerun
- If web bundling failed, inspect the bundle response body for the actual Metro error
- In monorepos, confirm Metro projectRoot/watchFolders/nodeModulesPaths point at the mobile app
- Ensure web bundle paths match the intended entry strategy (router vs App.js)

## Reporting
When reporting back, state:
- what command(s) were run
- whether installation succeeded
- whether lint/build/web checks passed
- any blockers and how they were resolved
- whether the result is a warning-only pass or a true clean pass
