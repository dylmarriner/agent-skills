# OpenHuman Core Architecture

## Memory Flow

```
User says "remember X"
  → Agent calls memory_tree.py write
  → Saved as Markdown with frontmatter at ~/.hermes/openhuman/wiki/topics/<slug>.md
  → Available for full-text search immediately

User asks "what do you know about Y"
  → Agent calls memory_tree.py search <Y>
  → Returns ranked results from all wiki files
  → Used as context for response

End of day
  → Agent calls memory_tree.py daily
  → Folds all day's entries into daily summary at wiki/daily/<date>.md
```

## Integration Points

The OpenHuman memory tree is accessible from:
- **Python scripts**: `python3 scripts/memory_tree.py <cmd>`
- **Direct file access**: All Markdown files at `~/.hermes/openhuman/wiki/`
- **Obsidian**: Open the wiki folder in Obsidian for manual browsing

## Auto-Fetch Framework (future)

The skill structure supports adding auto-fetch plugins:
1. Create a script in `scripts/sources/` that fetches from a service
2. Register it in a cron-like scheduler
3. Each fetch writes to the wiki using memory_tree.py

## Compatible Format

The wiki format is compatible with OpenHuman desktop app:
- YAML frontmatter with title, date, tags, source
- Max 3k tokens per note before folding
- Daily summaries from individual entries
