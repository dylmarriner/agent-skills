# Performer alias handling notes (2026-07-12)

Observed in session:
- `TheDanDangler` should be treated as a performer alias/model name when counting files.

Takeaway:
- Performer counting must support alias maps and concatenated names without spaces.
- Unmatched-file review should not stop at exact spaced-name matching; check for alias-style filenames and common concatenations.

Implementation hint:
- Normalize filenames aggressively (case-folding, leetspeak folding, punctuation stripping).
- Allow a small alias map for known performer aliases in the current library.
- Re-run unmatched buckets after adding a new alias so counts stay consistent.
