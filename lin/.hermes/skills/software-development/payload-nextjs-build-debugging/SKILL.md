---
name: payload-nextjs-build-debugging
description: Debug and fix Payload CMS + Next.js build failures — database schema migration issues, SSG worker race conditions, recursive API routes, and Tailwind v4 desync.
---

# Payload CMS + Next.js Build Debugging

## When To Use
`next build` fails with `relation "X" does not exist` errors, or Payload drops/recreates tables during build, or API routes hang/crash during SSG.

## Root Causes (check these first)

### 1. PAYLOAD_DROP_DATABASE=true in .env
Payload drops ALL tables on startup when this is set. During `next build`, multiple SSG workers initialize Payload in parallel — they race, drop each other's tables, and fail.

**Fix:** Override during build:
```bash
PAYLOAD_DROP_DATABASE=false npm run build
```
Or remove it from `.env` permanently.

### 2. push: true (default) causes schema sync during build
Payload's postgres adapter calls `pushDevSchema()` during init when `push !== false` and `NODE_ENV !== 'production'`.

**Fix:** Add `push: false` to the DB adapter config:
```ts
db: postgresAdapter({
  pool: { connectionString: process.env.DATABASE_URL || '', max: 5 },
  push: false,  // <-- prevents schema sync during build
}),
```
Then run migrations separately:
```bash
node node_modules/.bin/payload migrate
```

### 3. Outdated migration files
When collections are added/modified after the last migration was generated, Payload detects a schema mismatch and may drop/recreate tables.

**Fix — regenerate migrations:**
```bash
# 1. Delete old migrations
rm -rf src/migrations/*.ts src/migrations/*.json

# 2. Generate fresh schema from current collections
node node_modules/.bin/payload generate:db-schema

# 3. Create new migration from diff
# (if it prompts about enum renames, pipe 'yes')
echo yes | node node_modules/.bin/payload migrate:create --file fresh-migration

# 4. Apply it
node node_modules/.bin/payload migrate
```

### 4. Self-referencing Next.js API routes
If your Next.js route handler at `src/app/api/condolences/route.ts` (or similar) makes an HTTP fetch to `${payloadUrl}/api/condolences`, and `payloadUrl` resolves to the same server, it creates infinite recursion.

**Fix:** Use Payload's local API instead of HTTP:
```ts
import { getPayload } from '@/lib/payload'

export async function POST(req: NextRequest) {
  const payload = await getPayload()
  const doc = await payload.create({
    collection: 'condolences',
    data: { /* ... */ },
  })
}
```
Check if a `getPayload()` helper already exists at `@/lib/payload` — if not, create one:
```ts
import payload from 'payload'
import config from '@/payload.config'

let cachedPayload: typeof payload | null = null

export async function getPayload() {
  if (!cachedPayload) {
    cachedPayload = await payload.init({ config })
  }
  return cachedPayload
}
```

### 5. Tailwind v4 globals.css
If you see Tailwind build errors for custom classes like `bg-brand-ivory` or `font-sans`:

**Fix — v4 syntax:**
```css
@import "tailwindcss";

@theme {
  --color-brand-ivory: #FAF8F5;
  --color-brand-plum: #4A3F44;
  /* ... add all custom brand colors ... */
}
```
Replace `@tailwind base/components/utilities` with `@import "tailwindcss"`.

### 6. No database available during build
If Postgres isn't running, the build fails immediately.

**Quick fix — Docker test database:**
```bash
docker run -d --name test-pg \
  -e POSTGRES_USER=myapp \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=myapp_db \
  -p 5433:5432 postgres:16-alpine

# Use port 5433 in DATABASE_URL
DATABASE_URL=postgresql://myapp:test@localhost:5433/myapp_db
```

## Debugging Workflow

1. **Check `.env`** — is `PAYLOAD_DROP_DATABASE=true`? Override or remove.
2. **Check DB tables** — `\dt` in psql. Empty? Run `payload migrate`.
3. **Check migration files** — do they match current collections? If stale, regenerate.
4. **Check payload.config.ts** — is `push: false` set? Is `max: 1` in pool config set?
5. **Check full build output** — `npm run build 2>&1 | grep -i "drop\|relation\|error"`
6. **Check for recursive API routes** — grep for `fetch.*api.*collection` in API route handlers.

## Verification
```bash
# Clean build cache
rm -rf .next

# Run with DROP disabled
PAYLOAD_DROP_DATABASE=false npm run build

# Verify all pages render
npm run start &
curl -sL -w '%{http_code}' http://localhost:3000/en
curl -sL -w '%{http_code}' http://localhost:3000/api/obituaries/1
```
