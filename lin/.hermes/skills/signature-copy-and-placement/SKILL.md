---
name: signature-copy-and-placement
description: Use when placing an authorized signature on a document.
version: 1.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [signature, document, image-composite, authorized-signing]
    related_skills: [pdf-form-filling]
---

# Place a signature on a document

Use this workflow only to place the requesting user's own signature, or when the
signer has explicitly authorized this exact use. Never copy another person's
signature, imitate their handwriting, or alter a document to misrepresent who
signed it. If signer identity or authorization is unclear, stop before editing.

## When to Use

- The user asks to place their own signature on a document they are completing.
- The signer has explicitly authorized reuse of their signature on this document.

Not for: creating or transferring another person's signature, imitating a person's
handwriting, or making an unsigned document appear signed. For unsigned fields,
enter only the exact values the user supplies; do not infer titles, jurisdictions,
or extra wording. Handwriting-style references may guide layout only where the
signer is writing their own entries.

## Procedure

1. Confirm the signature is the requesting user's own, or that the signer explicitly
   authorized this exact placement. If not established, do not copy or place it.
2. Cut the source ink. `docforge_cut_signature` (plugin `docforge`) if the tool is
   in-session; otherwise `python ~/.hermes/plugins/docforge/signature.py` on the
   module directly. Pass `roi` unless auto-detect ranks a candidate well clear of
   the runner-up.
2. Accept the cut only on evidence: mode `RGBA`, alpha minimum 0, maximum reaching
   255, `ok: true`, no clip warning. Composite it over white and look at it before
   going further.
3. Measure the target field from pixels, never from a vision model's coordinates:
   ```python
   a = np.asarray(Image.open(page).convert("L")); dark = a < 128
   print([(i, int(dark[:, :cols].sum(1)[i])) for i in np.flatnonzero(dark[:, :cols].sum(1) > 200)])
   ```
   Long rows are the field's top and bottom rules, long columns the side rules.
   Border rows come back as runs wider than the field; take the pair closest below
   the label and stop. Boxes further down a form are often printed lighter — if the
   `128` threshold finds no columns at all, raise it (200) before believing the box has
   no sides, and cross-check the band against a zoom.
4. Size from the ink, not from the field. Height first, width by aspect: ~1.3x the
   interior height is the floor, and portrait ink in a landscape box is height-limited
   anyway so width stays a fraction of the field and *looks* small — a tall signature
   centred in a wide box reads right at 1.3-1.5x even though it occupies a fifth of the
   width. 60-75% of interior height fits inside the box but reads as a sticker, and
   "increase the size" means the user already hit that. The tail crossing the bottom
   rule is wanted; a tail ending on top of a label's text is too far, and so is a tail
   landing in a *boxed* field below. Loops clear the top rule; x centred, not inset left.
   The ceiling is the source dpi — cut at `scale=4` and never upscale the cut past it.
5. Harden the downscale on the **RGB only**: `UnsharpMask(1.0, 130, 2)`, then a mild
   alpha gamma `point(lambda v: int(255 * (v / 255) ** 0.7))`. The RGB sharpen keeps
   the dark edge crisp against crisp printed rules; the mild gamma thins the
   half-transparent rim, which is the source paper showing through and photographs as a
   white halo. **Do not sharpen the alpha and do not blur it.** Alpha is where the
   faint passages live; an alpha `UnsharpMask` plus any blur averages sub-pixel thin
   strokes away and the signature comes back solid with white gaps where its light
   strokes were. Alpha modulation is per-pixel noise only (see
   `references/handwriting-fields.md`).
6. Composite with `Image.alpha_composite`, on an RGBA page, then save a NEW file
   next to the input (`<name> - signed.png`). Never overwrite the input.
7. Crop and zoom the whole block. Check that the signature is in its labeled field,
   handwritten entries are legible, and no text crosses a stamp, border, or unrelated
   field. Only then report. Keep field text exactly as supplied; do not append a court,
   agency, or jurisdiction to an occupation unless the user provided it.
