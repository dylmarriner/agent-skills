# Overwriting values on a flattened (raster) form page

The common case: a quote/invoice/form PDF whose page is a single scanned or
printed raster (2494x3532 = A4 @300dpi is typical), no text layer, no form
fields, and a handful of ID fields to re-set (make, model, rego, odometer,
quote number, client name).

Works with pypdf + Pillow + reportlab only — no pymupdf, no img2pdf needed.

## 0. Confirm it is raster

```bash
pdftotext -layout doc.pdf - | head        # empty output = raster
python3 -c "import pypdf;r=pypdf.PdfReader('doc.pdf');print(len(r.pages), pypdf.PdfReader('doc.pdf').get_fields())"
```

Empty text is not missing data — the values are inked pixels. Render and read
the page with `vision_analyze` before deciding anything is blank.

## 1. Pull the page image at native resolution

```python
img = pypdf.PdfReader(SRC).pages[0].images[0].image.convert('RGB')
```

Work at native scale; never re-render at 150dpi and edit that. Convert crop
coordinates that vision reports at 150dpi by x2 — but treat those numbers as
approximate (see step 2).

## 2. Measure the ink boxes with numpy, not with vision

`vision_analyze` misreports coordinates (identical boxes for different words)
and times out on tall 2x crops. Use it to know *which* values are where, then
measure exactly:

```python
a = np.array(img.convert('L'))

# row runs of ink inside a value column -> find each value's y band
def rowruns(x1, x2, y1, y2, thr=160, gap=6): ...

# column runs inside a band -> find label vs value split
# (labels and values separate by a >12px whitespace gap; use it to find the
# value column start, e.g. x=626, and the next column's label start)
```

Get `(x1,y1,x2,y2)` per value. For values with no descenders the bbox bottom
**is** the baseline — keep those baselines, they are what you re-use.

Check for horizontal rules before choosing erase bands:

```python
for y in range(top, bottom):
    if (a[y, 100:-100] < 160).sum() > 300: print(y)   # full-width rule
```

A rule inside an erase band gets painted out and leaves a visible gap.

## 3. Identify the font by fit, not by eye

Vision's "looks like Times New Roman Bold" is a hint, not an answer. Score
every installed serif/sans bold against the original glyph crop:

```python
import glob, numpy as np
from PIL import Image, ImageDraw, ImageFont
tgt = mask_crop_of_one_original_value       # bool array, tight to ink
best = []
for f in glob.glob('/usr/share/fonts/**/*.ttf', recursive=True):
    for s in range(32, 56):
        ft = ImageFont.truetype(f, s)
        im = Image.new('L', (700, 140), 255)
        ImageDraw.Draw(im).text((30, 30), 'NMF464', font=ft, fill=0)   # same string
        b = np.array(im) < 160
        yy, xx = np.where(b); c = b[yy.min():yy.max()+1, xx.min():xx.max()+1]
        cm = np.array(Image.fromarray((c*255).astype('uint8'))
                      .resize((tgt.shape[1], tgt.shape[0]))) > 127
        best.append(((cm & tgt).sum() / (cm | tgt).sum(), f, s, c.shape))
```

The winner matches the original ink box in both dimensions and wins IoU
(~0.90). FreeSerifBold / LiberationSerif-Bold are the Times clones that usually
win on these NZ/UK trade documents; 42px at 300dpi == 10pt at 72dpi.

## 4. Paint over and re-set

Model the edit as ops keyed by page — footers, dates and client blocks repeat on
every page, and a page-1-only edit is instantly visible on page 2:

```python
# (x, baseline_y, text, font_path, size, erase_x0, erase_x1, erase_y0, erase_y1)
OPS = {0: [make, model, rego, odometer, quote_no, client, footer_label, footer_date],
       1: [footer ops only]}
for page_no, page in enumerate(reader.pages):
    for x, baseline, text, fp, size, x0, x1, y0, y1 in OPS.get(page_no, []):
        d.rectangle([x0, y0, x1, y1], fill=(255, 255, 255))
        d.text((x, baseline), text, font=ImageFont.truetype(fp, size), fill=(0, 0, 0), anchor='ls')
```

For a second run over an already-edited file, always re-read the untouched
`*.orig.pdf` and re-apply every op — editing the edited file double-paints and
accumulates compression loss.

Getting the baseline for a line that has a descender ('Created Wednesday …'):
render the string with `anchor='ls'` at a known baseline, measure `top - baseline`,
then `baseline = target_ink_top + that offset`. Cap-height tops line up across a
line even when descenders do not.

- `anchor='ls'` = left/baseline. Never position by top-left: one value with a
descender ("Volkswagen") drops off the row and looks pasted.
- Erase box: value column start -10px to just before the next column's label.
  Generous width is free; a short erase leaves the tail of the old word visible.
- Value column start from the measured ink bbox, not the label.
- Reproduce multi-run spacing: a label and its date printed as two runs ('Created'
  … gap … 'Tuesday May 8 2025') need two `d.text` calls at the measured x of each
  run; a single concatenated string closes the gap and misaligns the line.

## 5. Rebuild without destroying the other pages

`img2pdf`/one-page-image-PDF silently drops pages 2..n. Write the edited page at
the *original* mediabox and carry the rest over as untouched objects:

```python
c = canvas.Canvas(str(tmp), pagesize=(595, 841))     # original mediabox, in pt
c.drawImage(str(png), 0, 0, width=595, height=841)   # slight stretch is invisible
c.save()

out = pypdf.PdfWriter()
out.add_page(pypdf.PdfReader(str(tmp)).pages[0])
out.add_page(reader.pages[1])                        # original page 2, untouched
```

Back up the source once (`*.orig.pdf`) and write the update over the original
path the user gave you; they want that file updated, not a new name.

## 6. Leave one runnable check

Assert page count, then re-decode the output image and assert dark ink exists
where each new value was drawn — that catches a silently skipped field:

```python
assert len(pypdf.PdfReader(SRC).pages) == 2
a = np.array(pypdf.PdfReader(SRC).pages[0].images[0].image.convert('L'))
for x, basel, text, *_ in FIELDS:
    assert (a[basel-30:basel-5, x-2:x+40] < 100).sum() > 30, text
```

Then `pdftoppm -r 150` + `vision_analyze` the edited block **and** the whole
page: leftover old text, stray white patches, and damage elsewhere only show
up in the image. Crop by arithmetic, not by guess: at `dpi` the line with
PDF baseline `y` sits at `px_y = (page_height_pt - y) * dpi / 72`, so a
full-page read at 150dpi puts the value row exactly where you compute it.
Report which adjacent fields were left as-is (year, VIN, blank columns) instead
of silently inventing them.
