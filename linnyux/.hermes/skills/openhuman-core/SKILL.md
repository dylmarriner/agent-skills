---
name: openhuman-core
description: OpenHuman memory tree and integration engine built directly into Hermes. Obsidian-compatible Markdown wiki memory, full-text search, daily summaries, and auto-fetch framework. Replaces external memory services with local-first SQLite + Markdown vault.
triggers:
  - glob: "**/openhuman/**/*"
  - glob: "**/wiki/**/*.md"
  - semantic: "remember"
  - semantic: "memory tree"
  - semantic: "openhuman"
  - semantic: "save note"
  - semantic: "what do you know"
  - semantic: "recall"
  - semantic: "daily summary"
  - semantic: "memory search"
enabled: true
---

# OpenHuman Core — Hermes Integration

Built into Hermes as a first-class skill. No external services needed.

## Memory System

The memory tree lives at `~/.hermes/openhuman/wiki/` as Obsidian-compatible Markdown:

- `topics/` — structured notes with YAML frontmatter (tags, date, source)
- `daily/` — auto-generated daily summaries from entries
- `people/` — person-specific memory notes
- `projects/` — project-specific knowledge

## Scripts

- `memory_tree.py write <title> <content>` — Save a memory
- `memory_tree.py search <query>` — Full-text search across wiki
- `memory_tree.py daily` — Generate today's daily summary
- `memory_tree.py recent` — List recent memories
- `memory_tree.py stats` — Show memory tree statistics
- `references/linux-desktop-install.md` — OpenHuman Linux desktop install/launcher troubleshooting, including the AppImage vs `.deb` launcher split.

## Usage

When the user asks "remember this" or "what do you know about X":
1. Run `memory_tree.py search <query>` to find relevant memories
2. Use results as context
3. Save new information with `memory_tree.py write`

## Architecture

- Format: Canonical Markdown with YAML frontmatter (OpenHuman-compatible)
- Chunk size: Max 3k tokens before folding into daily summaries
- Compression: TokenJuice-style (truncate to key info before model calls)
- All data local-first in Markdown files + optional SQLite index
- Obsidian-compatible — open the wiki folder in Obsidian to browse/edit


## Integration Engine (118+ Apps)

Script: `scripts/integrations.py` — Social media & 118+ app integrations via Composio.

### Commands
- `integrations.py setup` — Show setup steps
- `integrations.py connect facebook` — OAuth connect Facebook
- `integrations.py connect messenger` — OAuth connect Messenger  
- `integrations.py social feed` — Fetch feed from connected socials
- `integrations.py social post <text>` — Post to connected socials
- `integrations.py list-connections` — Show connected apps

### Quick Start
1. Sign up at https://app.composio.dev (free)
2. Set: `export COMPOSIO_API_KEY=your_key`
3. Run: `composio login --no-browser`
4. Run: `composio add facebook` (opens browser for OAuth)
5. Now you can post/fetch from Facebook via Hermes

Available integrations include: Facebook, Messenger, Instagram, Gmail, Slack, GitHub, Discord, Telegram, WhatsApp, LinkedIn, Twitter, and 100+ more.
