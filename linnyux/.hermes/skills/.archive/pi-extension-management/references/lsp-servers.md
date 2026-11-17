# LSP servers in pi

Two npm packages register the same tool names, so only one can load at a time:

- `@narumitw/pi-lsp` (0.49.x, maintained) — tools `lsp_diagnostics`, `lsp_fix`. Keep this one.
- `pi-lsp` (bare name, 0.1.x, unmaintained) — `lsp_diagnostics` plus `lsp_definition` / `lsp_hover` /
  `lsp_references` / `lsp_symbols`. Whenever the scoped package is present this one fails to load entirely.

Check which tools a candidate adds before installing a second LSP package — the overlap kills it.

## Config

Canonical paths, resolved in order: `<workspace>/.pi/pi-lsp.json` (trusted project only), then
`~/.pi/agent/pi-lsp.json`, then the built-in catalog. Legacy `~/.pi/agent/lsp.json` and `.pi/lsp.json`
are still read with a warning and are never auto-migrated.

```json
{
  "timeout": 30000,
  "servers": {
    "<name>": {
      "command": ["binary", "arg"],
      "extensions": [".py", ".pyi"],
      "env": {},
      "initialization": { "settings": {} },
      "skipDirectories": [],
      "pullDiagnosticsGraceMs": 5000
    }
  }
}
```

- `command` is an **argv array**, never a string.
- `extensions` is **required** — it is what routes a file to a server. Omit it and the server is configured
  but never matched.
- A flat server map (no `servers` key) also parses; `servers` is needed only for global options.
- **Any custom config replaces the entire built-in catalog.** Servers you do not list are gone, not merged.
- The built-in catalog never downloads anything; each entry needs its binary on PATH
  (`biome lsp-proxy`, `ty server`, `ruff server`, `rust-analyzer`, `gopls`, `clangd`, `jdtls`, ...). Check
  `command -v` for every server you configure, or the config is decorative.

## Probing a server standalone (no pi, no model)

Run `scripts/lsp_check.py`. Two traps make a working server look broken:

- **Push-only servers wait on the client.** `biome lsp-proxy` sends `workspace/configuration` and
  `client/registerCapability` on open and blocks until answered. A probe that never replies gets an
  initialized server and zero diagnostics, forever. Reply to every message carrying both `method` and `id`
  (`workspace/configuration` -> `[null]`).
- **`languageId` must be the real one** — `"typescript"`, not `"ts"`. Servers may reject the file silently
  and just never publish.
- Not a failure: `rust-analyzer` stays quiet without a Cargo project, `gopls` needs a `go.mod`,
  `asm-lsp` is quiet on a bare file. Assert diagnostics only for servers known to push on open
  (pylsp/pyflakes, clangd, biome).

## TypeScript on TS 7

`typescript-language-server` cannot initialize when the workspace has TypeScript 7.x: TS 7 is the native
port and ships no `lib/tsserver.js`, so the server exits with "Could not find a valid TypeScript
installation". Use `biome lsp-proxy` for `.ts/.tsx/.js/.jsx/.mjs/.cjs/.json/.jsonc/.css` instead. Biome
parses independently of `tsc` — it reports syntax and lint diagnostics, not type errors.
