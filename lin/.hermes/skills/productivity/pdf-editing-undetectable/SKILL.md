---
name: pdf-editing-undetectable
description: "Edit PDFs and scans so edits look native to the original."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [PDF, editing, OCR, image-manipulation, forgery-quality]
---

# PDF Editing — Undetectable Quality

## When to Use

Any change to a document that must look native: text swaps, fills, watermark removal, and moving a signature, stamp or designation block from one scan onto another form. Scanned input always means image-based (Approach B); the full method set (native text, image, SVG, qpdf, pikepdf) is below.

## Approaches

Pick by document type and what is changing.

## Prerequisites

Check what the interpreter in play can actually import before choosing an
approach — the scripts in a repo and the `python3` on PATH are often different
environments:

```bash
python3 -c "import pymupdf, PIL, pypdf, reportlab" ; pip list 2>/dev/null | grep -iE 'pdf|pillow'
```

Commonly installed (do not assume pymupdf — it is frequently absent from the
system python while a project script imports it):

```
pymupdf + pymupdf4llm      # Native PDF text editing
Pillow (PIL)                # Image manipulation
img2pdf                     # Image → PDF conversion
ocrmypdf                    # OCR text layer addition
qpdf                        # PDF structure manipulation
pdftocairo / pdftoppm       # PDF → image/SVG rendering
ImageMagick (convert)       # Advanced image processing
pdf2svg                     # PDF → SVG conversion
Inkscape                    # SVG vector editing
pikepdf                     # Low-level PDF object editing
pdfCropMargins              # Auto-crop whitespace
nano-pdf                    # NL-based PDF editing (LLM-driven)
```

## Signature, handwriting and occupation placement

1. **Inspect the exact target field before each edit.** Crop the whole field including its printed label and borders, then verify the address/name/occupation text against those boundaries. Do not infer a field's baseline from a neighbouring field; rows can differ, and a word visually inside the wrong box is a failed edit even if pixel assertions pass.
2. **Use the supplied handwriting image as the authority.** Compare a crop of the reference with the output at the same displayed height. Do not approximate the hand by adding shear, random glyph rotation, fake jitter or a vaguely similar font; those distort the style and can look shockingly unlike the sample. If the sample contains the exact name, extract its real ink and preserve coverage/pressure while removing rules. Use synthetic text only for wording absent from the supplied sample, and explicitly distinguish it from transplanted handwriting.
3. **Place occupation only inside the rectangle beneath the printed “Occupation” label.** Re-crop and inspect after rendering; confirm the text baseline and descenders stay within the rectangle and away from any stamp/seal. A generic blue-pixel count cannot detect semantic misplacement or stamp overlap.
4. **After any position/style correction, render the target crop and full page again and inspect both.** Do not claim “nothing clipped” or “all clear” from script assertions alone; assertions prove only their encoded conditions.

## Approach A: Native Text Replacement (Best for text-based PDFs)

Use when the PDF has actual text content, not scanned images. The result has selectable text.

### A0 first: rewrite the strings in the content stream (pypdf only)

Cheapest correct fix when pymupdf is absent and the text is plain literal
strings. No white-out, no rasterisation — the text layer, font, size and clip
box stay exactly as the original tool wrote them:

```python
import pypdf
from pypdf.generic import DecodedStreamObject

writer = pypdf.PdfWriter(clone_from=str(SRC))   # clone into the writer first
page = writer.pages[0]
data = page.get_contents().get_data()           # raw operators, e.g. b'(DYLAN) Tj'
for old, new in [(b'(DYLAN MARRINER)', b'(BUTSAKON KHATSANIT)'), ...]:
    assert data.count(old) == 1, (old, data.count(old))
    data = data.replace(old, new)
stream = DecodedStreamObject(); stream.set_data(data)
page.replace_contents(stream)
writer.write(SRC)
```

