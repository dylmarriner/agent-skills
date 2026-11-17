---
name: message-screenshot-editor
description: Edit and redact existing message screenshots — blur/censor names, faces, phone numbers, replace text, draw colored rectangles over sensitive info, and crop. Uses ImageMagick (convert) and Python Pillow. Trigger when the user asks to censor, redact, edit, or modify a screenshot of text messages, chats, SMS, iMessage, WhatsApp, or any conversation screenshot.
compatibility: Requires ImageMagick (convert) and Python 3 + Pillow. Tested on Ubuntu 24.04.
---

# Message Screenshot Editor

A skill for editing message/conversation screenshots. Covers redaction, censoring, text replacement, and cropping.

## When to Use This Skill

Use this skill when the user wants to:
- Blur or pixelate names, phone numbers, profile pictures in a screenshot
- Draw colored rectangles/censor bars over sensitive text
- Replace text in a message bubble (change names, numbers, or message content)
- Crop or trim a screenshot
- Add or modify timestamps
- Clean up a screenshot for sharing publicly

## Prerequisites

- **ImageMagick 6** available as `convert` (Ubuntu: `sudo apt install imagemagick`)
- **Python 3 + Pillow**: `pip3 install --break-system-packages Pillow`
- Verify: `convert --version` and `python3 -c "from PIL import Image; print('ok')"`

## Core Operations

### 1. Blur / Pixelate a Region (ImageMagick)

Blur a rectangular area by specifying x,y coordinates and width,height:

```bash
# Apply Gaussian blur over a region (good for names, avatars)
convert input.png \
  -region 120x30+50+80 -blur 0x12 \
  output.png

# Pixelate (mosaic effect) — scale down then up
convert input.png \
  -region 120x30+50+80 -scale 10% -scale 1000% \
  output.png
```

To identify coordinates: open image with any viewer or use `identify` to get dimensions, then estimate based on visual layout. For precise pixel-perfect coordinates, use the coordinate-finder script (see reference).

### 2. Draw Censor Bars (ImageMagick)

Solid color rectangles over sensitive areas:

```bash
# Draw a black bar over a region
convert input.png \
  -fill black -draw "rectangle 50,80 170,110" \
  output.png

# Draw a colored highlight box
convert input.png \
  -fill "#FFEB3B" -fill-opacity 0.4 \
  -draw "rectangle 50,80 170,110" \
  output.png
```

Rectangle format: `rectangle X1,Y1 X2,Y2` where X1,Y1 is top-left and X2,Y2 is bottom-right.

### 3. Replace Text in a Message (Python + Pillow)

For changing message content, names, or numbers — more precise than ImageMagick:

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.open("input.png")
draw = ImageDraw.Draw(img)

# First, cover the old text with a background-colored rectangle
# (sample the background color from the image first)
# Then write new text

# Example: draw white rect over old text, then write new
bg_color = img.getpixel((100, 100))  # sample background
draw.rectangle([50, 80, 400, 110], fill=bg_color)

# Write new text (find fonts in /usr/share/fonts/)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
draw.text((50, 80), "New message text", fill="black", font=font)

img.save("output.png")
```

### 4. Crop (ImageMagick)

```bash
# Crop to a specific region WxH+X+Y
convert input.png -crop 400x800+0+0 output.png

# Crop to remove top notification bar (e.g. remove first 80px)
convert input.png -crop 100%x92%+0+80 output.png
```

### 5. Full Pipeline: Censor + Replace Text + Crop

```python
#!/usr/bin/env python3
"""Edit a message screenshot: censor regions, replace text, crop."""
import sys, subprocess
from PIL import Image, ImageDraw, ImageFont

input_path = sys.argv[1]
output_path = sys.argv[2]

# Step 1: Blur sensitive areas with ImageMagick
regions = [
    ("120x30+50+80",  "blur 0x12"),   # contact name
    ("100x100+300+50", "scale 5% -scale 2000%"),  # profile pic
]
for region, effect in regions:
    subprocess.run([
        "convert", input_path,
        "-region", region, *effect.split(),
        output_path  # overwrite each step
    ], check=True)
    input_path = output_path  # chain

# Step 2: Overlay text via Pillow
img = Image.open(output_path)
draw = ImageDraw.Draw(img)
# Sample background color near old text
old_text_region = (80, 200, 360, 230)
sample_x = old_text_region[0] + 5
sample_y = old_text_region[1] + 5
bg = img.getpixel((sample_x, sample_y))
draw.rectangle(old_text_region, fill=bg)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
draw.text((old_text_region[0] + 2, old_text_region[1] + 2),
          "REDACTED", fill="black", font=font)

# Step 3: Crop
img = img.crop((0, 80, img.width, img.height))  # remove status bar
img.save(output_path)
print(f"Done: {output_path}")
```

## Coordinate Finder

To find exact pixel coordinates for regions you want to censor/edit:

```python
#!/usr/bin/env python3
"""Click on an image to get pixel coordinates."""
from PIL import Image
import tkinter as tk
from tkinter import filedialog

