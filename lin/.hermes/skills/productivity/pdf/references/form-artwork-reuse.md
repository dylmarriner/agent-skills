# Reusing signature/stamp artwork and filling paper form boxes

The source document already carries the ink (a signed or scanned copy of the form) and the target is a blank copy of the same form. Goal: move existing pen/stamp artwork across faithfully, then fill the remaining boxes.

Fidelity order — take the first that works:

1. Copy the region as page *content* (`show_pdf_page` with `clip`). Nothing is re-rasterised; text stays text and images keep their resolution.
2. Copy only the ink artwork (embedded image + soft mask), cropped.
3. Composite a raster of the region and rescale. Last resort — it re-rasterises text.

## 1. Prove the geometry is identical first

Open both files and compare page count, page `Rect`, and the target page's text. Same form + same rect → every point maps 1:1 and coordinates transfer verbatim between them. Different sizes → scale by the page-width ratio; never eyeball a scale factor.

## 2. Whole-region vector copy

```python
rect = pymupdf.Rect(x0, y0, x1, y1)          # region in points
page.show_pdf_page(rect, src_doc, pno, clip=rect)   # rect == clip is the 1:1 case
```

Use when labels, rules and ink should all come across (copying the surrounding label band too is harmless when both pages print the identical label). Extend the region a few points past the box so overhanging artwork is not clipped.

## 3. Lift only the ink (isolation)

`page.get_images()` yields `(xref, smask, width, height, ...)`. Read each image with its soft mask, rebuild the alpha from the mask **plus** a luminance ramp so the scan's white paper drops out, crop with PIL, insert the PNG:

```python
al = np.minimum(al, np.clip((235 - rgb.min(axis=2)) * 6, 0, 255)).astype(np.uint8)
im = Image.fromarray(np.dstack([rgb, al]), "RGBA").crop(crop)
buf = io.BytesIO(); im.save(buf, "PNG"); page.insert_image(rect, stream=buf.getvalue())
```

- Alpha from the mask alone leaves an opaque white rectangle; alpha from luminance alone washes light artwork out. Use the minimum of the two.
- An image inside a scanned block usually contains the whole mini-form — printed labels and box rules included. Crop to the strokes, or you paste the labels twice and the box rules land mid-field.

## 4. Finding the ink box

Render at 96 dpi, overlay a labelled 50 px grid, ask `vision_analyze` for the tight box, then render the crop alone and confirm nothing is clipped. Vision coordinate reads miss by 10–20% often enough that on anything thin or tight you should confirm numerically with an ink row/column profile:

```python
cp = mask.sum(axis=0)            # columns carrying ink; the signature sits where counts jump over background
```

**Each embedded image has its own pixel geometry.** Crops measured on one image silently return an empty region on another whose height is smaller — and `insert_image` still succeeds, so the loss looks like success. Measure per image and assert the crop is non-empty.

## 5. Re-colour the ink, then place it to fill the box

A scan keeps its paper tone and grey/black pen: on a form the user wants pen **blue** and filling the field, not a grey thumbnail. Paint the ink solid and keep only the alpha:

```python
a = np.clip((235 - lum) * 5, 0, 255) * alpha / 255   # 0..255 float
x0, y0, x1, y1 = crop; a = a[y0:y1, x0:x1]
a[a.shape[0] and (a > 90).sum(axis=1) > a.shape[1] * 0.7] # rule rows, see below
rules = (a > 90).sum(axis=1) > a.shape[1] * 0.7
if drop_rules: a = a[~rules]                        # DELETE the rows, do not zero them
astr = np.clip(a, 0, 255).astype(np.uint8)          # whole-pixel clip BEFORE any comparison
a = np.where(astr < 40, 0, astr)                    # kill paper speckle
astr = np.clip(gaussian_filter(a, 1.0), 0, 255).astype(np.uint8)   # smooth the cut edges
ink = np.zeros((*astr.shape, 3), np.uint8); ink[:, :] = BLUE       # BLUE = (15, 45, 140)
```

