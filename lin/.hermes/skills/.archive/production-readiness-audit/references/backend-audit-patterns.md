# Backend Audit Patterns (Session Examples)

## Blocking Operations in Async FastAPI

**Problem**: `asyncio.create_task(blocking_fn())` where blocking_fn calls
yt-dlp, ffmpeg subprocess, or SMB upload — these block the event loop.

**Fix**:
```python
loop = asyncio.get_event_loop()

# In request handler:
loop.run_in_executor(None, _download_video, url, path, progress_cb)

# In blocking function (runs in thread pool):
def _download_video(url, path, progress_cb):
    # ... blocking yt-dlp code ...
    loop.call_soon_threadsafe(update_progress, pct)

# Each stage (download -> convert -> upload) gets its own executor call
# so errors in one stage don't leak temp files.
```

## SMB Upload via CLI Instead of Python Library

**Problem**: `smbprotocol.Connection` and `pysmb` have deep protocol-timing
requirements and fragile path construction.

**Fix**:
```python
import subprocess
cmd = [
    "smbclient", f"//{server}/{share}",
    "-U", f"{user}%{password}",
    "-c", f"cd {path}; put {local} {dest_name}",
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
```

## CLI with Deferred Imports

**Problem**: `import yt_dlp` at module level makes --help take 3-10s.

**Fix**:
```python
# videosnap (entry point) — thin, only argparse
parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="command")
dl_p = sub.add_parser("dl")
dl_p.add_argument("url")

args = parser.parse_args()

if args.command == "dl":
    import asyncio
    from cli_impl import cmd_dl      # imports yt_dlp, etc. HERE
    sys.exit(asyncio.run(cmd_dl(args)))
```

## SQLite Queue for Single-Server Background Jobs

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','running','completed','failed','cancelled')),
    progress    REAL NOT NULL DEFAULT 0.0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
```

Worker pattern:
```python
async def _worker_loop(self):
    sem = asyncio.Semaphore(self.max_concurrent)
    while self._running:
        pending = db.execute("SELECT * FROM jobs WHERE status='pending'")
        if not pending:
            await asyncio.sleep(2)
            continue
        tasks = [self._process(j, sem) for j in pending]
        await asyncio.gather(*tasks, return_exceptions=True)
```

## SSE EventSource GET Wrapper

```python
# Backend: add GET version alongside POST
@app.post("/api/download")
async def download_video(req: DownloadRequest):
    ...  # existing SSE streaming logic

@app.get("/api/download")
async def download_video_get(url: str = Query(...), quality: str = Query("best")):
    """GET variant for EventSource compatibility."""
    return await download_video(DownloadRequest(url=url, quality=quality))
```

## Parallel Proxy Health Checks

**Problem**: Checking N proxies one-at-a-time with 5s timeout each = 500s for 100.

**Fix**:
```python
results = await asyncio.gather(
    *[self._health_check(p) for p in candidates],
    return_exceptions=True,
)
for proxy, ok in zip(candidates, results):
    if ok is True:
        return proxy
```

## Process Tree Cleanup for Subprocesses

```python
proc = subprocess.Popen(cmd, start_new_session=True)  # process group
# ... later ...
pgid = os.getpgid(proc.pid)
os.killpg(pgid, signal.SIGTERM)       # kills whole tree
proc.wait(timeout=5)
if proc.returncode is None:
    os.killpg(pgid, signal.SIGKILL)    # force if still alive
```

## ANSI Escape Stripping for CLI Parsing

```python
import re
_ANSI_CLEAN = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
def strip_ansi(text: str) -> str:
    return _ANSI_CLEAN.sub("", text)

# Use before float() conversion:
raw = strip_ansi(d.get("_percent_str", "0%")).replace("%", "").strip()
pct = float(raw)
```

## Duplicate Script Consolidation

Before: 5 files with same imports, same class instantiation pattern, same
error handling, just different hardcoded URL lists.

After: 1 unified CLI entry with subcommands.

Grep for consolidation candidates:
```bash
# Find files with similar import structure
for f in *.py; do echo "=== $f ==="; head -15 "$f"; done

# Find hardcoded URL lists (business data in source)
rg 'https?://' backend/*.py | grep -v 'yt-dlp\|player\|example'

# Find SSH/API keys hardcoded
rg 'kubuntux@\|password=\|api_key=' backend/*.py
```
