# Transplanting scanned ink (signature, stamp, designation block) into a form

A signature/stamp only exists on some other scan and has to land in an empty
box on a target form scan. Pasting an opaque crop looks pasted: paper tone,
the source's own box rules and the white patch all come along. Extract the ink
as an alpha layer instead and the same code works on any sheet.

## Procedure

1. **Confirm the boxes in pixels before writing constants.** A vision read of a
gridded copy gives an approximate box; verify with a luminance histogram before
hardcoding anything, or the crop clips ink or keeps a border line:

   ```python
   a = np.asarray(Image.open(SRC).convert("L")).astype(int)
   for y in range(y_lo, y_hi):
       print(y, (a[y, x_lo:x_hi] < 150).sum())   # a full-width rule stands out ~10x above text rows
   ```

   Rules are the rows/cols whose dark count jumps to near the crop width.

2. **Crop ink only** - the target box plus the block beneath it, with the
   source's label rows and its outer border columns excluded from the crop.

3. **Build alpha, never an opaque paste.** Two channels, both anchored on
   measured luminance rather than a fixed offset:

   ```python
   blue = np.clip((a[:, :, 2] - np.maximum(a[:, :, 0], a[:, :, 1])) * 4, 0, 255)  # pen
   grey = np.clip((PAPER - a.min(axis=2)) * (255 / (PAPER - INK_FLOOR)), 0, 255)   # press print
   grey[:block_top] = 0        # restrict the luminance channel to where print actually is
   alpha = np.maximum(blue, grey); alpha[alpha < 35] = 0
   ```

   `PAPER` = luminance at the ~75th percentile of blank scan paper (≈228 on a
   flatbed scan), `INK_FLOOR` = darkest print (~140). Feeding 255 into the
   formula instead makes every paper speckle visible; a single scale factor
   either kills light grey print or floods the box with noise.

4. **Delete the source's box rule that crosses the ink**, keeping the pixels
   that are actually part of a stroke or glyph:

   ```python
   r0, r1 = rule_band
   keep = (g[r0 - 5:r0].min(axis=0) < 150) & (g[r1:r1 + 5].min(axis=0) < 150)
   a[r0:r1, ~keep] = 255
   ```

   `&` not `|`: text sitting *below* the rule has vertical support on one side
   only, so a single-sided test keeps the whole rule running through the text.
   A pen stroke crossing the rule is continuous and survives either way.

5. **Force neutral the pixels the luminance channel produced** (`rgb = mean * 0.55`)
   so light press print reads dark on any paper; keep pen pixels at their
   original colour.

6. **Fit into the destination box** - scale by `min(avail_w / w, avail_h / h)`
   with a ~20px margin, centre it, paste with the alpha as the mask. Fitting by
   height alone on a tall aspect (long signature tail) shrinks the ink until it
   is illegible; fit the *whole* ink bounding box, not the box it came from.

7. **Fill the adjacent text fields from the same source data** in a matching ink
   colour, and leave blank any field the source has no data for - do not invent
   an address. Say which field is still blank.

8. **Verify by looking, zoomed.** Render a 2x crop of the target box to PNG and
   read it back (`vision_analyze`): leftover rule, clipped glyphs, tone patch,
   wrong alignment each cost one iteration to see and are invisible in a
   downscaled full-page view. Print counts alone will pass a blurry result.

9. Leave a self-check in the script: ink above a pixel floor inside the box,
   every intended text field filled, and no ink bled outside into neighbouring
   columns. Assert on the saved file, not on the in-memory array.

## Cutting the ink out on its own

When the ink has to become a reusable asset (an RGBA PNG dropped into a spec or
a template later) the crop is not the deliverable - only the strokes are. Same
alpha principle, harder gates:

1. **Calibrate the colour key against this document's own printed grey,** per
   crop. Measure the blue excess `B - max(R, G)` over dark pixels of a printed
   line and of the handwriting, then put the threshold between them (printed grey
   measures <=11, blue pen 25-35; 20 separates them here). A single hard number
   either swallows the print or eats the light stroke ends.
2. **Decide chromatic vs luminance per candidate crop, never per page.** A
   blue-fraction test over the whole page fails on text-heavy pages: a signature
   is ~0.03% of all dark pixels there, so any page-wide ratio resolves to
   "not chromatic" and every printed line scores as ink. Page level only decides
   *whether pen ink exists at all* (an absolute pixel count, e.g. >1500); each
   crop decides which channel to use.
3. **Gate the alpha with a despeckled strong mask dilated 2px**, then take the
   alpha value from the raw colour excess inside it. The dilation keeps the
   antialiased ring; without the gate the scanner's blue cast on grey print
   survives as a ghost outline of the printed line.
4. **Un-blend the paper out of the RGB:** `(px - paper*(1-a)) / max(a, 0.08)`,
   paper = per-channel ~90th percentile. Otherwise every edge pixel carries
   paper tone and the ink glows white on a dark background.
5. **Trim to the remaining ink bbox once at the end,** and drop blobs detached
   from the stroke band (a typed date under the signature) by *vertical band
   overlap* with the main stroke - a width test keeps only the first letter.
6. Return the offset you actually cropped, plus a warning when the box touches
   the page edge: a clipped flourish is invisible in the result until someone
   pastes it.

## Pitfalls

- `Image.fromarray` rejects a float RGBA stack - cast `np.dstack(...)` to
  `uint8` before wrapping.
- Resizing a hard alpha with LANCZOS leaves halos; threshold the alpha after the
  resize, not only before.
- An opaque crop pasted at anything other than ~1:1 scale reads as a blurred
  stamp. If it must scale up, scale the alpha, not a flattened image.
- The source's outer border column is often 1-2px inside a generous crop. Check
  the far edge column count too; exclude it from `CROP` rather than erasing it.
- Re-check the destination's own label geometry: a field box top/bottom can be a
  different row than the neighbouring column's, so hardcode each box separately.
- **Do not blur the alpha to smooth jaggies.** A 0.6px Gaussian pushes nearly
  every pixel of a 1-2px stroke below full opacity and the ink goes watery. Build
  crisp alpha, then resample the RGBA 2x LANCZOS: peaks stay at 255 and the
  stair-steps become a real gradient.
- Despeckle by keeping pixels with **>=1** orthogonal neighbour. Requiring 2
  eats 1-2px stroke ends at scan resolution, which reads as a signature that
  stops mid-letter.
- A dilation helper that ORs into its own output compounds (dy(dy+1)/2 px, ~990px
  for dx=44) and collapses the whole page into one blob. Always shift a snapshot
  of the original mask, not the accumulating array.
- Probe first, judge the numbers: partial-alpha fraction should be a large share
  of ink pixels and peak alpha should reach 255. All-partial means blurred, no
  partial means jagged.
- Never let an advisory warning flip the success flag. "auto-picked candidate" is
  a note; if it sets `ok: false` every automatic run reports failure and the
  caller learns to ignore the flag.
- Self-check on a synthetic page with a known ink mask: recall over any alpha
  >0 (nothing clipped) and precision over alpha >128 (nothing foreign). Raw
  precision against a 1px ground-truth line fails legitimately once the
  antialiased ring is real.