- Only ever compare against `0..255` after clipping to `0..255`. Testing a `0..255` array against a value scaled for a larger range zeroes everything and the paste renders invisible while `insert_image` still reports success.
- Zeroing a rule row leaves a line running through the strokes; **dropping** the rows removes it. A near-full-width row inside the crop is a printed rule, never pen.
- Gaussian blur of about 1 px after the threshold step is what stops the stretched ink looking like a stipple pattern.

`insert_image` **keeps the aspect ratio by default**: a wide `rect` is fitted and centred inside, so a deliberately wide target still comes out a small centred thumbnail. Pass `keep_proportion=False` when the rect is the placement:

```python
page.insert_image(pymupdf.Rect(x0, y0, x1, y1), stream=png, keep_proportion=False)
```

- Signature: give it most of the field (roughly 70–85% of the box width, full interior height), anchored left, and leave a clear gap before any stamp at the right. A tall thin scrawl stretched ~3× horizontally still reads as handwriting at box scale.
- Stamp: roughly 20–25 pt high, and proportionally wide — squeezing a 1.4:1 block into a narrow rect truncates its lines.
- Both sit on the box baseline, a point inside the border so nothing is clipped.

## 6. Handwriting for fields with no digital original

- Sample the ink colour from the artwork (mean RGB of pixels under a luminance floor). Source pen is often near-neutral black or a grey scan, but the deliverable is normally expected in pen blue — re-colour both the artwork and the text to one blue (`(15, 45, 140)`) so signature, stamp and entries match.
- Embed a handwriting TTF per field: `insert_text(..., fontname="hand", fontfile=FONT, color=INK)`. Shrink the size until `pymupdf.Font(fontfile=FONT).text_length(text, size)` fits the box; there is no auto-fit.
- Baseline of the original entry (from the signed copy's text spans) is the insertion point — matching it beats any centring.
- Wobble for realism: `morph=(point, pymupdf.Matrix(1, 1).prerotate(±1°))` with a seeded `random.Random(...)` so reruns are byte-identical.

## 7. Self-check (asserts, no framework)

- page count unchanged; `get_images()` sizes equal the crop sizes and every image still has a smask;
- ink counts above a floor inside the signature box, the stamp box, the address and the occupation box — count coloured ink (`(b - r) > 40`) when the artwork is blue, so a red/grey remnant cannot satisfy it;
- the artwork actually spans the field: `max(cols) - min(cols)` of inked columns in the signature box must exceed most of the box width, because a correct-but-tiny paste otherwise passes every count;
- each expected string present in the page text layer;
- every other page text-identical to the input (`[i for i in range(n) if i != target and a[i].get_text() != b[i].get_text()] == []`).

Count ink from a 400 dpi render with a `< 235` luminance floor. At 200 dpi, thin strokes and 1.5 pt stamp glyphs clear a strict threshold or not depending on sub-pixel luck, and a `< 200` floor reports "not drawn" on artwork that is plainly there.

## 8. Prove it with a second renderer

```bash
TMPDIR=/tmp gs -q -dBATCH -dNOPAUSE -sDEVICE=png16m -r150 \
    -dFirstPage=N -dLastPage=N -sOutputFile=/tmp/check.png out.pdf
```

Then look at it. A file that renders in the library that wrote it can still break in a viewer; Ghostscript is an independent engine. `gs` needs a writable `TMPDIR` — point it at `/tmp` rather than whatever scratch dir the agent set up.

## 9. Library plumbing

- `insert_image(..., pixmap=...)` wants an alpha-contiguous pixmap; hand-built `Pixmap(cs, w, h, samples, alpha)` calls are easy to get wrong (`bad samples length`, `Unrecognised args`). Going PIL image → PNG bytes → `stream=` sidesteps it entirely.
- `pymupdf.Pixmap` has no `smask_xref`; get the smask number from `page.get_images()` and match it to the xref.
- Install pymupdf into the interpreter that already has PIL (e.g. `/usr/bin/python3 -m pip install --break-system-packages pymupdf`); a project venv usually has no pip.
- Once the PDF path works, delete the earlier raster/PNG compositing script — two implementations of the same job drift.

## Scope note

The declarant's own lines ("I ___, of ___") and their signature box are separate from the witness block; leave them blank unless asked, and say so in the report rather than filling them with witness data.
