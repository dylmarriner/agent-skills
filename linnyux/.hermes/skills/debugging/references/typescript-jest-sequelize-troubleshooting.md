# TypeScript + Jest + Sequelize Troubleshooting Reference

Common patterns when debugging a mixed TypeScript/JavaScript monorepo where legacy Sequelize code coexists with a Prisma-based backend.

## Jest can't parse TypeScript files

**Error:** `SyntaxError: Missing semicolon. (11:28)` pointing to TS type annotations (e.g. `: Promise<void>` or `: string`) when Jest runs `.js` test files that `require()` TypeScript source files.

**Root cause:** Jest uses Babel by default, which doesn't understand TypeScript. When a `.js` test does `require('../src/index')` (a `.ts` file), Jest's default babel transform tries to parse it as JavaScript and fails on type annotations.

**Fix:**
```
npm install --save-dev ts-jest @types/jest
```

Create or update `jest.config.js`:
```js
/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'node',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: 'tsconfig.json',
      diagnostics: false,  // Suppress TS errors in test context
    }],
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  testMatch: ['**/tests/**/*.test.[jt]s?(x)'],
};
```

**Pitfalls:**
- With ts-jest, `require('../src/config/module')` may load the `.ts` file instead of a sibling `.js` file. If the TS file uses `export default` but the test expects `module.exports`, the returned object may be `{ default: ... }` instead of flat properties. Use `const config = require('..'); const value = config.default || config;` as a safe accessor.
- The `isolatedModules` config option belongs in `tsconfig.json`, not in ts-jest options. If using ts-jest v29+, set `"isolatedModules": true` in tsconfig.
- `diagnostics: false` disables type checking during test runs — acceptable for test speed but don't rely on it to catch real errors during development.

## Sequelize model init: "Class constructor model cannot be invoked without 'new'"

**Error:** `TypeError: Class constructor model cannot be invoked without 'new'` when initializing models from `src/models/index.ts`.

**Root cause:** Sequelize model files have two different export patterns:
1. **Factory function pattern** — `module.exports = (sequelize, DataTypes) => { class extends Model { ... }; return ...; }` — must be *called* as `mod(sequelize, DataTypes)`.
2. **`sequelize.define()` pattern** — `const Model = sequelize.define('Model', { ... }); module.exports = Model;` — exports a class constructor directly. `typeof Model === 'function'` is true, but calling it without `new` throws.

Both pass the `typeof mod === 'function'` check, but only pattern 1 can be invoked directly.

**Fix:** Use a safe init helper:
```ts
function initModel(mod: any, sequelize: Sequelize, DataTypes: any) {
  if (typeof mod !== 'function') return mod;
  // Models from sequelize.define() are class constructors — use as-is
  if (/^class /.test(mod.prototype?.constructor?.toString?.() || '')) {
    return mod;
  }
  // Factory functions need to be called
  return mod(sequelize, DataTypes);
}
```

## Duplicate Sequelize association aliases

**Error:** `SequelizeAssociationError: You have used the alias X in two separate associations. Aliased associations must have unique aliases.`

**Root cause:** Multiple model files use the same `as:` value for `belongsTo` associations to the same target model. Common in large codebases where every model that belongs to an `InventoryItem` naively uses `as: 'inventoryItem'`.

**Fix:** Give each model a unique alias:
```js
// Before (conflict)
Sku.belongsTo(models.InventoryItem, { foreignKey: 'inventoryItemId', as: 'inventoryItem' });
StockLot.belongsTo(models.InventoryItem, { foreignKey: 'inventoryItemId', as: 'inventoryItem' });

// After
Sku.belongsTo(models.InventoryItem, { foreignKey: 'inventoryItemId', as: 'skuInventoryItem' });
StockLot.belongsTo(models.InventoryItem, { foreignKey: 'inventoryItemId', as: 'stockLotInventoryItem' });
```

**Quick scan command:**
```bash
grep -rn "as: 'inventoryItem'" src/models/  # Check for duplicate aliases
```

## Missing Sequelize package in a project that uses Prisma

**Error:** `Cannot find module 'sequelize'`

**Root cause:** The project migrated from Sequelize to Prisma, but legacy model files, services, or tests still import `sequelize`. The package was removed from dependencies.

**Fix:** Install sequelize as a dev dependency (or regular dependency if legacy code is in production paths):
```
npm install sequelize pg pg-hstore
```

Create a stub `config/database.js` that connects using DATABASE_URL:
```js
const { Sequelize } = require('sequelize');
require('dotenv').config();
const databaseUrl = process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/db';
const sequelize = new Sequelize(databaseUrl, {
  dialect: 'postgres',
  logging: process.env.NODE_ENV === 'test' ? false : undefined,
  define: { timestamps: true, underscored: false, freezeTableName: true },
});
module.exports = { sequelize, Sequelize };
```

## Pre-existing test issues vs infrastructure issues

When debugging test failures in a migrated project, distinguish:
- **Infrastructure issues** — missing deps, wrong Jest config, missing DB config, TS parse errors. These are fixable.
- **Pre-existing test issues** — tests that rely on old Sequelize sync (`sequelize.sync({ force: true })` conflicts with Prisma-managed tables), mock setups that reference models not in the current export schema, or missing legacy packages like `express-validator`. These are deeper code issues, not debugging problems.

## Model association runner with aliases

If your models object has aliases (e.g. `Sku: SKU, PriceSnapshot: PriceHistory`), running `associate()` for every key causes duplicate association registration:
```ts
// Wrong: calls SKU.associate() twice (once for 'SKU' key, once for 'Sku' key)
Object.keys(models).forEach(name => models[name].associate?.(models));

// Right: deduplicate by model instance
const seen = new Set();
Object.keys(models).forEach(name => {
  const model = models[name];
  if (seen.has(model)) return;
  seen.add(model);
  model.associate?.(models);
});
```