8. Leave ONE runnable check behind — asserts on the finished render: ink present in
   the field, no field left empty, tail clear of the text below. Blue ink is the only
   thing they can key on and the written text is blue too, so the "tail clear" assert
   goes on the GAP between text end and tail x, never the text's own row band.

## Rules

- Verify geometry by measurement, then confirm visually. Vision models return
  approximate boxes and will also contradict their own earlier verdict once the
  image changes — a measurement settles it, prose does not.
- A faint ghost already inside the field is NOT yours: prove it before touching it.
  Re-render or read the same field from the blank form/backup, and measure the hue —
  pre-printed form matter collapsed by a low-dpi crop is neutral grey
  (`B - max(R,G)` around 0, present in the blank too); pen residue is chromatic. Name
  it, then whiten the grey residue with `max(r,g,b) < 248 and blueness < 25` across the
  field interior — rules stay because they are darker, and the ink goes on afterwards.
  A brightness-only cut at `< 215` leaves the darker dots of the ghost behind. Apply
  page grain at the very end over the whole page: a whitened patch is smoother than the
  surrounding stock and reads as an edit without it. Compositing over the ghost silently
  makes you look like the cause.
- The rest of the block copies the DOCUMENT's own hand, not the font's defaults: if the
  source sheet carries a filled sample (place, date, name), read its casing, slant and
  letter size off it and reproduce those. Getting this wrong reads as two people. When
  the user supplies a separate handwriting sample, that sample outranks the sheet and is
  the spec — calibrate slant, weight, letter height and casing off it as literals before
  drawing anything (`references/handwriting-fields.md`).
- For a user's own form and own writing, a supplied sample is more faithful than a
  handwriting font. Use exact-string ink only when it is the user's own writing and
  reuse is authorized; otherwise enter the exact requested text legibly without
  imitating another person's hand. A font tuned to a sample can still look unlike it:
  inspect a crop at page scale before claiming the handwriting matches.
- Descenders may touch the bottom rule — that is real pen behaviour. Loops never
  touch the top rule or the label.
- A signature's long tail pulls its visual weight down and left, so exact centre on
  the field centre looks left-shifted. Offset the placement ~10 px the other way and
  check the tail clears any text already written in the field below.
- Set the top from the ink body just under the top rule, never from a vertical centring
  of the whole cut: the tail is part of the height, so centring the cut lifts the body
  over the rule.
- Save the page RGB if it had no alpha; keep the cut RGBA. Never flatten the cut
  to white.
- Report the numbers: field bounds, placement box, final size. "Looks good" alone
  is unverifiable.

## Pitfalls

- Two corrections on the same axis mean the mechanism is wrong, not the parameter.
  Slant/weight/size nudges after "doesn't look hand-written" are the third and fourth
  attempt at a font that will never pass — switch mechanism (trace the real ink, cut a
  real signature) instead of tuning again. Each tuning round costs a render and a review
  and moves nothing the user can see.
- Long multi-line shell heredocs can be refused by policy. Write the probe to a
  `.py` file and run the file instead of fighting quoting.
- `docforge_cut_signature` can come back as a handler contract error
  ("unsupported result type") while still having written the PNG and its JSON. `ls`
  the `out_dir` before retrying, and read the JSON for the roi it actually used.
- `PIL.Image.LANCZOS` is gone in newer Pillow; use
  `getattr(Image, "Resampling", Image).LANCZOS`.
- `random.Random` has `gauss(mu, sigma)` and `uniform`, **not** `normal`; numpy's `normal`
  takes a shape, `Random.gauss` takes one scalar per call. Mixing them up raises
  `AttributeError` mid-render after the compositing work is already spent.
- The interpreter that has `PIL`/`numpy`/`reportlab` is the environment venv under
  `~/.hermes/installs/<id>/environments/<id>/venv/bin/python`. Find it with
  `ls */lib/python3.*/site-packages/reportlab` rather than assuming a path.

Extraction mechanics, thresholds and the defects that cost time are in
`references/extraction-pitfalls.md`. Filling the rest of the block in the same hand —
font, per-glyph jitter, ink texture, the assert set — is in
`references/handwriting-fields.md`.