# Use identify first to get dimensions
# Then open in an image viewer that shows cursor coordinates
# Or use this crude approach:
img = Image.open("screenshot.png")
w, h = img.size
print(f"Image size: {w}x{h}")

# Better: use ImageMagick to show guide grid
# convert screenshot.png -font Courier -pointsize 12 \
#   -fill "rgba(0,0,0,0.5)" -draw "line 100,0 100,h line 200,0 200,h line 300,0 300,h ..." \
#   guide.png
```

## Making It Look Human (Critical)

This is the most important section. Poorly-done edits are instantly recognizable as fakes.

### Font Matching (Most Common Tell)

| Platform | Font | Install |
|----------|------|---------|
| **iOS** | SF Pro Display / SF Pro Text | `wget https://devimages-cdn.apple.com/design/resources/download/SF-Pro.dmg` (extract via 7z) |
| **Android** | Roboto | `sudo apt install fonts-roboto` |
| **Fallback** | DejaVu Sans Condensed | `sudo apt install fonts-dejavu-core` |

For quick human-quality results, use **Roboto** (apt-installable, very similar to SF Pro):
```bash
sudo apt install -y fonts-roboto fonts-noto-color-emoji
```

### Color Matching

Message bubble colors are platform-specific. Don't guess — sample from the image:

```
iOS received (iMessage):   #E5E5EA   (gray bubble)
iOS sent (iMessage):       #34C759   (green bubble)
iOS sent (iMessage blue):  #007AFF   → #007AFF with white text
Android received:          #E8E8E8   (gray bubble)
Android sent:              #C8E6C9   → get exact from image
```

When replacing text:
1. Sample the bubble fill color from an UNDAMAGED part of the same bubble
2. Paint over the old text with that exact color (not white!)
3. Write new text with proper padding (6-8px left, 3-5px top)

### Proper Padding & Layout

- **Left padding in bubbles**: text starts ~8px from left edge, ~4px from top
- **Bubble margins**: received bubbles have 12-16px left margin, sent have 12-16px right margin
- **Bubble-to-bubble spacing**: ~4-6px vertical gap between consecutive messages
- **Text color**: received = black (#000), sent (iMessage green/blue) = white (#FFF), sent (Android) = black (#000)

### Multi-Line Text

When replacing multi-line text:
```python
lines = text.split("\\n")
for i, line in enumerate(lines):
    draw.text((x + 8, y + 4 + i * line_height), line, ...)
```
Calculate `line_height` as `font_size * 1.3`.

### Censor Style: Pixelate, Not Solid Bars

Solid black rectangles scream "censored." For human-looking redaction:

- **Pixelation** (best): `-scale 5% -scale 2000%` — looks like a real mosaic blur
- **Gaussian blur** (good): `-blur 0x15` — subtle, looks like image compression artifact
- **Solid bars** (only when user explicitly asks for them)

### Timestamp Realism

Timestamps use a specific format per platform:
- iOS: "Today 2:30 PM" or "Yesterday 9:15 AM" or "Mon, Jan 5, 8:00 PM"
- Android: "2:30 PM" or "Jan 5, 2:30 PM"
- Font size: usually 11-12px
- Color: #8E8E93 (iOS gray) or #808080
- Centered between bubbles or right-aligned

## Pitfalls

- **ImageMagick 6 vs 7**: On Ubuntu 24.04, use `convert` not `magick`. ImageMagick 6 syntax differs slightly from v7.
- **Font availability**: Message screenshots use system-specific fonts (SF Pro on iOS, Roboto on Android). Install Roboto for best results: `sudo apt install fonts-roboto`.
- **Background color matching**: When covering old text, sample the exact background color from the image — don't assume pure white. Message bubble backgrounds vary (light gray for others, blue/green for sent messages).
- **Region coordinates**: Coordinates are relative to the image origin (0,0) at top-left. Use `identify` to check image dimensions first.
- **File format**: Work with PNG for lossless editing. Save intermediate steps as PNG. Export to JPG only at the end if needed.
- **Text alignment**: Message text is usually left-aligned with padding. Match the padding and line height for realistic results.
- **Shadow detection**: iOS bubbles have a subtle drop shadow. Don't paint over the shadow — keep zone tight around text only.
- **Emoji**: Real messages contain emoji. If you're replacing text, consider whether emoji should be present. Noto Color Emoji can render them.
- **Message status labels**: iOS shows "Delivered", "Read", "Sent" in small gray text below bubbles. Don't forget these if they exist.
- **Group chat names**: Group chats show multiple contact names/colors. Preserve the color-coding scheme.

## Common Workflows

### Quick Censor (just blur names)
```bash
# Blur top name (adjust coords based on image)
convert input.png \
  -region 200x40+60+30 -blur 0x15 \
  -region 200x40+60+70 -blur 0x15 \
  output.png
```

### Quick Censor (pixelate profile picture)
```bash
convert input.png \
  -region 60x60+20+20 -scale 10% -scale 1000% \
  output.png
```

### Batch censor multiple screenshots
```bash
for img in screenshots/*.png; do
  convert "$img" -region "200x40+60+30" -blur "0x12" "censored_$(basename "$img")"
done
```