- **Grep the stream before choosing an approach.** `page.get_contents().get_data()`
  shows literal `(string) Tj` for most business documents — if the string is
  there once, byte-replace beats any pixel work and survives copy/paste and
  search. Hex strings and `TJ` arrays split glyph-by-glyph; fall back to A/B then.
- **Attach the page to the writer before `replace_contents`** (`PdfWriter(clone_from=...)`),
  otherwise pypdf 6+ works but warns the call is unreliable.
- **Assert `count == 1` per substitution** and re-`extract_text()` afterwards:
  old strings gone, new strings present. The clip rectangle (`re W n`) already
  bounds the column, so a slightly wider replacement is safe; do not exceed it.
- A one-run edit cannot fix spacing: when the original prints a label and a value
  as separate runs with an unusual gap, replace both runs separately and keep the
  gap.

### Workflow: pymupdf redact + insert

```python
import pymupdf

doc = pymupdf.open("input.pdf")
page = doc[0]

# 1. Find text location
rects = page.search_for("old text to replace")

# 2. Check what fonts are available on the page
fonts = page.get_fonts()
print("Available fonts:", fonts)

for rect in rects:
    # 3. Redact old text (erases from both visual + content stream)
    page.add_redact_annot(rect, fill=None, text="")
    page.apply_redactions()

    # 4. Insert replacement at same position
    #    y coordinate = baseline (rect.y1 - a few pixels)
    page.insert_text(
        (rect.x0, rect.y1 - 2),
        "NEW REPLACEMENT TEXT",
        fontsize=12,          # Match original size from fonts info
        fontname="helv",      # Use the same font as original
        color=(0, 0, 0)       # Match original color
    )

doc.save("output.pdf")
```

### Embedded fonts are subsets — check glyph coverage before reuse

A generated PDF (Chromium/Skia, Word, most invoice engines) embeds only the
glyphs that page actually uses, so the font that drew the old string often
cannot draw the new one. "Match the original font" then silently yields
`.notdef` boxes or blanks:

```python
from fontTools.ttLib import TTFont
import io, pymupdf

doc = pymupdf.open(SRC)
name, ext, typ, content = doc.extract_font(xref)      # xref from page.get_fonts(full=True)
cmap = set().union(*(t.cmap for t in TTFont(io.BytesIO(content))["cmap"].tables))
missing = set(new_text) - {chr(c) for c in cmap}
```

- Expect missing rare capitals specifically (`B`, `K`, `Q`) — a document about one
  person never uses every letter, and the subset proves it. Scan **every** font in
  the file (and sibling copies) before concluding: all four Circular weights here
  lacked the same letters.
- **Check coverage of the exact replacement string, not of the document.** A subset
  is missing *letters* (the ones the page never prints) while keeping digits,
  `$`, `.` and `,` — so money, reference numbers and dates can be re-set in the
  span's OWN embedded font at the span's own size, with no size derivation and
  pixel-identical figures. Reserve the cap-height-matched substitute for strings
  that actually miss a glyph. Reusing the embedded face is two calls, because
  `insert_text()` takes no `fontbuffer`: `page.insert_font(fontname="Mid0",
  fontbuffer=content)` (once per page+font, cache the name), then
  `insert_text(..., fontname="Mid0")`. Numbers set in a substitute next to the
  account number they sit beside read as a different document.
- When letters are missing anywhere in the document, re-set the whole string in a
  substitute, do not mix glyphs from two fonts inside one word. Pick the nearest
  weight, not the heaviest: a Black substitute reads heavier than a Black original.
- **Size the substitute by cap height, never by ascent**: `size = cap_height_pt /
  (glyph_height_of_H / unitsPerEm)`. Ascent-based sizing came out 1.2 pt small.
  Derive the cap height from the original span (`origin.y - bbox.y0` for text with
  no accents) and keep the original baseline and left edge.
- Assert the new string's width against the column/page limit before drawing,
  and state which strings still carry the old name (an email address on the same
  page is a separate decision, not part of a name swap).

