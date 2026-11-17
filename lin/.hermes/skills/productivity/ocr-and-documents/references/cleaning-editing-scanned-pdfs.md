# Cleaning & Editing Scanned PDFs

Workflow for taking a scanned PDF (image-based, no extractable text), cleaning up the visuals, and/or editing the text content.

## ⚠️ CRITICAL: Preserve Original Content — DO NOT DESTROY

**This is the #1 mistake agents make with scanned documents. The user WILL reject the result if you destroy original content.**

### The rule: "clean up" = NO erasing, NO replacing, NO text overlays

If the user says "clean up", "restore", "make a copy and clean it", or "fix it" — that means **visual enhancement only**:
- ✅ Contrast adjust (per-channel, never grayscale-only)
- ✅ Noise removal (despeckle)
- ✅ Watermark crop (only at the very bottom edge)
- ✅ Light sharpen
- ❌ NO erasing text regions with white rectangles
- ❌ NO replacing text with a different font
- ❌ NO converting to grayscale
- ❌ NO overlaying new text
- ❌ NO trimming edges that might contain colored borders/stamps

### "Logos and colour" — what the user means

When told "it doesn't look like the original", they mean you destroyed something visible. The most common pattern of failure:

1. **Erase text with white rectangles** → destroys logos, stamps, colored ink, and design elements that were near the text
2. **Convert to grayscale** → destroys colored stamps (red/blue), gold/foil logos, and warm paper tones
3. **Overlay text in pure black sans-serif** → looks fake, mismatches the original handwritten/printed Naskh-style Persian text
4. **Crop off the bottom** → might remove a logo or design element at the edge

**Real example from an Iranian gold invoice:**
- Agent erased "ZOMORROD GOLD GALLERY" in the footer → destroyed the shop's logo/wordmark
- Agent used pure black text → original was dark reddish-brown (R=164, G=70, B=33)
- Agent used Noto Sans Arabic → original was Naskh-style
- Agent filled with pure white → original paper was warm beige
- Multiple white rectangles visible on page → looked obviously doctored

### The ONLY safe pipeline for restoration

```bash
# Step 1: Extract pages (keep as RGB — never grayscale)
pdftoppm input.pdf /tmp/page -png -r 300

# Step 2: Gentle per-channel enhancement (keep color!)
for pg in 1 2; do
  convert /tmp/page-${pg}.png \
    -contrast-stretch 1% \   # per-channel contrast (preserves color balance)
    -despeckle \              # noise removal only
    -quality 92 \
    /tmp/page-${pg}-restored.png
done

# Step 3: Crop watermark ONLY at the very bottom (120px = ~1cm at 300dpi)
convert /tmp/page-1-restored.png -gravity south -chop 0x70 /tmp/page-1-final.png

# Step 4: Keep as color JPEG when reassembling PDF
convert /tmp/page-1-final.png /tmp/page-2-final.png \
  -quality 85 -compress JPEG output_restored.pdf
```

**No white rectangles. No font replacements. No color changes. Just filters.**

### When you DO need to edit text (only if user asks to change content)

See Section 2 below for the full technique. But even then:
- Sample the original ink color — never assume pure black
- Sample the background color — never use pure white for erasure
- Use Naskh or Nastaliq fonts for Persian, not sans-serif
- Keep the image in RGB mode throughout — don't convert to grayscale


# Crop off watermark (e.g. CamScanner at bottom)
for pg in 1 2; do
  convert /tmp/page-${pg}-restored.png \
    -gravity south -chop 0x70 \
    /tmp/page-${pg}-final.png
done

# Reassemble as PDF
convert /tmp/page-1-final.png /tmp/page-2-final.png \
  -quality 85 -compress JPEG output_restored.pdf
```

**Key rules:**
- Keep color mode (RGB) — do NOT convert to grayscale
- Do NOT draw any white rectangles
- Do NOT overlay any new text
- Only crop off watermarks at the very bottom edge
- If you want to enhance text, use per-channel contrast stretch (each RGB channel independently), not grayscale+threshold

**If you DO need to edit text** (user explicitly asks to change a value): use the technique in section 2, but preserve the original background color around the text and match the original ink color — do NOT use pure black (0,0,0). Analyze the original text color first (see "Matching original text color" below).

## Prerequisites

```bash
# Image processing
sudo apt-get install -y imagemagick poppler-utils

