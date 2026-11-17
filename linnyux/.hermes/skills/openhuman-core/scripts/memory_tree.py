#!/usr/bin/env python3
"""OpenHuman Memory Tree - Obsidian-compatible Markdown wiki memory system.
Stores memories as canonical Markdown files with frontmatter.
Compatible format with OpenHuman desktop app.
"""
import os
import json
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

WIKI_DIR = Path(os.path.expanduser("~/.hermes/openhuman/wiki"))
SOURCES_DIR = Path(os.path.expanduser("~/.hermes/openhuman/sources"))
DB_PATH = Path(os.path.expanduser("~/.hermes/openhuman/memory.db"))

for d in [WIKI_DIR, SOURCES_DIR, WIKI_DIR / "daily", WIKI_DIR / "topics", WIKI_DIR / "people", WIKI_DIR / "projects"]:
    d.mkdir(parents=True, exist_ok=True)

def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', text.lower().strip()).strip('-')[:80]

def write_note(topic: str, content: str, tags: list[str] = None, source: str = "hermes"):
    """Write a memory note as Obsidian-compatible Markdown."""
    tags = tags or []
    today = date.today().isoformat()
    slug = slugify(topic)
    path = WIKI_DIR / "topics" / f"{slug}.md"
    frontmatter = {
        "title": topic,
        "date": today,
        "tags": tags,
        "source": source,
        "type": "memory"
    }
    fm = "---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n\n"
    path.write_text(fm + content + "\n")
    return str(path)

def search_memory(query: str, limit: int = 10) -> list[dict]:
    """Full-text search across memory wiki."""
    results = []
    for f in sorted(WIKI_DIR.rglob("*.md")):
        try:
            text = f.read_text()
            if query.lower() in text.lower():
                # Extract frontmatter
                parts = text.split("---", 2)
                content = parts[2] if len(parts) > 2 else text
                # Get first meaningful line
                preview = "\n".join(line for line in content.split("\n") if line.strip() and not line.startswith("---"))[:300]
                results.append({"path": str(f.relative_to(WIKI_DIR)), "preview": preview.strip(), "score": text.lower().count(query.lower())})
        except:
            pass
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

def generate_daily_summary() -> str:
    """Fold today's memories into a daily summary."""
    today = date.today().isoformat()
    entries = []
    for f in sorted(WIKI_DIR.rglob("*.md")):
        try:
            text = f.read_text()
            if today in text:
                parts = text.split("---", 2)
                content = parts[2] if len(parts) > 2 else text
                entries.append({"file": str(f.relative_to(WIKI_DIR)), "content": content[:500]})
        except:
            pass
    if not entries:
        return "No memories recorded today."
    summary = f"# Daily Summary - {today}\n\n## Entries ({len(entries)})\n\n"
    for e in entries:
        summary += f"### From: {e['file']}\n{e['content']}\n\n---\n\n"
    sum_path = WIKI_DIR / "daily" / f"{today}.md"
    sum_path.write_text(summary)
    return str(sum_path)

def get_recent_memories(days: int = 7) -> list[dict]:
    """Get recent memories."""
    results = []
    for f in sorted(WIKI_DIR.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
        text = f.read_text()
        parts = text.split("---", 2)
        content = parts[2][:200] if len(parts) > 2 else text[:200]
        results.append({"path": str(f.relative_to(WIKI_DIR)), "snippet": content.strip(), "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()})
    return results[:20]

def memory_stats() -> dict:
    """Get memory tree statistics."""
    total = len(list(WIKI_DIR.rglob("*.md")))
    topics = len(list((WIKI_DIR / "topics").glob("*.md")))
    daily = len(list((WIKI_DIR / "daily").glob("*.md")))
    return {"total_notes": total, "topic_notes": topics, "daily_summaries": daily, "wiki_path": str(WIKI_DIR)}

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "write":
        topic = sys.argv[2]
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        print(write_note(topic, content))
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        for r in search_memory(query):
            print(f"[{r['score']}] {r['path']}: {r['preview'][:80]}")
    elif cmd == "daily":
        print(generate_daily_summary())
    elif cmd == "recent":
        for r in get_recent_memories():
            print(f"{r['modified']} | {r['path']}: {r['snippet'][:80]}")
    elif cmd == "stats":
        s = memory_stats()
        for k, v in s.items():
            print(f"{k}: {v}")