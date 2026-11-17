# Hand-writing fields on the user's own document

Use this only for the user's own entries or writing the signer explicitly authorized.
Do not reproduce another person's handwriting to make entries appear to be theirs.
A signature alone in an otherwise empty witness block is a layout concern, not a reason
to fabricate handwriting; leave fields blank or type the exact user-provided values.

## Reuse, do not invent

If the project already has a filler for the same form, it already settled the font,
the ink colour and the field text. Steal all three — a `fill_witness.py` with a
`FONT`, a `BLUE` tuple and a `FIELDS` list is that contract. Matching values across
two outputs (a PDF and a PNG of the same page) is the point; a fresh choice per file
shows up as two different pens on two pages of one document.

- Handwriting font sits in `fonts/` beside the form; Patrick Hand is what this user's
  documents use.
- Ink is the tuple from the existing filler (e.g. `(15, 45, 140)`), drawn at ~235 alpha,
  not pure black-blue.
- Enter the exact name, address, and occupation the user supplies. Do not expand an
  occupation with an agency, court, or jurisdiction unless that wording was supplied.
  Keep every line inside its labeled field and clear of stamps, borders, and adjacent
  text; inspect a crop of the actual final render before reporting completion.
## Trace real ink before typesetting anything

The font is the fallback, not the plan. Before drawing a field, mine every image in
the project for that string in the signer's hand — the supplied sample, the signature
sheet, previews, phone photos of the form. A name is almost always there, and the
sample that was handed over as "what the handwriting should look like" usually
contains it. Copying the ink is both closer and less work than calibrating a font to it.

Lift it exactly like the signature: alpha from the **red channel** (`(255 - R) / 150`
to the power `0.7`) times a blue mask `(B - R) > 24 and B > 60`, pigment set to the flat
`BLUE` tuple. Keep the flat pigment — reusing the source RGB composites the paper blend
back in, the strokes come out pale, and the blue-count assert collapses with no error.

- Delete the printed rule the crop caught: `ink[ink.sum(axis=1) > width * 0.5] = False`.
  A blue-grey rule survives a chroma mask and composites as a dashed line under the text.
- Scale by height to the row, keeping aspect: the sample is usually shot/saved at
  roughly the page's own scale, so this is close to 1:1 and does not go soft.
- A traced name is WIDER than a typeset one, so it changes the tail geometry: the
  signature flourish will cross it. That is real-form behaviour — swap the "tail clear
  of the name" assert for "name ink present" rather than shrinking the real hand.
- Report which fields are traced and which are still typeset; the user then knows
  exactly what to supply to finish the set.

## Match the document's own hand

The font's default casing is a guess. The document is the spec: a declaration that
carries its own hand-written sample (a place, a date, the witness's name on the same
sheet) dictates casing, slant and letter size, and the copied signature already sets
the pen. Read the sample before drawing anything, then reproduce its three parameters —
typically block capitals for a name, mixed case elsewhere, a right slant, no joins.

- Slant is a whole-line property, not a per-glyph one, and the shear needs margin on
  BOTH sides of the tile. `(1, SLANT, 0, 0, 1, 0)` makes output pixel `(x, y)` sample
  input `(x + SLANT*y, y)`, so content low in the tile samples past the right edge and
  is clipped; a widened output canvas alone does not help, the input must be padded by
  the same amount first:
  ```python
  wide = w + round(h * SLANT)
  grown = Image.new("RGBA", (wide + round(h * SLANT), h), (0, 0, 0, 0))
  grown.paste(tile, (0, 0))
  tile = grown.transform((wide, h), Image.AFFINE, (1, SLANT, 0, 0, 1, 0), RS.BICUBIC)
  ```
  Around `SLANT = 0.22` for a normal hand; 0.30 reads as forced italics. Per-glyph
  rotation on top of a shear only adds noise; keep it to ±1.6° per line once the slant
  is in.
- Weight comes from `stroke_width`, not from alpha: pass `stroke_width=1, stroke_fill=BLUE`
  at `ss=3` (`BOLD = 1`). `BOLD = 2` thickens to a marker. Separately, alpha for pressure
  is `uniform(0.72, 0.96)` per glyph — flat 255 reads as vector text.
- Letter size off the sample, not off the box: a sample filling ~a third of its box is
  ~15 pt on a 27 px ruled row, name ~19 pt. Filling two thirds of the row is the
  over-large default and gets called out.
- Descenders crossing the bottom rule is real pen behaviour and is wanted; the failure
  is the glyph being CUT by the tile edge. Place at `y - size * 1.2` with tile height
  `round(size * 1.9) * ss` so the descender has room inside the tile, and lower the
  baseline by 1 px per line only if the result floats too high.