# OCR to locate text regions (for editing)
# See main SKILL.md for EasyOCR setup
source /tmp/easyocr_venv/bin/activate

# Python PIL (comes with Pillow — usually pre-installed)
pip install Pillow
```

---

## 1. Visual Cleanup

Remove scan artifacts, normalize contrast, crop watermarks.

### Step 1: Extract pages to high-DPI images

```bash
mkdir -p /tmp/pdf_clean
pdftoppm input.pdf /tmp/pdf_clean/page -png -r 300
# Use -r 600 for better detail (slower but sharper OCR later)
```

### Step 2: Clean each page with ImageMagick

```bash
for pg in 1 2; do
  convert /tmp/pdf_clean/page-${pg}.png \
    -colorspace Gray \
    -normalize \
    -contrast-stretch 2%x1% \
    -unsharp 0.5x1+0.8+0 \
    -despeckle \
    -quality 95 \
    /tmp/pdf_clean/page-${pg}-clean.png
done
```

**What each step does:**

| Operation | Effect |
|-----------|--------|
| `-colorspace Gray` | Removes color noise |
| `-normalize` | Stretches histogram to full range |
| `-contrast-stretch 2%x1%` | Slightly clips black/white points to avoid faded edges |
| `-unsharp 0.5x1+0.8+0` | Controlled sharpening without ringing artifacts |
| `-despeckle` | Removes isolated noise pixels |
| `-quality 95` | Preserves quality for PNG output |

### Step 3: Remove watermarks (e.g. CamScanner)

Find the watermark position by checking image dimensions and cropping:

```bash
h=$(identify -format "%h" /tmp/pdf_clean/page-1-clean.png)
# Crop off bottom 120 pixels (adjust as needed)
crop_h=$((h - 120))
convert /tmp/pdf_clean/page-1-clean.png -crop x${crop_h}+0+0 \
  /tmp/pdf_clean/page-1-cropped.png
```

**Alternative:** Paint over the watermark with a white rectangle:

```bash
convert page.png -fill white -draw "rectangle 0,2360,3509,2480" page-no-watermark.png
```

### Step 4: Reassemble into PDF

```bash
convert /tmp/pdf_clean/page-1-cropped.png /tmp/pdf_clean/page-2-cropped.png \
  -quality 85 -compress JPEG output_clean.pdf
```

---

## 2. Text Editing on Scanned PDFs

After OCR tells you where text is, you can erase old text and write new Persian/Arabic text.

### Step 1: Locate text regions via OCR

```python
import easyocr
reader = easyocr.Reader(['fa', 'en'], gpu=False)
results = reader.readtext('/tmp/page-1.png', detail=1)
for bbox, text, conf in results:
    if conf > 0.3:
        # bbox = [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        x1, y1 = int(bbox[0][0]), int(bbox[0][1])
        x2, y2 = int(bbox[2][0]), int(bbox[2][1])
        print(f"[{conf:.2f}] ({x1},{y1})-({x2},{y2}) = {text}")
```

### Step 2: Erase and overlay new text with PIL

Before erasing, **analyze the original text color** to match it:

> **Real-world example:** An Iranian gold invoice had text color R=164, G=70, B=33 (dark reddish-brown), not pure black. Using pure black (0,0,0) would have looked obviously fake. Always do pixel analysis.

```python
from PIL import Image
img = Image.open("/tmp/page-1.png").convert("RGB")
px = img.load()

# Sample pixels in the text region to find the ink color
r_sum, g_sum, b_sum, count = 0, 0, 0, 0
for x in range(x1, x2):
    for y in range(y1, y2):
        r, g, b = px[x, y]
        if r < 200 or g < 200 or b < 200:  # non-white = text pixel
            r_sum += r; g_sum += g; b_sum += b; count += 1

