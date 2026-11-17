# Harness matrix — commands, manifests, output reading

## Sources and where they land

| Harness | Register source | Install step | Cache / effect |
|---|---|---|---|
| Claude Code | `claude plugin marketplace add <path\|github\|git-url>` | `claude plugin install <p>@<m> -s user -y` | snapshots plugin into `~/.claude/plugins/cache/`; skills/agents/hooks load from the snapshot |
| Codex CLI | `codex plugin marketplace add <path\|git>` | `codex plugin add <p>@<m>` | copies plugin into `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`; marketplace root stays where you added it |
| Hermes | `hermes config set skills.external_dirs '[…]'` | none — scanned live | pack dir stays authoritative; Hermes treats external skills as read-only |

Local-directory marketplaces: Claude Code declares them as `Source: Directory (<path>)`;
Codex records the path as the marketplace ROOT (no copy). Both accept the same
`.claude-plugin/marketplace.json` at the repo root, so one file wires a repo for
both harnesses.

## Manifest schemas

### `.claude-plugin/marketplace.json` (repo root; read by Claude Code AND Codex)

```json
{
  "name": "<marketplace>",
  "owner": { "name": "<owner>", "url": "https://github.com/<owner>" },
  "metadata": { "description": "<one line>" },
  "plugins": [
    {
      "name": "<plugin>",
      "source": "./plugins/<plugin>",
      "description": "<one line>",
      "version": "1.2.3",
      "author": { "name": "<owner>" },
      "license": "MIT",
      "homepage": "https://…",
      "repository": "https://…",
      "keywords": ["…"],
      "category": "development"
    }
  ]
}
```

`source` is relative to the marketplace root, or `"./"` when the plugin IS the
repo. Use the relative form whenever the plugin lives in a subdirectory — it
keeps the repo clean and avoids a second shim directory.

### `.claude-plugin/plugin.json` (the plugin itself)

```json
{
  "name": "<plugin>",
  "version": "1.2.3",
  "description": "<one line>",
  "commands": ["./commands/"],
  "skills": ["./skills/"],
  "mcpServers": "./.mcp.json"
}
```

Rules that break install/load when violated: `commands`/`skills` are arrays;
no `agents` key (root `agents/` is auto-discovered); no `hooks` key pointing at
the standard root `hooks/hooks.json`.

### `.agents/plugins/marketplace.json` (Codex-native marketplace view)

```json
{
  "name": "<marketplace>",
  "interface": { "displayName": "<Display>" },
  "plugins": [
    {
      "name": "<plugin>",
      "version": "1.2.3",
      "source": { "source": "local", "path": "./" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

Only needed when you want Codex-specific interface metadata; a
`.claude-plugin/marketplace.json` alone already installs.

### `.codex-plugin/plugin.json` (Codex-native plugin metadata)

```json
{
  "name": "<plugin>",
  "version": "1.2.3",
  "description": "<one line>",
  "skills": "./skills/",
  "mcpServers": "./.mcp.json",
  "interface": { "displayName": "<Display>", "category": "Coding" }
}
```

Presence of this file is what makes Codex register a dedicated skill root for a
plugin's `skills/` dir in `codex debug prompt-input`. Without Codex-native
metadata the plugin still installs and its root skills dir is usually still
discovered — verify rather than assume either way.

## Reading harness output

- `claude plugin list` — `✔ enabled` / `✘ failed to load` + `Error:` line per
  plugin. The error text is the actual diagnosis; the install line is not.
- `claude plugin details <p>@<m>` — component inventory (Skills/Agents/Hooks/MCP
  counts), `Projected token cost → Always-on: ~N tok`, plus per-component
  on-invoke cost. Use it as the cost gate.
- `claude plugin validate <dir>` — manifest, command, and frontmatter validation.
  Warnings (missing frontmatter) do not block; errors do.
- `codex plugin list` — `installed, enabled` + resolved SOURCE path per plugin.
- `codex debug prompt-input "hi"` — full model-visible prompt as JSON. The
  `<skills_instructions>` block contains a skill-roots table (`r0`..`rN`) and an
  enumerated skill list with `(file: rN/path/SKILL.md)` entries. Roots present =
  wired; enumeration is capped at tens of skills, so absence from the list is not
  proof of failure.
- Hermes `hermes skills list` / `hermes skills inspect <name>` resolve against
  REGISTRIES as well as local+packs, so they can show a same-named remote skill.
  For a true path check use `get_all_skills_dirs()` + `_find_skill()` from the
  Hermes venv (see SKILL.md Verification).

## Adding a fourth harness

The pattern is the same three questions — where does it READ sources from, what
manifest does it demand there, and what output proves a load:

1. Find the harness's source/plugin command surface (`<cli> --help`, plus
   `<cli> plugin --help` / `<cli> skills --help`).
2. Point it at the same repo, ideally the same `.claude-plugin/marketplace.json`.
3. Verify from an introspection command (prompt/config dump) or a config read,
   never from the install message.

Per-harness operator detail lives in the sibling skills `antigravity-cli`,
`pi-extension-management`, `claude-code-troubleshooting`.