- Block capitals are wide. Shortening the tail's clearance starts a fight with the
  name: re-measure where the text now ends, move its end boundary out, and nudge the
  signature ~10 px further from it rather than shrinking the name back down.

## Placement

- Measure each box from pixels the same way as the signature field; border lines under
a label are found by counting dark pixels per column in the box's row band.
- Baseline lands ~6 px above the box's bottom rule, first glyph ~4 px inside the left
  rule; shrink the size in 0.5 pt steps until `font.getlength(text)` fits the interior
  width. Never let it clip the side rule.
- Draw the line into ONE transparent tile at supersample scale, modulating alpha per
  glyph as you go, then `resize` the tile down with LANCZOS, shear it, tilt it ±1.6°
  and composite once at `y - size` with a small baseline jitter. Fixed seed so a re-run
  is reproducible. Rotating the page or the individual draw call instead shears
  everything else on it.
- Per glyph: `ImageFont.truetype(FONT, round((size + uniform(-1,1)) * ss))`, multiply
  its alpha by `uniform(0.70, 0.95)` (pressure) and `gauss(1.0, 0.05)` (broken edge),
  advance by `font.getlength(ch)/ss * uniform(0.92, 1.05)`.
  **Tile size is `((right - x) * ss, round(size * 1.8) * ss)`** — supersample scale on
  both axes. Sizing the tile in final pixels while drawing at ss coordinates clips the
  glyph tops off and the ink-count assert drops to background level with no error.
- 1x text without supersampling is not enough. Drawing strings straight at final size with only a small
  size/opacity wobble still reads as a font on review — "it doesn't look hand written"
  is the response. The supersample is what supplies the soft, uneven stroke edge and the
  wide rotation range is what breaks the even baseline; both together or neither.
- A whole string in one `draw.text` shares one baseline, one weight and one opacity —
  the strongest tell of all, worse than the font choice.
- Shorten the field list to what the form asks; an occupation line that overruns its
  box is more obvious than an empty one.
- Keep letters short of the signature's descending tail: the tail may cross the box
  and sit in the gap beside the text, but striking through a written name is the
  giveaway that the two were placed separately.

## Ink texture

Apply the modulation to the cut's alpha before compositing, **per pixel, no blur**:
multiply the RGB by `normal(1.0, 0.05)` and the alpha by `normal(1.0, 0.07)`. Two
parameters matter and both are easy to get wrong:

- Mean **1.0, not 0.86**. The multiply is against an already-thin stroke, so any mean
  below 1 silently dims the whole signature and the ink-count check collapses.
- Blur is not needed at all. A `GaussianBlur(0.8)` on the map averages neighbouring
  alpha together, and on 1-2 px light strokes that averaging is exactly what erases
  them — the signature comes back solid with white gaps. Diagonal pressure structure is
  the upgrade path; blur does not buy it.

Page grain goes on last, over the finished composite: `normal(0, 2.4)` added to every
channel. It is a flat overlay, so it does not separate ink from paper — enough to kill
the clean digital edge, not enough for a loupe.

## Assert the result in code

End the script with asserts and let it fail loudly; vision review is for judging
realism, not for catching a placement that moved. Check: ink present in the field,
no empty field left, and the tail clear of the name.

The name check is the one that bites: **the written text is itself blue**, so
"assert no blue in the row band of the name" always trips. Assert on the GAP band
between the end of the text and the tail's x, in the tail's row range, and keep both
bounds as literals from the measured geometry.

Vision models confabulate this one specifically — they report the tail "striking
through" the name across a 60 px gap, and keep reporting it after the render changes.
Settle it with measurements: print the blue column runs in the name's row band and read
whether a gap sits between the last text column and the tail. Group adjacent columns
into runs; a clean gap means no overlap whatever the model claims.

## Calibrating against a reference strip

When the user supplies a handwriting sample, compare it to the render in ONE image —
sample on top, the rendered block below, neither resized to a common width (forcing
both to equal width squashes the shorter crop and the reviewer reports "stretched" and
"compressed" that are pure comparison artefacts). Read four numbers off the sample and
carry them as literals: slant, stroke weight, letter height as a fraction of the box,
and casing.

Vision reviews oscillate — a pass called "too thin, too upright, too small" comes back
"too heavy, too slanted, too big" after the correction. Do not chase it step by step;
split the delta, land on the literal from the sample, and take the first review that
calls it pen rather than the first that stops complaining.

## Report

Field bounds, text placed, per-line size, and the assert list that passed. Then zoom
the whole block at 4x and look before saying it is done.