if count > 0:
    ink_color = (r_sum//count, g_sum//count, b_sum//count)
    print(f"Original text color: R={ink_color[0]} G={ink_color[1]} B={ink_color[2]}")
else:
    ink_color = (0, 0, 0)  # fallback to black
```

Then use that color when writing new text:

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.open("/tmp/page-1.png").convert("RGB")
draw = ImageDraw.Draw(img)

# Font setup — use a font that supports the target script
# For Persian/Arabic: Noto Sans Arabic, Noto Naskh Arabic, IBM Plex Sans Arabic
font_path = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
font_bold = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"

# ALSO preserve any background color/stamp in the erased region:
# First sample the background color of the region
bg_r, bg_g, bg_b = 0, 0, 0
bg_count = 0
for x in range(x1, x2):
    for y in range(y1, y2):
        r, g, b = px[x, y]
        if r > 230 and g > 230 and b > 230:  # near-white background
            bg_r += r; bg_g += g; bg_b += b; bg_count += 1

if bg_count > 0:
    bg_color = (bg_r//bg_count, bg_g//bg_count, bg_b//bg_count)
else:
    bg_color = (255, 255, 255)  # fallback

# Erase the old text with a rectangle matching the background color
draw.rectangle([x1-20, y1-20, x2+20, y2+20], fill=bg_color)

# Write new Persian text (RTL — position right-aligned) using MATCHED ink color
font = ImageFont.truetype(font_bold, 72)
draw.text((x2-20, y1-10), "طلاسازی زمرد", fill=ink_color, font=font)

img.save("/tmp/page-1-edited.png", quality=95)
```

**Key points:**
- Always add ~20-30px padding around the OCR bounding box when erasing
- For RTL scripts like Persian/Arabic, the text starts at the right edge of your bounding box
- Use `ImageFont.truetype(path, size)` with a script-appropriate font
- Sizes depend on DPI: at 300 DPI, 72pt is ~1 inch (approx 24px per character in Persian)
- Check available Persian/Arabic fonts: `fc-list :lang=fa`
- **Never assume pure black** — scanned documents often have brownish/sepia ink (e.g. R=164, G=70, B=33 from an Iranian gold invoice)
- **Never use pure white fill** — use the actual background color of the region
- **Prefer Noto Naskh Arabic** over Noto Sans Arabic for traditional Persian documents (looks more natural)
- **If you don't need to change text, DON'T ERASE ANYTHING** — just clean the image

### Step 3: Convert edited images back to PDF

```bash
convert /tmp/page-1-edited.png /tmp/page-2-edited.png \
  -quality 85 -compress JPEG output_edited.pdf
```

---

## 3. Full Pipeline Example

A complete script for cleaning + editing page 1 of a scanned Persian invoice:

```python
import easyocr
from PIL import Image, ImageDraw, ImageFont

# 1. Extract from PDF first (shell):
#    pdftoppm input.pdf /tmp/page -png -r 300

# 2. Clean with ImageMagick (shell):
#    convert /tmp/page-1.png -colorspace Gray -normalize -sharpen 0x1 -despeckle /tmp/page-1-clean.png

# 3. OCR to locate text
reader = easyocr.Reader(['fa'], gpu=False)
results = reader.readtext('/tmp/page-1-clean.png', detail=1)

# 4. Edit
img = Image.open('/tmp/page-1-clean.png').convert('RGB')
draw = ImageDraw.Draw(img)
font = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf', 72)

# Erase and rewrite shop name
draw.rectangle([1200, 160, 2200, 370], fill='white')
draw.text((2150, 210), 'طلاسازی زمرد', fill='black', font=font)

img.save('/tmp/page-1-edited.png', quality=95)

# 5. Convert to PDF (shell):
#    convert /tmp/page-1-edited.png /tmp/page-2-edited.png -quality 85 output.pdf
```

---

## Pitfalls

- **Font availability**: Not all Arabic fonts support Persian-specific characters (گ, چ, پ, ژ). Noto Sans Arabic and IBM Plex Sans Arabic do. Verify with `fc-list :lang=fa`.
- **Font style matching**: For traditional Persian documents (invoices, official letters), **Noto Naskh Arabic** looks more natural than Noto Sans Arabic. Noto Nastaliq Urdu is available for handwritten-style text. Test with a small crop before applying to the whole page.
- **RTL text positioning**: PIL's `text()` starts at the left edge by default. For RTL text, position the x-coordinate near the right edge of where you erased.
- **DPI mismatch**: If the OCR was done at 600 DPI but the font is sized for 300 DPI, text will look tiny. Scale font size proportionally: 72pt @300 DPI = 144pt @600 DPI.
- **Camera-scanned skew**: If the scan is rotated even slightly, white rectangles will be visible. In that case, use a slightly larger erasure area or apply a slight rotation correction first.
- **ImageMagick PDF output**: `convert` with JPEG compression is fine for viewing. For archival quality, use PNG compression instead: `-compress Zip`.
