# Finding the Right state.db on a Remote Hermes Host

When answering "what does Hermes on <host> know about X?", the query target is rarely
`~/.hermes/state.db` on the FIRST path you try. Hosts accumulate multiple Hermes installs,
profiles, and clones — enumerate before extracting.

## Why this matters (observed)

On kubuntux, three separate candidate trees existed:

- `/root/.hermes/` — root-owned, full directory tree (51 entries) including a
  `/root/.hermes/profiles/default/` skeleton with an EMPTY `memories/` dir.
  Its `sessions/` dir was empty too. All plausible-looking; all dead ends for session data.
- `/home/kubuntux/.hermes` — a symlink to `/mnt/storage/kubuntux-home/.hermes`.
  This is the REAL install: `state.db` with real data, populated `memories/`,
  populated `sessions/`, `logs/agent.log*`.
- Deeply nested stale copies (`openclaw-imports/webclaw/web/.next/standalone/.openclaw/workspace/skills/...`)
  — snapshot garbage from an OpenClaw migration. Ignore.

## Discovery sequence

```bash
# 1. Enumerate every .hermes tree and DB candidate in one pass
ls -la /root/.hermes /home/*/.hermes 2>/dev/null
find /root /home -maxdepth 4 \( -name "state.db" -o -name "*.sqlite3" \) 2>/dev/null | grep -v node_modules

# 2. Read BOTH memory stores cheaply before touching SQL
grep -rilE "<keywords>" /root/.hermes/memories/ /root/.hermes/MEMORY.md \
  /home/*/.hermes/memories/ /home/*/.hermes/MEMORY.md 2>/dev/null

# 3. Confirm which state.db actually holds sessions
python3 - <<'EOF'
import sqlite3
con = sqlite3.connect("/home/<user>/.hermes/state.db")
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
assert 'sessions' in tables and 'messages' in tables
print(list(con.execute("SELECT COUNT(*), MIN(datetime(started_at,'unixepoch')) FROM sessions")))
EOF
```

## Extraction pattern that worked

"Does it remember X?" = TWO different questions:

1. **What it SAVED** → grep memory files (step 2 above). Can legitimately return zero hits.
2. **What it DISCUSSED** → query the real `state.db` messages table.

```sql
-- loose keyword sweep (misspellings included)
SELECT role, timestamp, substr(content,1,250)
FROM messages
WHERE content LIKE '%domino%' AND active=1
ORDER BY timestamp DESC LIMIT 40;
```

Then identify which session_id dominates, and pull full slices only from that one:
```sql
SELECT role, timestamp, substr(content,1,3500) FROM messages
WHERE session_id='<id>' AND content LIKE '%<kw>%' AND active=1 ORDER BY timestamp ASC;
```

Real outcome of this exact workflow: grep over both memory stores → nothing.
DB messages sweep → 23 raw hits, filtered to 7 assistant messages inside ONE
long-lived topical session (561 messages total). Everything worth reporting lived
in that single session id. Time-to-answer dropped from minutes to seconds by
scanning compact first, expanding second.

## Pitfalls

- **Filter on `active=1`.** Without it you get superseded/compacted duplicate rows.
- **Timestamps are REAL epoch floats** — render with `datetime.fromtimestamp(ts)`.
- **Skip tool-role hits** (`web_extract`, web_search dumps) unless payload matters;
  conclusions live in assistant/user rows.
- **Heredocs over SSH break** when inner python contains parens/quotes — bash
  re-interprets them. Signature error:
  `eval: line N: syntax error near unexpected token '('`. Correct move: pipe the
  script into `ssh host python3 -` via stdin (subprocess input=script from the
  calling agent's code, or base64-encode the script first).
- **v0.17+ schema note:** `messages.timestamp` (REAL epoch); older builds used
  `messages.created_at`. Check `PRAGMA table_info(messages)` if column-not-found fires.
- **FTS5 trigram index exists (`messages_fts_trigram`) for fast substring search**
  on large DBs; plain LIKE is fine up to a few hundred MB.
- **Memory-store claim ≠ history.** MEMORY.md/USER.md are distilled notes; the
  conversation record is state.db. Check both independently — they can disagree,
  and "not in memory files" does NOT mean "never discussed".
- **Multi-word keyword sweeps via FTS:** an OR-clause over many LIKE terms gets
  slow on big DBs; for quick triage run each keyword as its own LIKE against a
  bounded LIMIT instead of one giant WHERE.