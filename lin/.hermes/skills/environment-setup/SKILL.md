---
name: environment-setup
description: Configure and manage development, staging, and production environments. Use when setting up environment variables, managing configurations, or separating environments. Handles .env files, config management, and environment-specific settings.
allowed-tools: Read Write Edit Bash
metadata:
  tags: environment, configuration, env-variables, dotenv, config-management
  platforms: Claude, ChatGPT, Gemini
---


# Environment Configuration


## When to use this skill

- **New Projects**: Initial environment setup
- **Multiple Environments**: Separate dev, staging, production
- **Team Collaboration**: Share consistent environments

## Instructions

### Existing repository setup workflow

1. Read the repository's setup instructions and dependency manifest, then check the current branch/worktree, runtime versions, installed services/models, and existing per-user config before changing anything.
2. Reuse the repository's declared setup command and already-installed prerequisites; avoid running a second installer that clones files or replaces user configuration when the checkout is already present.
3. Preserve existing config by default. Inspect the specific relevant keys and use the application's supported config command for any needed change; never overwrite a whole config just to set up one backend.
4. Verify in increasing cost: dependency/setup command, CLI help or version, diagnostic command, then a minimal real application smoke test against the intended backend. A clean dependency install or successful diagnostic alone does not prove the application can perform its core task.
5. If the smoke test fails, distinguish install completion from operational readiness. Report the exact failing layer and observed evidence; do not claim a working setup or prescribe an unverified workaround.

Pitfall: Do not overwrite a user's existing project or per-user configuration with a fresh-init command unless the target is confirmed absent or replacement was explicitly requested; initialization may destroy customized settings or local state.

### Step 1: .env File Structure

**.env.example** (template):
```bash
# Application
NODE_ENV=development
PORT=3000
APP_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# Redis
REDIS_URL=redis://localhost:6379
REDIS_TTL=3600

# Authentication
JWT_ACCESS_SECRET=change-me-in-production-min-32-characters
JWT_REFRESH_SECRET=change-me-in-production-min-32-characters
JWT_ACCESS_EXPIRY=15m
JWT_REFRESH_EXPIRY=7d

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# External APIs
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
AWS_ACCESS_KEY_ID=AKIAXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxx
AWS_REGION=us-east-1
AWS_S3_BUCKET=myapp-uploads

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=info

# Feature Flags
ENABLE_2FA=false
ENABLE_ANALYTICS=true
```

**.env.local** (per developer):
```bash
# Developer personal settings (add to .gitignore)
DATABASE_URL=postgresql://localhost:5432/myapp_dev
LOG_LEVEL=debug
```

**.env.production**:
```bash
NODE_ENV=production
PORT=8080
APP_URL=https://myapp.com

DATABASE_URL=${DATABASE_URL}  # Injected from environment variables
REDIS_URL=${REDIS_URL}

JWT_ACCESS_SECRET=${JWT_ACCESS_SECRET}
JWT_REFRESH_SECRET=${JWT_REFRESH_SECRET}

LOG_LEVEL=warn
ENABLE_2FA=true
```

### Step 2: Type-Safe Environment Variables (TypeScript)

**config/env.ts**:
```typescript
import { z } from 'zod';
import dotenv from 'dotenv';

// Load .env file
dotenv.config();

// Define schema
const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']),
  PORT: z.coerce.number().default(3000),

  DATABASE_URL: z.string().url(),

  JWT_ACCESS_SECRET: z.string().min(32),
  JWT_REFRESH_SECRET: z.string().min(32),

  SMTP_HOST: z.string(),
  SMTP_PORT: z.coerce.number(),
  SMTP_USER: z.string().email(),
  SMTP_PASSWORD: z.string(),

  STRIPE_SECRET_KEY: z.string().startsWith('sk_'),

  LOG_LEVEL: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
});

// Validate and export
export const env = envSchema.parse(process.env);

// Usage:
// import { env } from './config/env';
// console.log(env.DATABASE_URL); // Type-safe!
```

**Error Handling**:
```typescript
try {
  const env = envSchema.parse(process.env);
} catch (error) {
  if (error instanceof z.ZodError) {
    console.error('❌ Invalid environment variables:');
    error.errors.forEach((err) => {
      console.error(`  - ${err.path.join('.')}: ${err.message}`);
    });
    process.exit(1);
  }
}
```

