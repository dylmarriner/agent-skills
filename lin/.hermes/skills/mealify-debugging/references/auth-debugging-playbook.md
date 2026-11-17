---
name: mealify-auth-debugging-playbook
description: End-to-end workflow for diagnosing and fixing Mealify local auth/signup failures involving schema initialization, JWT config, and token validation.
metadata:
  category: software-development
---

# Mealify Auth Debugging Playbook

Use this when Mealify signup/login/validate fails locally or in live smoke tests.

## Steps
1. Verify backend health endpoint and actual listening port.
2. Reproduce the auth request directly against the backend.
3. Inspect backend logs for the exact exception, not just the HTTP 500.
4. Check schema state for missing tables or unsynced models.
5. Ensure startup runs schema sync/migrations before serving in local dev so auth requests do not fail on missing tables.
6. Make sure local dev startup seeds safe JWT defaults before model initialization if the environment does not provide them, while keeping production strict.
7. Centralize JWT secret configuration in one shared module.
8. Make middleware, token generation, refresh, and revocation all use the shared JWT config.
9. Require explicit JWT env vars in production and fail fast if they are missing; avoid silent fallback secrets.
10. Re-test register, login, and validate end to end with a fresh account under the same runtime config.
11. Run a small targeted test set with explicit JWT env vars so strict config validation and startup smoke tests reflect the real runtime contract.
12. If repeated error-message or env parsing logic appears across controllers/services, move it into a shared helper before broadening the fix.
13. When refactoring env-backed services, verify actual module dependencies after renaming or consolidating imports; a missing service path can slip past lint but fail module-load smoke tests.
14. In Expo web verification, a stale browser tab can go blank even when the bundle is healthy; retry with a fresh navigation/cache-busting URL before treating the page as broken.
15. For React Native Web touchables, add explicit accessibility labels/roles or test IDs to make sign-up/sign-in toggles visible to browser automation.
16. If a web login or signup request appears to fail, first prove whether the auth handler actually ran by adding a temporary visible debug message or checking the console after the click. Distinguish between “button did nothing,” “request failed,” “request succeeded but navigation did not happen,” and “request succeeded but the client still reported a generic sign-in failure.”
17. When a valid Expo web auth response is returned by the backend but the UI still stays on the auth shell, inspect browser storage directly (localStorage/sessionStorage) to confirm whether the token was persisted. A missing token usually means the client write path is the bug, not the navigator.
18. If browser storage is empty after a successful response, fix the web storage path explicitly instead of only changing the navigator; Expo web can behave differently from native AsyncStorage. Use a web-safe storage fallback and rehydrate from it on startup if needed.
19. If the browser UI stays on the auth shell, verify the backend directly with the exact register/login payload before assuming the client is broken; a live 500 can look like a stale transition problem.
20. A backend auth suite can be fully green while the live `/api/auth/register` request still returns 500; always reproduce the live request with `curl` or browser context before trusting tests.
21. When a live register/login request fails but tests pass, inspect the running backend's stdout/stderr or module initialization path, not just Jest output; runtime-only failures often come from startup/config state that tests bypass.
22. Mealify's mobile API client defaults to `http://localhost:3000` in local mode when no explicit API URL is set, so a broken signup smoke test is usually not a base-URL issue unless the browser is pointed elsewhere.
23. The canonical post-auth mobile shell should land on the five tabs: Home, Week, Grocery, Pantry, Insights; if auth succeeds but the UI does not transition, check browser/session staleness before changing the navigator.
24. Register payloads in Mealify currently expect `firstName`, `lastName`, `email`, and `password`; use that exact shape when reproducing runtime auth bugs.
25. When the browser console shows the auth request reaching `/auth/login` but the UI still says “Sign in failed,” treat that as a client-side response-handling or persistence problem until proven otherwise. The backend can be healthy while the app still misreports failure.
26. Add a temporary visible debug string or test ID in the auth screen when browser automation is ambiguous; it helps separate event wiring issues from true network/auth errors.

## Common pitfalls
- API response wrapper destructuring mismatch: The backend wraps all responses with `success()` (→ `{ ok: true, data: { ... } }`), but the mobile hooks often destructure from `response.data` directly. If the hook reads `const { accessToken, refreshToken } = response.data`, both will be `undefined` because the actual tokens live under `response.data.data.token` / `response.data.data.refreshToken` and the key is `token`, not `accessToken`. Passing `undefined` to `SecureStore.setItemAsync()` throws "invalid value provided to securestore. values must be strings". Fix by unwrapping the nested data in the hook: `const body = response.data?.data || response.data; const token = body.token;` and always `String()`-coerce before writing to SecureStore.
- Multiple backend instances pointing at different SQLite files.
- The client app targeting the wrong local backend port or base URL even when the backend itself is healthy.
- Missing JWT_SECRET causing token creation to fail only after signup appears to work.
- A silent JWT fallback masking production config problems.
- Revocation helpers incorrectly treating all tokens as revoked due to bad Op usage or token lookup logic.
- Verifying only one endpoint instead of the whole auth flow.
- Leaving auth, startup, or test suites dependent on implicit env vars.
- A sign-up request can return 201 yet the app still appears stuck if the browser session is stale or the redirect route name does not exist; verify the browser console, auth state, and navigator route names before changing backend code.
- Fixing controller-by-controller error handling without first creating a shared env/error helper.

## Verification
- Register returns 201.
- Login returns 200 with access and refresh tokens.
- Validate returns 200 with the user payload.
- Health endpoint returns 200.
- Startup smoke tests pass with explicit JWT env vars.
- Targeted auth tests pass when explicit JWT env vars are provided.
- Browser smoke test reaches the canonical five-tab app after successful auth.
