#!/usr/bin/env python3
"""
Template: rename exported JSON items by a semantic field (title/name/label).

Adapt for your data: change INPUT, KEY_FIELD, and the slug-to-UUID mapping.
"""
import json
import re
from pathlib import Path

INPUT = Path("data.json")
OUTDIR = Path("export")
KEY_FIELD = "title"  # change to "name" or "label" as needed
FALLBACK = "untitled"


def slugify(text: str, max_len: int = 60) -> str:
    """Turn text into a clean filesystem-safe slug."""
    if not text or text.strip() == "":
        return FALLBACK
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "-").strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:max_len].rstrip("-")[:max_len] or FALLBACK


def main():
    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found")
        return

    print(f"Reading {INPUT.name} ...")
    with open(INPUT, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Found {len(items)} items")
    renamed = 0

    for item in items:
        item_id = item.get("id", "")
        title = item.get(KEY_FIELD, "").strip() or FALLBACK
        slug = slugify(title)
        uuid_short = item_id[:8] if item_id else ""
        new_stem = f"{slug}__{uuid_short}" if uuid_short else slug

        for ext in (".json", ".md", ".txt"):
            old = OUTDIR / f"{item_id}{ext}" if item_id else None
            if old and old.exists():
                new = OUTDIR / f"{new_stem}{ext}"
                if old != new:
                    old.rename(new)
                    renamed += 1

    print(f"Renamed {renamed} files in {OUTDIR}")


if __name__ == "__main__":
    main()
