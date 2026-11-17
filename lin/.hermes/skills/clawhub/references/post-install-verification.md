# ClawHub Post-Install Verification

Use the page at `https://clawhub.ai/<user>/<slug>` as the source of truth for requirements:
- `requires.bins` lists exact preinstall system commands.
- `requires.env` / `optionalEnv` lists env vars to verify or set.
- Post-install section contains first-use setup steps and runtime notes.
- Actions table maps user prompts to executable actions/interfaces.

## Verified-Source Pattern
1. Read landing page with web_extract before install.
2. Install with `clawhub install <slug>` or `openclaw skills install <slug>`.
3. Read local `SKILL.md` in the installed skill dir.
4. Compare page summary against local SKILL.md for install scripts, paths, and required binaries.
5. Run the skill's preflight/check_deps script when present before calling install/postinstall scripts.

## Decision Rule for Downgrades/Warnings
- If registry metadata + local SKILL.md agree on installed version, proceed.
- If page says pinned release tag or prior requirement but installed version differs, fetch release notes or repo tag before running privileged setup steps.