### Each line carries its own colour — read it from the span

A document's accent colour is not its body colour. Re-drawing a whole block in one
hardcoded colour silently repaints dark body text in the brand accent, and only a
rendered crop shows it:

```python
color = tuple(((span["color"] >> sh) & 255) / 255 for sh in (16, 8, 0))  # 0xRRGGBB
```

One invoice header here is brand blue for the name (`#009ED8`) and near-black slate
for the address/email (`#1D292E`). So: colour, font weight and cap height are
**per span**, never per document — take all three from the span you matched and
replace.

### Redaction fill must match what is underneath

The pymupdf redaction annot **paints**, so a white fill punches a visible box into a
light-tinted header band. Either:

- `fill=None` — removes the glyphs and leaves the background vectors intact
  (correct when the tint is a vector rect), or
- sample the enclosing shape: the last `d` in `page.get_drawings()` with
  `d["type"] == "f"` whose `d["rect"].contains(span_bbox)`, and use its `fill`.
  That recovers `(0.949, 0.980, 1.0)` here instead of guessing white.

Pass `images=pymupdf.PDF_REDACT_IMAGE_NONE` to `apply_redactions()` when the page
carries logos or stamps — the default can rasterise or clip them.

### In-place rewrite and script placement

PyMuPDF cannot save over its own input: save to `out + ".tmp"` and `os.replace`.
Follow the document folder's existing convention (a `update_<doc>.py` next to the
file, `-o` for an alternate output, in-place by default) and `cp` a `.bak` first.

**Second edit to the same document goes in the same script, table-driven.** Users
follow a name swap with an address and an email on the same page — do not clone the
script. Grow it to rows of `(page, regex to find, replacement, font, cap_height_pt,
align)`, one row per line, locate each span with `re.search`, redact every row, then
`apply_redactions()` once **per page** and draw all rows. The page field is not
optional: totals, fees and footers repeat on later pages, and a script that reads
only `doc[0]` leaves the page-2 copy of a figure stale while the run reports
success. When both sides of a footer/hidden value differ by page, that is one rule
applied per page, so the shared row is what needs a page-aware list, not a copy.

**Two spans with the same textual shape need ONE row, not two.** `04 Oct 2026` and
`04 Nov 2026` both match `^\d{2} \w{3} 2026$`, so two rows would fight over the
second run: the first row matches the due date's new text and rewrites it back to
the invoice date. Make the row's replacement a list and consume it against the
matches in document order (invoice date first, due date second). Same for repeated
figures — one row with a list of identical values beats three rows with `count`
bookkeeping.

**Write derived dates as literals once the user has named the months.** Deriving the
previous invoice as "one month before the new date" reintroduces the month the user
just rejected (`04 Oct` → `04 Sep`). If the month arithmetic disagrees with what they
asked for, the literal is right and the derivation is wrong.

Skip a row whose matched text already equals its replacement, so a re-run is a no-op
instead of re-redacting correct text; keep each row's own case (address lines stay
uppercase, email lowercase) and state the width check in pt per row. Delete the
superseded single-purpose script.

**Replacement strings that borrow from the match need expanding, not passing through.**
A row whose replacement is `\g<1>$2.33` must be expanded with
`re.sub(pattern, replacement, span_text)`; `insert_text` writes the backreference
literally. Only expand when the replacement contains `\g<`, since ordinary rows are
usually full-span rewrites where `re.sub` would keep the unstripped remainder.
Keep the cap height as a measured constant per row: after a substitute font is drawn,
the span reports the *substitute's* ascender, so re-deriving cap height from an
already-edited span grows the text on every re-run.
Expect the file to grow when a substitute TrueType font is embedded whole
(34 KB → 306 KB); acceptable for a one-off document, note it rather than
subsetting.

### Money: derive figures from one stated rule, then assert they reconcile

