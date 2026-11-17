---
name: update-docs
description: Update the Maer'Ken indexed docs (docs/architecture.md, docs/implementation.md, docs/patterns.md, docs/decisions.md, docs/changelog.md) after finishing a feature or bugfix in the Maer-Ken project. Use after every edit that adds/renames a module, changes architecture, or fixes a bug — not before.
---

# Update Docs (Maer'Ken)

1. Run `git diff HEAD~1 --name-only` to identify changed files.
2. Re-scan only the changed files and their direct neighbors (same package/directory).
3. Update the relevant doc files using targeted edits (do not rewrite unaffected sections):
   - New module/package → update `docs/architecture.md`, `docs/implementation.md`
   - New class/function/endpoint → update `docs/implementation.md`
   - Renamed files/folders → update `docs/architecture.md`, `docs/patterns.md`
   - New dependency → update `docs/architecture.md`
   - New naming/code pattern → update `docs/patterns.md`
4. Ask: "Did this change involve making or reversing an architectural decision?"
   - If yes → append an ADR entry to `docs/decisions.md`
   - If no → skip
5. Append a dated changelog entry to `docs/changelog.md`:
   ```
   ## YYYY-MM-DD — [brief description]
   - What changed
   - Which modules were affected
   ```
