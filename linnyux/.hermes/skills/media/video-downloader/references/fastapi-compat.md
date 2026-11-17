# FastAPI Version Compatibility — url2video Service

## Problem

The url2video service at `/home/kubuntux/video-downloader/backend/url2video.py` crashed on startup with:

```
TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
```

## Root Cause

The system had FastAPI 0.124.4, which fully removed the deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` API. The url2video service used `@app.on_event("startup")`.

## Fix

Replace the `@app.on_event("startup")` block with the modern `lifespan` context manager pattern:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup logic (moved from @app.on_event("startup"))
    yield

app = FastAPI(title="url2video", version="1.0.0", lifespan=lifespan)
```

Also remove the old `@app.on_event("startup")` function — having both causes a silent failure.

## Alternate Fix

Downgrade FastAPI to a version that still supports `on_event`:

```bash
pip install --break-system-packages 'fastapi>=0.110.0,<0.112.0'
```

This installs FastAPI 0.111.x which supports both `@app.on_event()` AND the new `lifespan` pattern.

## Important Note About the node_service

The `start.sh` at `/home/kubuntux/video-downloader/start.sh` also starts a Node.js Puppeteer service (`backend/node_service/index.js`) on port 3001. This is NOT needed for url2video — url2video uses `browser_bypass.py` directly. The node_service is only needed by the SSE-based `main.py` API on port 8000.