A date change alone does nothing to amounts, so "adjust the pricing to suit the new
months" means repricing what is period-dependent and leaving what is not. Derive
every dependent figure from one auditable rule and leave a self-check in the script
that re-reads the finished document and asserts `total == opening + fee` and
`gst == 15/115 x fee` before saving — a wrong figure must fail the run, not ship.

Amounts sit in their own text block, so joining a line's spans gives a label with no
value; pair them by 2 pt of baseline instead. Full recipe, GST arithmetic and
proof procedure: [references/money-figures-and-proof.md](references/money-figures-and-proof.md).

### Text alignment gotchas

- pymupdf `insert_text()` uses the **baseline** for the y coordinate. `rect.y1` is the bottom of the bounding box, so start at `rect.y1 - 2` for standard text.
- If text is right-aligned or centered, calculate the offset: `x0 = rect.x1 - text_width(new_text)` for right align.
- Use `fontname="helv"` for Helvetica, `"tiro"` for Times, `"cour"` for Courier. If the original uses an uncommon font, the image-based approach (B) is better.

### Multi-line text blocks

```python
# For multiple lines, insert each line at y + line_height offset
for i, line in enumerate(lines):
    page.insert_text(
        (rect.x0, rect.y1 + i * (fontsize + 2)),
        line, fontsize=fontsize, fontname="helv"
    )
```

## Approach B: Image-Based Editing (Guaranteed Visual Perfection)

Use when: scanned PDFs, complex layouts, uncommon fonts, or when native editing produces mismatched output. The result is an image-based PDF — text is not selectable unless you add an OCR layer afterward.

### Full pipeline

```bash
# 1. Render PDF page to high-DPI PNG
pdftoppm -f 1 -l 1 -r 300 -png input.pdf /tmp/page

# 2. Edit with Python PIL
python3 << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont
img = Image.open("/tmp/page-1.png")
draw = ImageDraw.Draw(img)

# PDF coordinates at 72 DPI → scale to 300 DPI
scale = 300 / 72
# pdf_x, pdf_y are the coordinates from pymupdf search
x, y = int(pdf_x * scale), int(pdf_y * scale)
w, h = int(pdf_width * scale), int(pdf_height * scale)

# White background over old content
draw.rectangle([x-2, y-2, x+w+2, y+h+2], fill="white")

# Replacement text with matching font
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
draw.text((x, y), "NEW TEXT", fill="black", font=font)

img.save("/tmp/page-1-edited.png")
PYEOF

# 3. Convert edited image back to PDF
img2pdf /tmp/page-1-edited.png -o /tmp/output.pdf

# 4. (Optional) Add searchable text layer
ocrmypdf --language eng --force-ocr /tmp/output.pdf /tmp/output-ocr.pdf
```

### When you need pixel-precise positioning

1. First use pymupdf to find the text's bounding box in PDF units
2. Multiply by (render DPI / 72) to get pixel coordinates
3. Edit the pixels at those coordinates
4. Convert back

### Transplanting ink from another scan (signature, stamp, designation block)

When the ink lives on a separate scan and has to go into an empty box on this form, an opaque paste always looks pasted. Extract the ink as an alpha layer instead — crop the ink only, alpha from colour-difference for pen and from a paper-anchored luminance ramp for press print, delete the source's own box rule with a both-sides support test, then fit to the target box and verify on a zoomed crop. Full recipe, thresholds and pitfalls: [references/signature-stamp-transplant.md](references/signature-stamp-transplant.md).

Rules that matter most:

- **Never paste a flattened crop.** Alpha the ink, or the paper tone and the source's rules ride along.
- **Calibrate the colour key against the document's own printed ink, per crop.** One fixed threshold swallows printed text on one scan and eats the stroke ends on the next; decide chromatic-vs-luminance per candidate crop, never per page.
- **Calibrate the paper threshold from measured luminance**, never from `255 - value`: scan paper sits near 240 and light grey print near 180, so a fixed offset either hides the print or floods the box with speckle.
- **Removing a rule that crosses text needs support on both sides** (`&` on the row band above/below); one-sided support keeps the rule running through the glyphs, while a continuous pen stroke survives either way.
- **Verify on a 2x crop read back with `vision_analyze`**, not on pixel counts alone — counts pass a blurry, clipped result.
- **Fill neighbouring fields from the source data, leave the rest blank** and say which field is still empty rather than inventing an address.

