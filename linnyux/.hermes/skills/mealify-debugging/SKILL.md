---
name: mealify-debugging
description: 'Diagnose and fix Mealify application issues: auth/signup failures, backend auth stabilization, codebase canon cleanup, and Expo/Android build & debug.'
---

# Mealify Debugging

Troubleshooting for Mealify application across auth, backend, codebase health, and Android build.

## When to Use

Triggers:
- Mealify signup/login/validate fails locally or in smoke tests, including "network error" on device
- Backend auth test failures after JWT/config changes
- Codebase alignment with project roadmap/canon
- Expo APK build failures, missing JS bundle, or app crash on device
  - "No QueryClient set" or "Unable to load script" errors on device
  - App shows "network error" on signup — check backend is running first (see ref 5, step 0)
  - Signup fails with 409 Conflict — email already exists in DB (see ref 5, "409 Conflict on signup")
  - "invalid value provided to securestore" on signup/login — API response parsing mismatch (see ref 5, "invalid value provided to securestore")
  - GoTrue auth migration: GoTrue in Docker, API routes proxied, JWT fallback chain, mobile HTTPS URL (see ref 7, Auth Architecture Migration)
  - GoTrue Docker won't start: schema/auth missing, postgres role missing, search_path wrong, port conflicts (hindsight uses 9999)
  - GoTrue /token endpoint uses grant_type as query param (not form body or JSON body field)
  - Legacy user fallback: GoTrue-first, bcrypt-second login chain for migration period
  - Auth error UX principle: API error messages must be user-facing (not HTTP-status-oriented). A 409 should read "This email is already registered. Please sign in instead." not "User already exists". The mobile error handler must extract `error.response?.data?.message` rather than showing raw Axios error text.
  - GoTrue /token endpoint requires grant_type as query param (not form body). Use `POST /token?grant_type=password` with JSON body {email, password}.
  - mkcert on headless Linux: set CAROOT and MKCERT_DISABLE_KEYTOOL=1 to bypass Java keytool errors
  - Android network_security_config.xml needed for debug builds to trust local HTTPS (mkcert) certs

## Sub-workflows

### 1. Auth Debugging Playbook
See: `references/auth-debugging-playbook.md`
End-to-end workflow for diagnosing auth/signup failures involving schema init, JWT config, and token validation.

### 2. Backend Auth Stabilization
See: `references/backend-auth-stabilization.md`
Fix backend auth/tests by handling JWT env propagation, schema sync at startup, and middleware consolidation.

### 3. Canon Cleanup
See: `references/canon-cleanup-playbook.md`
Align the mealify codebase with project roadmap and blueprint conventions.

### 4. Theme Compat Layer Pattern
See: `references/theme-compat-pattern.md`
When screens reference flat `Theme.colors.primary` but the canonical tokens are nested under `sys.*`/`accent.*`/`sem.*`, create a flat compat layer in DesignSystem.js instead of rewriting every screen.

### 5. Expo Android Build & Debug
See: `references/expo-android-build-debug.md`
Build a debug APK from the Expo source, install on OPPO/Android device, and diagnose runtime errors (missing QueryClientProvider, missing JS bundle, OPPO-specific quirks, SecureStore value errors, 409 conflicts). Covers the manual two-step build pipeline (`react-native bundle` -> `gradlew assembleDebug`) plus ADB install and log reading.

### 6. Auth Architecture Migration
See: `references/auth-architecture-migration.md`
Planned migration from Fastify JWT auth to self-hosted Supabase Auth (GoTrue) + SQLCipher offline encrypted DB. Reference for architecture decisions, data flow, and migration step order.