# Adding Skill Sync to a Paperclip Adapter

Pattern for implementing `listSkills` / `syncSkills` on a Paperclip adapter, following the existing ephemeral or persistent modes.

## Decision: Ephemeral vs Persistent

| Mode | When to use | Example adapters |
|------|-------------|------------------|
| `ephemeral` | Skills travel with the wake payload / prompt bundle, not persisted on disk by the adapter itself | `claude_local`, `openclaw_gateway` |
| `persistent` | Adapter manages skills as symlinks or files in a local directory (e.g. `~/.claude/skills/`) | `opencode_local`, `cursor_local`, `gemini_local`, `pi_local` |

## Ephemeral Mode (for remote/gateway adapters)

Ephemeral adapters report skills as `configured`/`available` without managing files — the skills are materialized at runtime via the wake payload or prompt bundle.

### Implementation

Create `src/server/skills.ts`:

```typescript
import { fileURLToPath } from "node:url";
import path from "node:path";
import type {
  AdapterSkillContext,
  AdapterSkillEntry,
  AdapterSkillSnapshot,
} from "@paperclipai/adapter-utils";
import {
  readPaperclipRuntimeSkillEntries,
  resolvePaperclipDesiredSkillNames,
} from "@paperclipai/adapter-utils/server-utils";

const __moduleDir = path.dirname(fileURLToPath(import.meta.url));

async function buildXxxSkillSnapshot(
  config: Record<string, unknown>,
): Promise<AdapterSkillSnapshot> {
  const availableEntries = await readPaperclipRuntimeSkillEntries(config, __moduleDir);
  const availableByKey = new Map(availableEntries.map((entry) => [entry.key, entry]));
  const desiredSkills = resolvePaperclipDesiredSkillNames(config, availableEntries);
  const desiredSet = new Set(desiredSkills);
  const entries: AdapterSkillEntry[] = availableEntries.map((entry) => ({
    key: entry.key,
    runtimeName: entry.runtimeName,
    desired: desiredSet.has(entry.key),
    managed: true,
    state: desiredSet.has(entry.key) ? "configured" : "available",
    origin: entry.required ? "paperclip_required" : "company_managed",
    originLabel: entry.required ? "Required by Paperclip" : "Managed by Paperclip",
    readOnly: false,
    sourcePath: entry.source,
    targetPath: null,
    detail: desiredSet.has(entry.key)
      ? "Will be included in the [wake payload / prompt bundle] on the next run."
      : null,
    required: Boolean(entry.required),
    requiredReason: entry.requiredReason ?? null,
  }));
  const warnings: string[] = [];

  for (const desiredSkill of desiredSkills) {
    if (availableByKey.has(desiredSkill)) continue;
    warnings.push(`Desired skill "${desiredSkill}" is not available from the Paperclip skills directory.`);
    entries.push({
      key: desiredSkill,
      runtimeName: null,
      desired: true,
      managed: true,
      state: "missing",
      origin: "external_unknown",
      originLabel: "External or unavailable",
      readOnly: false,
      sourcePath: undefined,
      targetPath: undefined,
      detail: "Paperclip cannot find this skill in the local runtime skills directory.",
    });
  }

  entries.sort((left, right) => left.key.localeCompare(right.key));

  return {
    adapterType: "<adapter_type>",
    supported: true,
    mode: "ephemeral",
    desiredSkills,
    entries,
    warnings,
  };
}

export async function listXxxSkills(ctx: AdapterSkillContext): Promise<AdapterSkillSnapshot> {
  return buildXxxSkillSnapshot(ctx.config);
}

export async function syncXxxSkills(
  ctx: AdapterSkillContext,
  _desiredSkills: string[],
): Promise<AdapterSkillSnapshot> {
  return buildXxxSkillSnapshot(ctx.config);
}
```

### Registration

In `src/server/index.ts`:

```typescript
export { listXxxSkills, syncXxxSkills } from "./skills.js";
```

In `server/src/adapters/registry.ts`:

```typescript
import { listXxxSkills, syncXxxSkills } from "@paperclipai/adapter-<name>/server";

// On the adapter object:
const xxxAdapter: ServerAdapterModule = {
  // ...existing fields...
  listSkills: listXxxSkills,
  syncSkills: syncXxxSkills,
};
```

## Persistent Mode (for local adapters)

Persistent adapters create symlinks into a local skills directory (e.g. `~/.claude/skills/`). They use `buildPersistentSkillSnapshot` from `@paperclipai/adapter-utils/server-utils`.

See existing implementations:
- `packages/adapters/opencode-local/src/server/skills.ts` — uses `~/.claude/skills/`
- `packages/adapters/pi-local/src/server/skills.ts` — uses `~/.pi/agent/skills/`

The key difference from ephemeral mode is:
- `buildPersistentSkillSnapshot` checks actual symlinks on disk via `readInstalledSkillTargets`
- `syncXxxSkills` runs `ensurePaperclipSkillSymlink` to create/remove symlinks

## Verification

1. `pnpm --filter @paperclipai/adapter-<name> typecheck` should pass
2. `pnpm --filter @paperclipai/adapter-<name> build` should succeed
3. The server's `GET /api/adapters` response should show `capabilities.supportsSkills: true` for the adapter
4. The agent detail page in the UI should show a "Skills" tab
