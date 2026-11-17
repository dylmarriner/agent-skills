---
name: pdf-editing-undetectable
description: "Edit PDFs so the result is visually indistinguishable from the original. Covers native text replacement (pymupdf redact+insert), image-based editing (pdftoppm→PIL→img2pdf→ocrmypdf), SVG pipeline (pdftocairo→Inkscape→cairo), and qpdf structure-level operations."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [PDF, editing, OCR, image-manipulation, forgery-quality]
---

# PDF Editing — Undetectable Quality

Three approaches, depending on the PDF type and what you're changing.

## Prerequisites — already installed on this machine

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

## Approach A: Native Text Replacement (Best for text-based PDFs)

Use when the PDF has actual text content, not scanned images. The result has selectable text.

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
| Text-based | Simple text swap | A (pymupdf native) — fastest, text stays selectable |
| Text-based | Multi-line / complex layout | A or C |
| Text-based | Uncommon font, styled text | B (image-based) — pixel-perfect |
| Scanned PDF | Any text change | B (image-based) — only option |
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
```
