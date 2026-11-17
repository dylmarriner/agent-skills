# TypeScript and Next.js Development

Use for TypeScript, JavaScript, React, Next.js, Node, Prisma, Tailwind, and full-stack web work.

Rules:
- Prefer strict types.
- Do not use any unless justified.
- Do not silence TypeScript errors.
- Do not create fake API contracts.
- Check existing route/component/data-fetching patterns.
- Keep components small.
- Separate UI, validation, data access, and business logic.
- Use existing styling conventions.

Validation:
- npm run typecheck
- npm run lint
- npm test
- npm run build only after smaller checks pass

For Prisma/database work:
- inspect schema first
- check relations before query changes
- avoid raw SQL unless necessary
- never add null placeholders to satisfy types
