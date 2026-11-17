# Auth Migration: Self-Hosted GoTrue (Phase 1 Complete)

## Architecture

```
                  ┌──────────────────┐
                  │  Mobile App      │
                  │  (Expo SecureStore)│
                  └──────┬───────────┘
                         │ HTTPS (Caddy :8443)
                         ▼
              ┌────────────────────┐
              │ Caddy Reverse Proxy│
              └────┬───────────────┘
                   │
          ┌────────┴────────┐
          ▼                  ▼
   ┌────────────┐    ┌──────────────┐
   │ GoTrue     │    │ Fastify API  │
   │ :9999      │    │ :3000         │
   │ /signup    │    │ /api/*        │
   │ /token     │    │ /auth/* proxy │
   │ /logout    │    │               │
   │ /user      │    │ requireAuth() │
   └──────┬─────┘    └──────┬────────┘
          │                 │
          └────────┬────────┘
                   ▼
          ┌────────────────┐
          │ PostgreSQL     │
          │ schema: public │  ← Mealify tables ("User", "Household", etc.)
          │ schema: auth   │  ← GoTrue tables (users, identities, etc.)
          └────────────────┘
```

## Docker Setup

**GoTrue config** (`infra/docker-compose.yml`):

```yaml
gotrue:
  image: supabase/gotrue:v2.189.0
  ports: ["9998:9999"]  # 9998 external (hindsight uses 9999)
  environment:
    GOTRUE_SITE_URL: https://mealify.local
    API_EXTERNAL_URL: https://mealify.local/auth
    DATABASE_URL: postgresql://mealify:change_me@postgres:5432/mealify
    GOTRUE_DB_DRIVER: postgres
    GOTRUE_DB_NAMESPACE: auth
    GOTRUE_JWT_SECRET: <shared-secret-match-api>
    GOTRUE_JWT_EXP: 3600
    GOTRUE_DISABLE_SIGNUP: "false"
    GOTRUE_EXTERNAL_EMAIL_ENABLED: "true"
    GOTRUE_MAILER_AUTOCONFIRM: "true"
    GOTRUE_SECURITY_REFRESH_TOKEN_ROTATION_ENABLED: "true"
    GOTRUE_LOG_LEVEL: debug
    API_HOST: 0.0.0.0
    PORT: 9999
```

## Database Prerequisites (before starting GoTrue)

GoTrue's migration fails if the `auth` schema and `postgres` role don't exist:

```sql
CREATE SCHEMA IF NOT EXISTS auth;
CREATE ROLE postgres WITH LOGIN SUPERUSER;
ALTER ROLE mealify SET search_path TO '$user', public, auth;
```

The search_path change is critical — GoTrue queries `identities` (no schema prefix) at runtime.

## JWT Chain: Two-Token Fallback

The `requireAuth` middleware tries in order:

1. **GoTrue JWT** — verify with `env.gotrueJwtSecret` (HMAC-SHA256), look up Mealify user by `gotrueId`
2. **Legacy JWT** — verify with old `jwtConfig.JWT_SECRET`, extract userId/householdId directly from payload

This allows migrated users (with `gotrueId`) to use GoTrue tokens while unmigrated users continue using legacy tokens.

The login route mirrors this: GoTrue first, bcrypt fallback second.

## Prisma Schema

```prisma
model User {
  id           String   @id @default(uuid())
  gotrueId     String?  @unique          // ← added for GoTrue linkage
  email        String   @unique
  passwordHash String                       // empty for GoTrue-managed users
  displayName  String
  ...
}
```

## GoTrue API Quirks

| Endpoint | Method | Gotcha |
|----------|--------|--------|
| `/signup` | POST | JSON body: `{email, password}`. Also accepts `data` for user_metadata |
| `/token?grant_type=password` | POST | `grant_type` as **query param**, not body field. JSON body: `{email, password}` |
| `/token?grant_type=refresh_token` | POST | `grant_type` as query param. JSON body: `{refresh_token}` |
| `/logout` | POST | Needs `Authorization: Bearer <token>` header |
| `/user` | GET | Needs auth header. Returns current user info |
| `/health` | GET | Returns `{version, name, description}` (not JSON `ok` wrapper) |
| `/settings` | GET | Public settings (no auth) |
| `/.well-known/jwks.json` | GET | Returns empty `{keys:[]}` for HMAC — GoTrue uses symmetric keys |

## API → GoTrue Proxied Routes

| Route | Action |
|-------|--------|
| `POST /api/auth/register` | → GoTrue `/signup`, then create Mealify User + Household + UserHousehold |
| `POST /api/auth/login` | → GoTrue `/token?grant_type=password` (fallback bcrypt for legacy) |
| `POST /api/auth/refresh` | → GoTrue `/token?grant_type=refresh_token` |
| `POST /api/auth/logout` | → GoTrue `/logout` |
| `GET /api/auth/me` | Local DB lookup by `gotrueId` from decoded JWT |
| `GET /api/auth/validate` | Legacy alias → `/api/auth/me` via `app.inject` |

## Response Formats

**GoTrue /signup response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "...",
  "user": { "id": "uuid", "email": "...", ... }
}
```

**API login response (wrapped):**
```json
{
  "ok": true,
  "data": {
    "user": { "id", "email", "displayName", "householdId", "householdName", "role" },
    "token": "eyJ...",
    "refreshToken": "..."
  }
}
```

## Migration Status

- [x] GoTrue container running in Docker (port 9998 external)
- [x] API auth routes proxy through GoTrue
- [x] JWT verification uses shared secret
- [x] Legacy fallback for unmigrated users
- [x] Prisma schema has `gotrueId` column
- [ ] All existing users migrated to GoTrue
- [ ] SQLCipher offline DB
- [x] HTTPS via Caddy (cert issued, port 8443, network_security_config.xml for Android dev)
