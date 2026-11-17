# Remote Hermes Session Query

When past session data lives on a different machine's Hermes instance, SSH into that machine and query its `state.db` SQLite database directly. Do NOT try to use `session_search` from the local Hermes — that only searches the local session store.

## Quick Start

```bash
# Find recent sessions
ssh user@host 'python3 -c "
import sqlite3, os
db = os.path.expanduser(\"~/.hermes/state.db\")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute(\"SELECT id, title, started_at FROM sessions ORDER BY started_at DESC LIMIT 10\")
for r in cur.fetchall():
    print(f\"  {r[\\\"id\\\"][:35]:35s} | {str(r[\\\"started_at\\\"])[:19]:20s} | {str(r[\\\"title\\\"])[:60]}\")
conn.close()
"'
```

## Full Workflow

### 1. Discover relevant sessions

Keyword search via SQL LIKE (slow on large DBs but accurate):

```bash
ssh user@host 'python3 -c "
import sqlite3, os
db = os.path.expanduser(\"~/.hermes/state.db\")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

keywords = [\"reverse\", \"unlock\", \"bios\", \"cmos\", \"samsung\"]
for kw in keywords:
    cur.execute(\"SELECT DISTINCT s.id, s.title, s.started_at FROM sessions s JOIN messages m ON s.id=m.session_id WHERE m.content LIKE ? ORDER BY s.started_at DESC LIMIT 5\", (f\"%{kw}%\",))
    rows = cur.fetchall()
    if rows:
        print(f\"== {kw} ==\")
        for r in rows:
            print(f\"  {r[\\\"id\\\"][:30]} | {str(r[\\\"started_at\\\"])[:19]} | {str(r[\\\"title\\\"])[:60]}\")
conn.close()
"'
```

**Note:** On large DBs (500MB+ state.db), `LIKE '%keyword%'` can be slow. For production use, Hermes state.db has FTS5 trigram indexes (`messages_fts_trigram`). Use FTS5 syntax for faster searching:

```bash
ssh user@host 'python3 -c "
import sqlite3, os
db = os.path.expanduser(\"~/.hermes/state.db\")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute(\"SELECT DISTINCT s.id, s.title, s.started_at FROM sessions s JOIN messages m ON s.id=m.session_id WHERE m.rowid IN (SELECT rowid FROM messages_fts_trigram WHERE messages_fts_trigram MATCH ?) ORDER BY s.started_at DESC LIMIT 10\", (quote,))
for r in cur.fetchall():
    print(f\"  {r[\\\"id\\\"][:35]} | {str(r[\\\"started_at\\\"])[:19]} | {str(r[\\\"title\\\"])[:60]}\")
conn.close()
"'
```

### 2. Read session content

```bash
ssh user@host 'python3 -c "
import sqlite3, os
db = os.path.expanduser(\"~/.hermes/state.db\")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

sid = \"SESSION_ID_HERE\"
cur.execute(\"SELECT title FROM sessions WHERE id=?\", (sid,))
s = cur.fetchone()
print(f\"Title: {s[\\\"title\\\"]}\" if s else \"Not found\")

cur.execute(\"SELECT role, content FROM messages WHERE session_id=? ORDER BY id\", (sid,))
msgs = cur.fetchall()

# Show first user message
for m in msgs:
    if m[\"role\"] == \"user\":
        print(f\"First: {(m[\"content\"] or \\\"\\\")[:400]}\")
        break

# Show last N exchanges
for m in msgs[-6:]:
    if m[\"role\"] in (\"user\", \"assistant\"):
        print(f\"[{m[\\\"role\\\"].upper()}] {(m[\"content\"] or \\\"\\\")[:500]}\")

print(f\"Total messages: {len(msgs)}\")
conn.close()
"'
```

### 3. State.db Schema (Hermes v0.17+)

| Table | Purpose |
|-------|---------|
| `sessions` | Session metadata (id, title, started_at, source, model) |
| `messages` | All messages (session_id, role, content, tool_calls, created_at) |
| `messages_fts` | FTS5 full-text index on content |
| `messages_fts_trigram` | FTS5 trigram index (substring matching) |

Columns in `sessions`: `id TEXT PK`, `source TEXT`, `user_id TEXT`, `model TEXT`, `model_config TEXT`, `system_prompt TEXT`, `parent_session_id TEXT`, `started_at REAL`, `title TEXT`, `updated_at REAL`

Columns in `messages`: `id INTEGER PK`, `session_id TEXT REFERENCES sessions`, `role TEXT`, `content TEXT`, `tool_call_id TEXT`, `tool_calls TEXT`, `created_at REAL`

### Pitfalls

- **`started_at` is a Unix timestamp (REAL), not a string** — format it with `str(value)[:19]` or `datetime.fromtimestamp(value).isoformat()`
- **Large DB performance** — `state.db` can be 500MB+. `LIKE '%keyword%'` does a full table scan. Prefer FTS5 trigram search for speed.
- **JSON session files may coexist** — `~/.hermes/sessions/*.json` files are an older format used before the SQLite backend. Check both if searching for historical sessions.
- **FTS5 trigram quotes** — pass search terms as parameterized queries, not string interpolation, to avoid SQL injection. FTS5 MATCH syntax uses double quotes: `"\"keyword\""`.
- **No `session_search` equivalent** — the remote machine's Hermes has its own session search command. If SSH is available, `ssh host 'hermes session search <query>'` is the simplest approach when it works.

## When to Use This

- User references a past conversation on another machine
- You need to understand context of work done on a different Hermes instance
- Debugging a cross-machine issue and need to see both sides of a conversation
- User says "remember when we talked about X on lin" — check lin's state.db, not your own
