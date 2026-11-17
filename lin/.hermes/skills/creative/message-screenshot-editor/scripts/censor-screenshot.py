#!/usr/bin/env python3
"""
Censor a message screenshot — one command, multiple operations.

Usage:
  python3 censor-screenshot.py input.png output.png \
    --censor 50,80,200,120  --censor 300,50,400,90 \
    --blur 20,20,80,80 \
    --pixelate 50,80,200,120 \
    --replace "100,150,350,180:New text here"

Options:
  --censor X1,Y1,X2,Y2       Draw black rectangle over area (repeatable)
  --blur X1,Y1,X2,Y2         Gaussian blur over area (repeatable)
  --pixelate X1,Y1,X2,Y2     Pixelate/mosaic over area (repeatable)
  --replace "X1,Y1,X2,Y2:Text"  Replace text in a region (repeatable)
  --font-size N              Font size for --replace (default: 16)
  --crop "WxH+X+Y"          Crop output (ImageMagick format)
  --platform ios|android     Platform presets for colors/padding (default: ios)

For realistic results:
  - Prefer --pixelate over --censor (pixelation looks like a real mosaic blur)
  - Sample the bubble fill color from the image before --replace
  - Use --blur for subtle redaction (looks like image compression artifact)
  - Install Roboto font for Android-style: sudo apt install fonts-roboto
"""
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

PLATFORM = {
    "ios": {
        "bubble_received": None,
        "bubble_sent": None,
        "text_received": "black",
        "text_sent": "white",
        "time_color": "#8E8E93",
        "time_size": 11,
        "font": "DejaVuSans.ttf",
    },
    "android": {
        "bubble_received": None,
        "bubble_sent": None,
        "text_received": "black",
        "text_sent": "black",
        "time_color": "#808080",
        "time_size": 12,
        "font": "Roboto-Regular.ttf",
    },
}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def resolve_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def parse_rect(s):
    parts = [int(x) for x in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Need 4 ints (x1,y1,x2,y2), got: {s}")
    return tuple(parts)

def parse_replace(s):
    m = re.match(r"(\d+,\d+,\d+,\d+):(.+)", s)
    if not m:
        raise ValueError(f"Format: 'x1,y1,x2,y2:text', got: {s}")
    return parse_rect(m.group(1)), m.group(2)

def sample_bubble_color(img, rect, margin=4):
    x1, y1, x2, y2 = rect
    samples = [
        (x1 + margin, y1 + margin),
        (x2 - margin, y1 + margin),
        ((x1 + x2) // 2, (y1 + y2) // 2),
    ]
    colors = []
    for sx, sy in samples:
        try:
            colors.append(img.getpixel((sx, sy)))
        except IndexError:
            pass
    if not colors:
        return None
    return tuple(sum(c) // len(c) for c in zip(*colors))

def main():
    args = sys.argv[1:]
    if len(args) < 2 or "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    input_path, output_path = args[0], args[1]
    censors = []
    blurs = []
    pixelates = []
    replaces = []
    font_size = 16
    crop = None
    platform = "ios"
    i = 2
    while i < len(args):
        if args[i] == "--censor" and i + 1 < len(args):
            censors.append(parse_rect(args[i + 1]))
            i += 2
        elif args[i] == "--blur" and i + 1 < len(args):
            blurs.append(parse_rect(args[i + 1]))
            i += 2
        elif args[i] == "--pixelate" and i + 1 < len(args):
            pixelates.append(parse_rect(args[i + 1]))
            i += 2
        elif args[i] == "--replace" and i + 1 < len(args):
            replaces.append(parse_replace(args[i + 1]))
            i += 2
        elif args[i] == "--font-size" and i + 1 < len(args):
            font_size = int(args[i + 1])
            i += 2
        elif args[i] == "--crop" and i + 1 < len(args):
            crop = args[i + 1]
            i += 2
        elif args[i] == "--platform" and i + 1 < len(args):
            val = args[i + 1].lower()
            if val not in PLATFORM:
                print(f"Unknown platform: {val}. Use 'ios' or 'android'.", file=sys.stderr)
                sys.exit(1)
            platform = val
            i += 2
        else:
            print(f"Unknown option: {args[i]}", file=sys.stderr)
            sys.exit(1)

    current = input_path
    temp_files = []

    for x1, y1, x2, y2 in censors:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_files.append(tmp.name)
        subprocess.run([
            "convert", current, "-fill", "#1a1a1a",
            "-draw", f"rectangle {x1},{y1} {x2},{y2}", tmp.name
        ], check=True)
        current = tmp.name

    for x1, y1, x2, y2 in blurs:
        w, h = x2 - x1, y2 - y1
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_files.append(tmp.name)
        subprocess.run([
            "convert", current, "-region", f"{w}x{h}+{x1}+{y1}",
            "-blur", "0x15", tmp.name
        ], check=True)
        current = tmp.name

    for x1, y1, x2, y2 in pixelates:
        w, h = x2 - x1, y2 - y1
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_files.append(tmp.name)
        subprocess.run([
            "convert", current, "-region", f"{w}x{h}+{x1}+{y1}",
            "-scale", "6%", "-scale", "1667%", tmp.name
        ], check=True)
        current = tmp.name

    if replaces:
        img = Image.open(current)
        draw = ImageDraw.Draw(img)
        font_path = resolve_font()
        if not font_path:
            print("WARNING: No font found, using default.", file=sys.stderr)
            font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(font_path, font_size)

        for (x1, y1, x2, y2), text in replaces:
            bg_color = sample_bubble_color(img, (x1, y1, x2, y2))
            if bg_color is None:
                bg_color = img.getpixel((min(x1 + 2, x2 - 1), min(y1 + 2, y2 - 1)))
            draw.rectangle([x1, y1, x2, y2], fill=bg_color)
            padding_x = 8 if platform == "ios" else 10
            padding_y = 4 if platform == "ios" else 3
            text_color = "black"
            r, g, b = bg_color[:3]
            if platform == "ios" and g > 150 and r < 100 or platform == "ios" and b > 200 and r < 100 and g < 150:
                text_color = "white"
            line_height = int(font_size * 1.35)
            for i, line in enumerate(text.split("\n")):
                draw.text(
                    (x1 + padding_x, y1 + padding_y + i * line_height),
                    line, fill=text_color, font=font
                )

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_files.append(tmp.name)
        img.save(tmp.name)
        current = tmp.name

    if crop:
        subprocess.run(["convert", current, "-crop", crop, output_path], check=True)
    else:
        subprocess.run(["convert", current, output_path], check=True)

    for f in temp_files:
        try:
            os.unlink(f)
        except OSError:
            pass

    print(f"Saved: {output_path}")
    print(f"  Censor bars: {len(censors)} | Blurs: {len(blurs)} | Pixelates: {len(pixelates)} | Text replaces: {len(replaces)}")
    print(f"  Platform: {platform}")
    if crop:
        print(f"  Cropped: {crop}")

if __name__ == "__main__":
    main()