### Step 3: Per-Environment Config Files

**config/index.ts**:
```typescript
interface Config {
  env: string;
  port: number;
  database: {
    url: string;
    pool: { min: number; max: number };
  };
  jwt: {
    accessSecret: string;
    refreshSecret: string;
    accessExpiry: string;
    refreshExpiry: string;
  };
  features: {
    enable2FA: boolean;
    enableAnalytics: boolean;
  };
}

const config: Config = {
  env: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '3000'),

  database: {
    url: process.env.DATABASE_URL!,
    pool: {
      min: parseInt(process.env.DATABASE_POOL_MIN || '2'),
      max: parseInt(process.env.DATABASE_POOL_MAX || '10'),
    },
  },

  jwt: {
    accessSecret: process.env.JWT_ACCESS_SECRET!,
    refreshSecret: process.env.JWT_REFRESH_SECRET!,
    accessExpiry: process.env.JWT_ACCESS_EXPIRY || '15m',
    refreshExpiry: process.env.JWT_REFRESH_EXPIRY || '7d',
  },

  features: {
    enable2FA: process.env.ENABLE_2FA === 'true',
    enableAnalytics: process.env.ENABLE_ANALYTICS !== 'false',
  },
};

// Validate required fields
const requiredEnvVars = [
  'DATABASE_URL',
  'JWT_ACCESS_SECRET',
  'JWT_REFRESH_SECRET',
];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}

export default config;
```

### Step 4: Environment-Specific Configuration Files

**config/environments/development.ts**:
```typescript
export default {
  logging: {
    level: 'debug',
    prettyPrint: true,
  },
  cors: {
    origin: '*',
    credentials: true,
  },
  rateLimit: {
    enabled: false,
  },
};
```

**config/environments/production.ts**:
```typescript
export default {
  logging: {
    level: 'warn',
    prettyPrint: false,
  },
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || [],
    credentials: true,
  },
  rateLimit: {
    enabled: true,
    windowMs: 15 * 60 * 1000,
    max: 100,
  },
};
```

**config/index.ts** (unified):
```typescript
import development from './environments/development';
import production from './environments/production';

const env = process.env.NODE_ENV || 'development';

const configs = {
  development,
  production,
  test: development,
};

export const environmentConfig = configs[env];
```

### Step 5: Docker Environment Variables

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.local
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: myapp

  redis:
    image: redis:7-alpine
```

## Output format

```
project/
├── .env.example           # Template (commit)
├── .env                   # Local (gitignore)
├── .env.local             # Per developer (gitignore)
├── .env.production        # Production (gitignore or vault)
├── config/
│   ├── index.ts           # Main configuration
│   ├── env.ts             # Environment variable validation
│   └── environments/
│       ├── development.ts
│       ├── production.ts
│       └── test.ts
└── .gitignore
```

**.gitignore**:
```
.env
.env.local
.env.*.local
.env.production
```

## Constraints

### Required Rules (MUST)

1. **Provide .env.example**: List of required environment variables
2. **Validation**: Error when required environment variables are missing
3. **.gitignore**: Never commit .env files

### Prohibited (MUST NOT)

1. **Commit Secrets**: Never commit .env files
2. **Hardcoding**: Do not hardcode environment-specific settings in code

## Best practices

1. **12 Factor App**: Manage configuration via environment variables
2. **Type Safety**: Runtime validation with Zod
3. **Secrets Management**: Use AWS Secrets Manager, Vault

## References

- [dotenv](https://github.com/motdotla/dotenv)
- [Zod](https://zod.dev/)
- [12 Factor App - Config](https://12factor.net/config)

## Metadata

### Version
- **Current Version**: 1.0.0
- **Last Updated**: 2025-01-01
- **Compatible Platforms**: Claude, ChatGPT, Gemini

### Tags
`#environment` `#configuration` `#env-variables` `#dotenv` `#config-management` `#utilities`

## Examples

### Example 1: Basic usage
<!-- Add example content here -->

### Example 2: Advanced usage
<!-- Add advanced example content here -->
