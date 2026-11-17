---
name: publish-helper
description: "Bump version, append changelog, and run the right clawhub publish command in one pass. Use this skill when the user wants to publish or release an OpenClaw skill or plugin to ClawHub. Signals include 'publish this skill,' 'bump and publish,' 'ship v[X] of [skill],' 'release [skill] as patch,' 'release [skill] as minor,' 'release [skill] as major,' or 'time to release [project].' Detects skill vs. plugin from folder contents, validates the SKILL.md frontmatter, bumps version in SKILL.md (and plugin.json/openclaw.plugin.json/package.json if a plugin), appends a dated changelog entry, then prints the exact clawhub command with all flags filled in. Optionally executes the command on user confirmation. Do NOT trigger on requests to install or update someone else's skill ('install X' is not a publish action), on dry-run inspections without a bump intent, or on first-time publishing before the user has run clawhub login."
license: "MIT"
metadata:
  permissions:
    files:
      read: ["<target skill or plugin folder>"]
      write: ["<target SKILL.md or plugin manifests>", "<target CHANGELOG.md if exists>"]
    shell: ["clawhub whoami, clawhub publish, clawhub package publish (only when user confirms)"]
    network: false
---

# Publish Helper

The Cron Sentinel and Client Services Co-Pilot publish flows both ended in the same dance: edit the version in SKILL.md, add an entry to CHANGELOG, then carefully type a clawhub command with five flags. Publish Helper collapses that into a confirm-and-run.

## What this skill does

Given a target path (a skill folder or a plugin folder) and a bump type, walk the publish flow:

1. **Detect target type.** Does the folder contain a SKILL.md (skill mode), or a `.claude-plugin/plugin.json` plus an `openclaw.plugin.json` (plugin mode)? Tell the user which mode was detected.
2. **Auth precheck.** Run `clawhub whoami`. If it errors, stop and tell the user to run `clawhub login` first.
3. **Validate frontmatter.** Spot-check the obvious: `name` present and kebab-case, current version is valid semver, description is non-empty. For deeper checks, recommend the SKILL.md Linter.
4. **Bump the version.** Patch, minor, or major. In skill mode, update SKILL.md. In plugin mode, update SKILL.md (for any contained skills if their versions are tied), `.claude-plugin/plugin.json`, `openclaw.plugin.json`, and `package.json`. Cross-check that the resulting versions match.
5. **Update CHANGELOG.md.** Append a new section with the new version, today's UTC date, and the changelog text the user provided. If no CHANGELOG exists, create one with a Keep-a-Changelog header.
6. **Compose the publish command.** See `references/clawhub-commands.md` for the exact shapes. Skill mode uses `clawhub publish`. Plugin mode uses `clawhub package publish --family bundle-plugin --bundle-format claude` (the working recipe for Claude-style bundle plugins).
7. **Confirm before running.** Print the command and ask the user to confirm.
8. **On confirmation, execute via shell.** Capture stdout and stderr. Report success with the version id from the output, or failure with the error message and a one-line suggestion.

## How to run it

When invoked:

1. Ask for the target path if not given.
2. Detect skill vs. plugin from the folder contents. If ambiguous, ask.
3. Ask for bump type (patch / minor / major) and changelog text if not provided.
4. Run the steps above in order. Show the user each change as you make it: the new version number, the appended changelog block, the composed command.
5. After execution, suggest the next action: tag the GitHub release, log the publish in the user's tracker, or run Skill Doctor to confirm nothing else regressed.

## Skill vs. plugin matrix

| Detection                                                                    | Command                  | Required flags                                                                |
| ---------------------------------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------- |
| Folder contains `SKILL.md` (single skill)                                    | `clawhub publish`        | `--slug`, `--name`, `--version`, `--changelog`                                |
| Folder contains `openclaw.plugin.json` plus `.claude-plugin/plugin.json`     | `clawhub package publish` | `--family bundle-plugin`, `--bundle-format claude`, `--name`, `--display-name`, `--version`, `--changelog` |

Full flag reference and edge cases live in `references/clawhub-commands.md`.

## Safety rules

- **Never publish without explicit confirmation.** Print the command, ask, wait.
- **Never bump major without confirmation.** Major bumps are breaking. Require an extra "yes, major."
- **Refuse to publish if not logged in.** Detect via `clawhub whoami`. If it errors, stop.
- **Never invent a changelog entry.** If the user did not supply text, ask. Do not guess at what changed.

## Edge cases

- **No CHANGELOG.md.** Create one with a Keep-a-Changelog header and the new entry.
- **Plugin version mismatch across manifests.** If `openclaw.plugin.json` and `.claude-plugin/plugin.json` disagree before bumping, flag it and ask which is authoritative.
- **Same version as currently published.** ClawHub rejects re-publishes of the same version. If the user tries to publish without bumping, warn and offer to bump.

## When NOT to use

- Installing or updating someone else's skill: "install X" is not a publish action.
- Dry-run inspections where the user wants to see what would change without bumping. Use a diff-style review instead.
- First-time publishing if the user has not yet authenticated. Prompt to run `clawhub login` first.
