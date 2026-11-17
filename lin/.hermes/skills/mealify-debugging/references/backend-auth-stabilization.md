---
name: mealify-backend-auth-stabilization
description: Stabilize Mealify backend auth/tests by handling JWT env setup, Jest module reloads, Sequelize model reattachment, and password-reset email configuration.
metadata:
  category: software-development
---

# Mealify Backend Auth Stabilization

Use this skill when Mealify backend auth tests or runtime behavior become brittle around JWT config, Jest module resets, Sequelize model initialization, or password-reset email behavior.

## When to use
- `backend/tests/auth.test.js` fails after auth/controller changes
- JWT secret handling differs between runtime and tests
- `jest.resetModules()` causes stale model/controller state
- password reset flows fail because `FRONTEND_URL` is missing
- email preview logging is noisy or keeps running after tests

## Core lessons learned
- Backend login returns `accessToken` and `refreshToken`; mobile or tests must not assume `token`.
- Some test setups need auth modules to be re-required after setting env secrets so they read fresh config.
- The Sequelize model registry may need to be reattached to `sequelize.models` after module reloads.
- Password-reset email flows require `FRONTEND_URL` to build reset links.
- Preview URL logging should be conditional and non-blocking in non-production.
- Live runtime auth failures can be caused by startup-time env hydration, not just controller logic; make sure JWT secrets exist before token generation in the actual running process.
- If the code looks fixed on disk but the live endpoint still shows the old JWT error, assume the process is stale until you do a clean backend restart and confirm the restarted PID is running `node src/index.js`.
- If the live process keeps emitting `secretOrPrivateKey must have a value`, add focused logging around the controller catch block to print the exact exception and re-hit the endpoint before changing more code.
- If the code change is verified on disk but the live endpoint still shows the old error, do a clean restart of the running backend process and confirm the restarted PID is the updated `node src/index.js` instance before changing more code.
- Keep server bootstrap and module import separate (`require.main === module`) so tests can import startup helpers without accidentally binding ports or leaving open handles.
- If a register/login request still returns a generic 500 after tests pass, add temporary focused logging around the controller catch block to print the real exception name/message/stack and request body.
- Verify the live process is the updated `node src/index.js` instance and confirm the exact exception line from stdout/stderr before changing more code.
- Prefer using the resolved JWT config module value directly in token signing code rather than relying on `process.env` at the call site, especially when runtime env hydration has been flaky.
- If live logs seem to show the old exception after a patch, assume the process is stale until proven otherwise; restart once, then re-hit the endpoint and read fresh logs.

## Workflow

1. Reproduce the exact auth failure
   - Run the smallest relevant test command first.
   - Prefer one of:
     - `npm test -- --runInBand backend/tests/auth.test.js`
     - `npm test -- --runInBand backend/tests/jwt_config.test.js`
     - `npm test -- --runInBand backend/tests/startup_smoke.test.js`

2. Check env/config assumptions
   - Confirm `JWT_SECRET` and `JWT_REFRESH_SECRET` are set before requiring auth code in tests.
   - If the project supports alternate env names, keep fallback support in the config module, not scattered across tests.
   - For password reset tests, set `FRONTEND_URL` to a real URL before calling the controller.

3. Handle Jest module reloads carefully
   - If a test needs fresh config, call `jest.resetModules()` before re-requiring the controller or model module.
   - Re-require only the module that must see the fresh env state.
   - Avoid leaving temporary reload logic in production code.

4. Verify Sequelize model availability
   - If you see `SQLITE_ERROR: no such table: users`, inspect whether the model registry is still attached after reload.
   - A safe pattern is to ensure the model index reattaches the initialized model map onto `sequelize.models`.
   - Confirm `sequelize.sync({ force: true })` is run in the test setup before creating seed records.

5. Keep email side effects quiet in tests
   - Mock `sendPasswordResetEmail` where possible.
   - Build reset links from `FRONTEND_URL` only.
   - Preview logging should be conditional on a real preview URL and should not fail the request path.

6. Verify the fix
   - Run the targeted backend auth, JWT config, and startup smoke tests together.
   - Confirm all pass before moving on.

## Useful code locations
- `backend/src/controllers/auth_controller.js`
- `backend/src/config/jwt.js`
- `backend/src/models/index.js`
- `backend/src/services/email_service.js`
- `backend/tests/auth.test.js`
- `backend/tests/jwt_config.test.js`
- `backend/tests/startup_smoke.test.js`

## Pitfalls
- Leaving test-only env mutations unreset
- Requiring auth modules before setting env values
- Assuming `User.create` failing means the model is wrong, when the issue is often module reload/state loss
- Forgetting to set `FRONTEND_URL` in reset-password tests
- Writing assertions against `json` when the response spy is on `res.json`

## Verification checklist
- `auth.test.js` passes
- `jwt_config.test.js` passes
- `startup_smoke.test.js` passes
- No stray email preview logs or async test noise
- No stale module reload regressions

## Notes
This skill captures the repeated Mealify backend auth/test stabilization pattern so future fixes start from the known-good test and config flow instead of rediscovering the same reload and env pitfalls.