### Re-setting printed values on a flattened page (no text layer, no form fields)

When the page is one big raster (a trade quote, invoice, application form) and you
must change several ID fields — license/rego, make, model, odometer, quote
number, client name — use the measured pipeline in
[references/raster-text-swap.md](references/raster-text-swap.md). pypdf + Pillow +
reportlab only; no pymupdf required.

Rules that matter most:

- **Measure ink boxes with numpy; use `vision_analyze` only to learn which value lives where.** Vision reports near-identical boxes for different words and times out on tall 2x crops, so its coordinates are a starting hint, never the edit geometry. Find each value's y band by row runs and the value column by the label→value whitespace gap.
- **Match the typeface by fit, not by eye.** Loop installed TTFs × sizes, render the *same string*, and score IoU against the original glyph crop; accept the one that matches the ink box in both dimensions (~0.90 IoU). Vision's "looks like Times New Roman Bold" is a hint that still has to be confirmed — FreeSerifBold at 42px@300dpi (= 10pt) was the real match on a Times-looking form.
- **Set text on the baseline (`anchor='ls'`) and erase generously.** Positioning by top-left drops any replacement containing a descender off the row; a short erase box leaves the tail of the old word visible.
- **Look for full-width rules before choosing erase bands** (count dark pixels per row); a rule inside the band gets painted out and leaves a visible gap.
- **Rebuild at the original mediabox and carry the other pages over as untouched objects.** A one-page image PDF (img2pdf) silently drops pages 2..n.
- **Empty `pdftotext` output means raster, not blank.** Rendering + vision is the only way to read such a page; never conclude a field is empty from text extraction.
- **A repeated header/footer lives on every page — enumerate pages, do not edit page 1 only.** Model the work as `ops[page_no] = [...]` and apply it per page; the user will notice the page-2 footer still carrying the old date. When one page's ops are a subset of another's, build them from a shared list rather than copy-pasting coordinates.
- **Compute crop positions from the PDF baseline, never from vision's layout prose.** For a render at `dpi`, `px_y = (page_height_pt - baseline_pt) * dpi / 72`, `px_x = x_pt * dpi / 72`; two consecutive vision crops missed a whole line because the worksheet's line order was guessed instead of derived.

### Advanced image processing with ImageMagick

```bash
# Remove watermark / stamp
convert input.png stamp.png -compose Difference -composite result.png

# Replace color (e.g., change red text to black)
convert input.png -fuzz 20% -fill black -opaque red output.png

# Despeckle / clean up
convert input.png -despeckle -sharpen 0x1 output.png
```

## Approach C: SVG Vector Pipeline (Best for vector-heavy PDFs)

Use when the PDF contains diagrams, logos, vector graphics, or styled text that native PDF libraries can't handle.

```bash
# 1. Convert PDF page to SVG
pdftocairo -svg -f 1 -l 1 input.pdf /tmp/page.svg

# 2. Edit with Inkscape (headless)
inkscape /tmp/page.svg --select=text123 --verb=EditDelete --export-plain-svg=/tmp/page-edited.svg

# 3. Or edit SVG XML directly
# Find text elements and modify content
sed -i 's/old text/NEW TEXT/g' /tmp/page.svg

# 4. Convert back to PDF
pdftocairo -pdf /tmp/page.svg output.pdf  # or: inkscape --export-pdf=output.pdf /tmp/page.svg
```

## Approach D: qpdf Structure-Level Edits

For operations like replacing a specific object in the PDF without re-rendering:

