---
name: session-logs
description: Search and analyze Hermes Agent session history across SQLite state.db and JSON session files. Use when a user references past conversations, prior downloads, or historical context that session_search alone can't find.
metadata:
  tags: session-history, sqlite, state-db, session-search, historical-context
---

# Session Logs (Hermes Agent)

Search your complete conversation history. Use this when a user references older sessions, past downloads, or historical context that the `session_search` tool doesn't return — or when you need to search beyond the tool's indexed scope.

## Trigger

- User asks "remember when we did X" and session_search returns nothing
- User says "you haven't looked far back enough" or similar frustration
- Need to find URLs, file paths, or specific commands from weeks ago
- Need exhaustive search across all platforms (CLI + Telegram)

## Storage Locations

Hermes Agent stores session data in two places:

### 1. SQLite Database (primary, full-text searchable)
**File:** `~/.hermes/state.db`

**Tables:**
- `sessions` — 500+ sessions with metadata (id, source, title, started_at, message_count, tokens, cost)
- `messages` — All messages across all sessions (role, content, tool_calls, timestamp)
- `messages_fts` — FTS5 full-text search index on messages content

**Sources:** `cli`, `telegram`, `discord`, etc.

### 2. JSON Session Files (full transcripts)
**Directory:** `~/.hermes/sessions/`

**Format:**
- `session_<YYYYMMDD_HHMMSS>_<hash>.json` — full session transcript with all messages and tool calls
- `request_dump_*.json` — older request dumps (pre-date session format)

## Query Patterns

### Full-text search (fastest, best for keywords)

```bash
sqlite3 ~/.hermes/state.db "
SELECT s.id, s.source, s.title, s.started_at, m.content
FROM messages_fts fts
JOIN messages m ON m.id = fts.rowid
JOIN sessions s ON s.id = m.session_id
WHERE messages_fts MATCH 'keyword'
AND m.role = 'user'
ORDER BY m.timestamp DESC
LIMIT 20;
"
```

### Search for specific URLs from all sessions

```bash
sqlite3 ~/.hermes/state.db "
SELECT s.source, m.content FROM messages m
JOIN sessions s ON m.session_id = s.id
WHERE m.role = 'user'
AND m.content LIKE '%example.com%'
ORDER BY m.timestamp DESC;
"
```

### Count sessions by platform

```bash
sqlite3 ~/.hermes/state.db "
SELECT source, COUNT(*) FROM sessions GROUP BY source;
"
```

### List all sessions with dates and message counts

```bash
sqlite3 ~/.hermes/state.db "
SELECT id, source, title, datetime(started_at, 'unixepoch') as date, message_count
FROM sessions
ORDER BY started_at DESC
LIMIT 30;
"
```

### Search session JSON files for a keyword (good for complex queries)

```bash
cd ~/.hermes/sessions && grep -l -i "keyword\|phrase" session_2026*.json
```

### Check creation times of files on disk to correlate with sessions

```bash
# When was a file created? (useful for downloads)
stat --format='%W|%n' /mnt/pivideos/videos/*.mp4 | sort -t'|' -k1 -n | tail -20
```

## Cross-Machine Search (SSH Jump Host Pattern)

When the user says you "haven't looked far back enough" and you've already exhausted local session data, check for other machines they use. The search may need to span multiple hosts.

### Discovery pattern

```bash
# 1. Check which machines in their Tailscale network are reachable
ssh -o ConnectTimeout=5 user@<tailscale_ip> "echo OK" 2>&1

# 2. If Tailscale policy blocks direct SSH ("tailnet policy does not permit"),
# find a jump host that has SSH access to the blocked machine
ssh jump-host "ssh blocked-host 'echo OK'"

# 3. Once connected, search for agent config/sessions
ssh user@host "
  # Hermes
  ls ~/.hermes/state.db 2>/dev/null && sqlite3 ~/.hermes/state.db \"
    SELECT COUNT(*) FROM sessions;
    SELECT source, COUNT(*) FROM sessions GROUP BY source;
    SELECT content FROM messages WHERE content LIKE '%keyword%' AND role='user' LIMIT 10;
  \"
  # OpenClaw
  ls ~/.openclaw/ 2>/dev/null && find ~/.openclaw/ -name '*.json' -exec grep -l 'keyword' {} \;
  # Other AI agents
  for d in .claude .codex .copilot .continue .aider .windsurf .gemini; do
    [ -d ~/\$d ] && echo \"\$d present\"
  done
"
```

### Check file creation times vs. session dates

Use `stat` birth time to correlate files on disk with session IDs:

```bash
stat --format='%W|%n' /mnt/pivideos/videos/*.mp4 | sort -t'|' -k1 -n
```
Then convert the Unix epoch to a session date:

```bash
date -d @<epoch>
```

### Search session JSON files with grep

For complex searches across raw transcripts:

```bash
cd ~/.hermes/sessions
grep -l -i "keyword1\|keyword2\|keyword3" session_2026*.json
grep -l -i "keyword" request_dump_2026*.json
```

### Platform-specific session isolation

The state.db `sessions.source` column identifies where a session originated:

```bash
sqlite3 ~/.hermes/state.db "
  SELECT source, COUNT(*) as count, MAX(datetime(started_at, 'unixepoch')) as latest
  FROM sessions GROUP BY source ORDER BY count DESC;
"
```

Combine with content search:

```bash
sqlite3 ~/.hermes/state.db "
  SELECT s.source, s.title, m.content FROM messages m
  JOIN sessions s ON m.session_id = s.id
  WHERE s.source = 'telegram' -- or 'cli' or 'discord'
  AND m.content LIKE '%keyword%'
  ORDER BY m.timestamp DESC;
"
```

## Pitfalls

- **session_search tool is limited** — it only indexes session summaries, not full message content. For exhaustive searches (across all 500+ sessions), query state.db directly.
- **FTS5 requires exact words** — partial-word matches need LIKE or trigram search. Use `LIKE '%partial%'` for URL fragments.
- **JSON files are the raw transcripts** — they contain tool_call details that the SQLite messages table may truncate. Use JSON for full context, SQLite for fast search.
- **Old sessions may be in request_dump_*.json format** — these predate the `session_*.json` naming convention but contain valuable history.
- **Telegram sessions are mixed with CLI** — use `s.source = 'telegram'` filter to isolate platform.
- **Don't trust partial session summaries** — a summary may say something failed, but the actual session transcript may show it was retried and succeeded. Always verify download outcomes by checking the file system and the full session transcript, not just the summary.
