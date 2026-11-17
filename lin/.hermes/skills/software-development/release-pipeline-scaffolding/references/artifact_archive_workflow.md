# Consent-preserving artifact archive workflow

When your new CLI emitter produces different artifacts than what's currently committed, the wrong move is to overwrite. The right move is to archive first.

## Detection: are there committed artifacts?

```bash
ls artifacts/                          # see what's there
git ls-files artifacts/                # see what's tracked
```

If both return non-empty, the artifacts are committed. Don't overwrite them.

## Archive before regenerate

```bash
# 1. Date stamp — when this happened, not when the file was last modified
DATE=$(date +%Y-%m-%d)
mkdir -p artifacts/archive-$DATE/

# 2. Move (not copy) the existing artifacts into the archive
for f in artifacts/canon_digest.txt \
         artifacts/determinism_proof.txt \
         artifacts/verification_100kyr.json \
         artifacts/verification_100kyr.bincode \
         artifacts/verification_1myr.json \
         artifacts/verification_1myr.bincode \
         artifacts/verification_10myr.json \
         artifacts/verification_10myr.bincode \
         artifacts/emitter_meta.json \
         artifacts/README.md; do
  if [ -f "$f" ] && [ ! -f "artifacts/archive-$DATE/$(basename $f)" ]; then
    git mv "$f" "artifacts/archive-$DATE/"
  fi
done

# 3. NOW regenerate
./target/release/mk verify --out artifacts/

# 4. Verify the new files exist and look right
ls -la artifacts/
```

## Document the archive

In `docs/VERIFICATION_REPORTS.md` (or equivalent), add a note like:

```markdown
A historical snapshot of pre-`mk_cli` artifacts (generated 2026-04-02 by the
standalone `mk_phase7_artifacts` binary using a different canon-derivation
path) is preserved at `artifacts/archive-2026-04-02/`. **Do not delete it** —
it is the only record of the prior canonical digest (`93175592fc0607ba...`).
```

Without this note, a future session will think the archive is junk and delete it.

## Why this matters — a real consequence

In one real project, the `canon_digest.txt` value changed between emitter runs because the canon-derivation path was refactored. The old value (`93175592fc0607ba...`) had been the *immutable* digest in the project README. The new value (`81db77278976655e...`) was correct under the new path. If the old file had been overwritten without archival:

- No record that the canon-digest had ever had a different value
- No way to verify a future canon-digest change was intentional vs. accidental
- The `artifacts/canon_digest.txt` would be the only thing in git, with no history

The archive subdir is the audit trail. It costs almost nothing to maintain and prevents irreversible information loss.

## When NOT to archive

- If the artifacts are *not* committed (you've added `artifacts/` to `.gitignore`), there's nothing to archive — just regenerate
- If the new emitter produces byte-identical output to the committed artifacts, no archive needed; the file is unchanged
- If the user explicitly says "overwrite is fine," do that
