# clawhub publish command matrix

Canonical reference for how Publish Helper composes `clawhub` commands.
Update this file when the CLI changes.

## Skill publish

For a single skill (a folder containing SKILL.md):

```
clawhub publish <path> \
  --slug <kebab-name> \
  --name "<display name>" \
  --version <new semver> \
  --changelog "<text>"
```

Required flags: `--slug`, `--name`, `--version`, `--changelog`.
Optional: `--tags <csv>` (defaults to `latest`).

## Plugin publish (bundle plugin)

For a plugin folder containing `.claude-plugin/plugin.json`,
`openclaw.plugin.json`, and `package.json`:

```
clawhub package publish <path> \
  --family bundle-plugin \
  --bundle-format claude \
  --name <kebab-name> \
  --display-name "<display name>" \
  --version <new semver> \
  --changelog "<text>"
```

Required flags: `--family`, `--bundle-format`, `--name`, `--display-name`,
`--version`, `--changelog`.

## Plugin publish (native code plugin)

For a plugin with a runtime module and a GitHub-hosted source. Heavier
flow; only use when the plugin genuinely runs code in-process.

```
clawhub package publish <path> \
  --family code-plugin \
  --name <kebab-name> \
  --display-name "<display name>" \
  --version <new semver> \
  --changelog "<text>" \
  --source-repo <owner/repo> \
  --source-commit <sha>
```

Required additional flags: `--source-repo`, `--source-commit`.

## Auth precheck

Before any publish, Publish Helper runs:

```
clawhub whoami
```

If the exit code is non-zero or stdout indicates "not logged in," abort
and tell the user to run:

```
clawhub login
```

## Environment overrides

Useful when publishing from CI or a non-standard machine:

- `CLAWHUB_REGISTRY`: alternate registry URL
- `CLAWHUB_CONFIG_PATH`: alternate token store path
- `CLAWHUB_WORKDIR`: working directory override
- `CLAWHUB_DISABLE_TELEMETRY=1`: disable telemetry on sync
