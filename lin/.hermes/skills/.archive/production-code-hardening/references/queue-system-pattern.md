# Persistent Async Queue Pattern — Reference

A reusable pattern for building a SQLite-backed persistent async queue with
background worker, CLI commands, and REST API endpoints. Used in production
for the VideoSnap download queue.

## Architecture

```
CLI  ──→  Queue (SQLite)  ──→  Worker (asyncio)  ──→  Job execution
            ↕                                ↕
API ──→                              API polls status
```

## Components

### 1. Queue Manager (`queue.py`)

A SQLite-backed job store with state machine. Singleton pattern for API/CLI sharing.

**States:** `pending → running → completed / failed → cancelled`

```python
# ── Core API surface ──
class DownloadQueue:
    def add(self, url: str, quality: str = "best") -> dict: ...
    def get(self, job_id: str) -> dict | None: ...
    def list(self, status: str | None = None) -> list[dict]: ...
    def cancel(self, job_id: str) -> bool: ...
    def retry(self, job_id: str) -> bool: ...
    def clear_completed(self) -> int: ...
    def stats(self) -> dict: ...
    async def start_worker(self) -> None: ...
    async def stop_worker(self) -> None: ...
```

**Key SQLite patterns:**

```python
import sqlite3

def _db() -> tuple:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row          # dict-like rows
    conn.execute("PRAGMA journal_mode=WAL") # concurrent reads
    conn.execute("PRAGMA busy_timeout=5000")# retry on lock
    return conn, conn.cursor()
```

- Use `CHECK(status IN (...))` constraint — the DB enforces valid states, not just Python
- WAL mode allows concurrent reads while the worker writes
- Index on `status` for fast pending-job polling
- `row_factory = sqlite3.Row` so rows are dict-like (`dict(row)`)
- Timestamps stored as ISO 8601 strings (timezone-aware)

### 2. Background Worker

An asyncio task that polls for pending jobs and processes them with a
concurrency limit via `asyncio.Semaphore`:

```python
async def _worker_loop(self) -> None:
    sem = asyncio.Semaphore(self.max_concurrent)
    while self._running:
        conn, cur = _db()
        cur.execute(
            "SELECT * FROM jobs WHERE status='pending' ORDER BY created_at ASC LIMIT ?",
            (self.max_concurrent,),
        )
        pending = [dict(r) for r in cur.fetchall()]
        conn.close()
        if not pending:
            await asyncio.sleep(2)
            continue
        tasks = [self._process_job(j, sem) for j in pending]
        await asyncio.gather(*tasks, return_exceptions=True)
```

**Critical patterns:**
- **Work-stealing poll** — worker grabs up to `max_concurrent` jobs and processes them concurrently
- **Semaphore-limited** — prevents too many concurrent executions against external services
- **Exception-safe** — `return_exceptions=True` so one job failure doesn't block others
- **Clean lifecycle** — `start_worker()` / `stop_worker()` wrapping an asyncio.Task that cancels cleanly
- **Job isolation** — each job creates its own ProxyManager, BrowserBypass, and Downloader singletons

### 3. Progress Updates

The worker writes progress back to SQLite as the job runs:

```python
async for event in dl.download(url, job_dir, quality, proxy, cookie_file, headers):
    if event["type"] == "progress":
        self.update(jid, progress=event["percent"], speed=event.get("speed"),
                    eta=event.get("eta"), size=event.get("downloaded"))
    elif event["type"] == "complete":
        self.update(jid, status="completed", progress=100.0, filename=event["filename"], ...)
    elif event["type"] == "error":
        self.update(jid, status="failed", error=event.get("message"), ...)
```

### 4. CLI Integration

Deferred-import pattern so `--help` is fast:

```python
# Entry point — argparse only, no heavy imports
def main() -> int:
    args = _parser().parse_args()

    if args.command == "dl":
        from cli_impl import cmd_dl      # deferred
        return asyncio.run(cmd_dl(args))

    if args.command == "queue":
        from queue import get_queue      # deferred
        ...
```

### 5. API Integration

FastAPI lifespan hooks start/stop the worker:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    q = get_queue()
    await q.start_worker()
    yield
    await q.stop_worker()
```

API endpoints mirror the queue manager methods:

```python
@app.get("/api/queues")
async def queue_list(status: Optional[str] = Query(None)):
    return get_queue().list(status=status)

@app.post("/api/queues")
async def queue_add(req: DownloadRequest):
    return get_queue().add(req.url, quality=req.quality)

@app.post("/api/queues/{job_id}/cancel")
async def queue_cancel(job_id: str):
    if get_queue().cancel(job_id):
        return {"status": "cancelled", "id": job_id}
    raise HTTPException(status_code=400, detail="Cannot cancel")
```

## Pitfalls

- **SQlite single-writer**: Only one writer at a time. WAL mode helps readers but
  writes serialize. For high-throughput queues, switch to PostgreSQL + asyncpg.
- **Worker restart**: If the API server restarts, the worker resumes with the DB
  state — any jobs stuck in "running" are lost. Mitigate by having the worker
  reset stale "running" jobs to "pending" on startup (or use a heartbeat column).
- **Polling interval**: 2-second poll is fine for a local queue with < 100 jobs/day.
  For higher throughput, use `asyncio.Condition` or a notification channel.
- **Semaphore starvation**: If all `max_concurrent` slots are filled with long-running
  jobs, no new jobs can start until one finishes. This is usually desired (backpressure)
  but should be configurable.
- **Job directory naming**: Use job ID as the subdirectory name to avoid filename
  conflicts between concurrent jobs downloading to the same output directory.
