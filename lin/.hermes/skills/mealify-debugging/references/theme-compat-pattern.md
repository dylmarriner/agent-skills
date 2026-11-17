# DesignSystem.js Flat Compat Layer Pattern

A technique for migrating React Native screens from flat property references (`Theme.colors.primary`) to a new nested design token system (`Theme.colors.accent.primary`) **without rewriting every screen's StyleSheet**.

## Problem

Screens reference theme properties as flat, pre-existing names:
```js
import { Theme } from '../styles/DesignSystem';
// ...
color: Theme.colors.primary,
backgroundColor: Theme.colors.background,
color: Theme.colors.error,
color: Theme.colors.text.dimmed,
```

But the canonical design tokens are nested under `sys.*`, `accent.*`, `sem.*`:
```js
{
  sys: { bg, text, border, ... },
  accent: { primary, teal, warm, violet, ... },
  sem: { success, warning, danger, ... },
  ttl: { fresh, soon, urgent },
  stock: { full, low, out },
  budget: { safe, tight, over },
}
```

Rewriting every screen is high risk and tedious for a large codebase.

## Solution: Flat Compat Layer

Create a `DesignSystem.js` that wraps the canonical tokens with all the flat aliases screens actually use:

```js
import { kitchenDaylight, midnightPantryLab, spacing, radius, motion } from '@mealify/ui';

function flatMap(colors) {
  return {
    // flat aliases screens already reference
    primary: colors.accent.primary,
    primarySoft: colors.accent.primarySoft,
    background: colors.sys.bg,
    surface: colors.sys.surface,
    error: colors.sem.danger,
    success: colors.sem.success,
    warning: colors.sem.warning,
    text: colors.sys.text,
    textPrimary: colors.sys.text,
    textSecondary: colors.sys.textMuted,
    textDimmed: colors.sys.textSubtle,
    border: colors.sys.border,
    // ...map every property screens use
  };
}

// Spread both the nested object AND the flat aliases
// so screens can use either pattern
export const Theme = {
  name: 'midnight-pantry-lab',
  colors: {
    ...midnightPantryLab,        // nested: sys, accent, sem...
    ...flatMap(midnightPantryLab), // flat: primary, background, error...
  },
  spacing,
  radius,
  motion,
  elevation: { /* ... */ },
};
```

## Why it works

1. `Theme.colors.primary` resolves to `midnightPantryLab.accent.primary` = `#27E0A3`
2. `Theme.colors.sys.bg` still works for new components using nested tokens
3. Zero changes to existing StyleSheets
4. Light/dark switching works through the same compat layer

## Migration path

1. **Phase 1 (compat)** — Add the flat compat layer. All existing screens render correctly.
2. **Phase 2 (new components)** — Use nested tokens directly: `Theme.colors.accent.primary`
3. **Phase 3 (gradual refactor)** — When you touch a screen, migrate its StyleSheet to nested tokens
4. **Phase 4 (remove compat)** — Once all screens use nested tokens, delete the `flatMap()` aliases

## When NOT to use this pattern

- If the codebase is small (under 5 screens), just rewrite them directly
- If the screens already use a theme hook/context with dynamic switching, propagate tokens through that instead
- If the token structure is flat and doesn't need nesting, this adds unnecessary indirection

## Key insight

The compat layer buys you time. It lets you deploy your new design system immediately while refactoring screens at your own pace. Each screen you touch becomes a native user of nested tokens without a big-bang rewrite.