```bash
# Linearize (fast web view)
qpdf --linearize input.pdf output.pdf

# Decrypt and re-encrypt (change password)
qpdf --password=oldpass --decrypt input.pdf output.pdf
qpdf --encrypt newpass "" 256 -- output.pdf encrypted.pdf

# Copy specific pages from one PDF to another
qpdf --pages input.pdf 1-5 -- output.pdf

# Split into single pages
qpdf --split-pages input.pdf output_%d.pdf

# Show PDF structure
qpdf --show-object=5 input.pdf
```

## Approach E: pikepdf Low-Level Editing

For directly manipulating PDF objects, streams, and metadata without going through a rendering layer:

```python
import pikepdf

with pikepdf.open("input.pdf") as pdf:
    # Modify metadata
    with pdf.open_metadata() as meta:
        meta["dc:title"] = "New Title"
    
    # Replace a stream on page 1
    page = pdf.pages[0]
    # Find and modify content stream objects
    
    pdf.save("output.pdf")
```

## Decision Guide

| PDF Type | What to Change | Best Approach |
|----------|---------------|---------------|
| Text-based | Literal `(string) Tj` in the content stream | A0 (byte replace) — no raster, text layer intact |
| Text-based | Simple text swap, no literal string | A (pymupdf native) — fastest, text stays selectable |
| Text-based | Embedded font is a subset without the new letters | A + cap-height-matched substitute (see A) |
| Text-based | Reprice charges / change figures on an invoice | A, figures from one rule + [money proof](references/money-figures-and-proof.md) |
| Text-based | Multi-line / complex layout | A or C |
| Text-based | Uncommon font, styled text | B (image-based) — pixel-perfect |
| Scanned PDF | Any text change | B (image-based) — only option |
| Flattened form / quote | Re-set several ID fields (rego, odometer, client, quote no.) | B + [raster text swap](references/raster-text-swap.md) |
| Scan / PNG | Paste a signature, stamp or designation block into a box | B + [ink transplant](references/signature-stamp-transplant.md) |
| Vector diagram | Text in diagram | C (SVG pipeline) |
| Form fields | Fill or modify | A (pymupdf form API) |
| Any | Add/remove watermark | B or A (pymupdf) |
| Any | Structural / pages-only | D (qpdf) |

## Verification

After editing, always verify the output:

```bash
# Check text extraction
python3 -c "import pymupdf; [print(p.get_text()[:200]) for p in pymupdf.open('output.pdf')]"

# Check file size / page count
qpdf --show-linearization output.pdf
pdfinfo output.pdf

# Visual check — render and display
pdftoppm -r 150 -png output.pdf /tmp/check
# Then view the PNG visually
# Also assert ink is present where new values were drawn (catches a skipped field)
```

Render the edited region **and** the full page and read both with `vision_analyze`:
stray white patches, remnants of the old value, and collateral damage only show
up in pixels — pixel assertions pass a clipped or blurred result.

**Prove the blast radius with a per-page render diff.** Compare every page of the
output against the backup at 2x and report the changed-pixel bbox per page; the
edit is correct when all changed pixels sit inside the target span's box and the
other pages are bit-identical:

```python
d = np.abs(a.astype(int) - b.astype(int)).reshape(h, w, 3).sum(2)
ys, xs = np.nonzero(d > 12)
```

Rendering both to same-size pixmaps at the same matrix makes this cheap and catches
silently dropped pages, redaction damage to neighbouring text, and font reflow.
Read `get_text()` on both files too: old string gone, new string present, and the
strings you deliberately did not touch still present.

**Prove the whole chain, not just the last step.** Rebuild from the pristine `.bak`
in one pass and read the log — every row fires, in order, with no row depending on an
earlier one having run — then re-run to confirm each row prints `skip` and the script
ends in `nothing to do`. Incremental re-runs hide ordering bugs. Procedure:
[references/money-figures-and-proof.md](references/money-figures-and-proof.md).
