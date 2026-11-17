# Placeholder & Stub Patterns — Production Audit Reference

Patterns found in real codebases that were rejected by users as "not production ready."
Every pattern here was once deployed code that *looked* like a real function but was
actually a stub.

## Stub Return Strings

The most insidious pattern — functions with real dispatchers, real parameters, real
logging, but the body is a string pretending to be a result:

```python
# BAD — looks real, does nothing
def exploit_wep(self, network):
    print("WEP exploitation would be implemented here")
    return "WEP exploitation placeholder"

# BAD — same pattern, different phrasing
def exploit_wps(self, network):
    print("WPS exploitation would be implemented here")
    return "WPS exploitation placeholder"
```

Detection: grep for these phrases:
```
grep -rn "would be implemented here" --include="*.py" .
grep -rn "placeholder" --include="*.py" .
grep -rn "not yet implemented" --include="*.py" .
grep -rn "not implemented" --include="*.py" .
grep -rn "implement later" --include="*.py" .
grep -n "pass" $(grep -rl "^def .*:" --include="*.py" .) | grep "^\s*pass$" | head -20
```

## NotImplementedError Stubs

```python
# BAD — dead function
def intercept_sms(self):
    raise NotImplementedError("SMS interception not supported yet")
```

Detection: `grep -rn "NotImplementedError" --include="*.py" .`

## Empty init.py Next to __init__.py

Generated projects often have both `init.py` (no underscores) and `__init__.py`
(double underscores). The former is dead code:

```
src/core/init.py          ← orphan, delete
src/core/__init__.py      ← real package marker
```

Detection: `find . -name 'init.py'` (files named exactly `init.py`)

## Duplicate Module Trees

Same module defined in both root and src/ — one version is inferior:

```
core/enhanced_scythe.py       ← inferior copy (no duplicate-handler guard)
utils/logger.py               ← inferior copy (adds handlers on every call)
src/core/enhanced_scythe.py   ← real version
src/utils/logger.py           ← real version
```

Detection: compare `ls core/` with `ls src/core/` — same filenames = likely duplicate.

## Hardcoded Interface Lists

```python
# BAD — static fallback, no real detection
common_interfaces = ["wlan0", "wlan1", "wlp2s0"]
for iface in common_interfaces:
    self.interface_combo.addItem(iface)
```

Fix: detect real interfaces via `/sys/class/net` or `iw dev`:

```python
net_dir = Path("/sys/class/net")
ifaces = [d.name for d in net_dir.iterdir()
          if d.name.startswith("wl") or (d / "wireless").is_dir()]
```

## Dict Key-Value Confusion

A subtle bug where the code treats a dict key as a value field. The BSSID is the
outer key of the networks dict, but the attack methods try to access
`network['bssid']`:

```python
# BAD — network['bssid'] doesn't exist; BSSID is the dict key
networks = {"AA:BB:CC:DD:EE:FF": {"ssid": "MyWiFi", "channel": "6"}}

def auto_exploit(self, bssid):
    network = self.networks[bssid]
    result = self.pmkid_attack(network)   # network['bssid'] → KeyError!

def pmkid_attack(self, network):
    cmd = f"... --filterlist={network['bssid']}"  # BOOM
```

Fix: either pass the BSSID separately, or include it as a redundant field in the
value struct (`"bssid": bssid`). The second approach is defensive — any downstream
code can access `network['bssid']` without needing the outer key.

## Fake Pip Package in requirements.txt

A `requirements.txt` that lists a package that exists ONLY as an npm package but
is listed as a pip dependency:

```txt
# BAD — puppeteer==0.0.0 is a dummy/placeholder pip package
# The actual puppeteer lives in backend/node_service/package.json (npm)
puppeteer==0.0.0
```

Fix: remove the fake pip dependency. The actual Puppeteer is an npm package
installed via `npm install` in the node_service directory. If the Python code
needs to communicate with it, use HTTP or a subprocess wrapper — don't pretend
it's a pip package.

Detection: `grep -rn 'puppeteer==0.0.0\|selenium==0.0.0\|playwright==0.0.0' requirements*.txt`

## Async Blocking Without run_in_executor

FastAPI async endpoints that call synchronous blocking code directly will freeze
the entire event loop. This is a production defect because all concurrent requests
hang:

```python
# BAD — blocks the event loop for 30+ seconds
@app.post("/convert")
async def convert(req: Request):
    output = subprocess.run(["ffmpeg", ...])  # blocks ALL requests!
```

Fix: use `loop.run_in_executor(None, sync_fn, *args)` to push blocking work to a
thread pool, and use `loop.call_soon_threadsafe()` for progress callbacks:

```python
@app.post("/convert")
async def convert(req: Request):
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _pipeline, task_id, arg1, arg2, loop)
    return {"task_id": task_id}

def _pipeline(task_id, arg1, arg2, loop):
    def progress(pct):
        loop.call_soon_threadsafe(_update_task, task_id, progress=pct)
    # ... blocking work ...
    progress(100)
```

For yt-dlp/ffmpeg/download pipelines, ensure EVERY blocking operation
(yt-dlp extract, ffmpeg transcode, SMB upload, HTTP download) runs inside
a thread pool executor.

## Conference-Call requirements.txt

Two `requirements.txt` files at different nesting levels where neither is
authoritative and they conflict. One pins `puppeteer==0.0.0` (fake), the other
has proper `yt-dlp>=2024.1.0`:

```txt
# backend-requirements.txt (wrong)
puppeteer==0.0.0

# backend/requirements.txt (correct)
yt-dlp>=2024.1.0
fastapi>=0.109.0
```

Fix: pick one location (prefer the one closest to the code it serves). Delete
the other. Verify every listed package exists on PyPI before shipping.

## GUI Blocking Operations (Not a stub, but same class of defect)

When a GUI calls a blocking IO function on the main thread, the UI freezes.
This makes the feature unusable (= production defect):

```python
# BAD — blocks the GUI for 30+ seconds
result = self.scythe.auto_exploit(bssid)  # runs on UI thread
```

Fix: move to QThread.

## Five-Way Duplicate Script Consolidation

When 5+ scripts share 70%+ structural identical code (same imports,
same proxy/browser-bypass/downloader instantiation, same loop structure,
same error handling), consolidate into ONE:

```python
# Instead of: download_with_proxies.py + concurrent_downloader.py +
#             retry_single.py + retry_failed.py + download_borntobefuck.py
# All doing the same thing with different hardcoded URL lists:

# DO THIS:
async def download_url(url: str, output_dir: Path, quality: str = "1080p") -> bool:
    pm = ProxyManager()
    bb = BrowserBypass()
    dl = VideoDownloader(timeout=600)
    await pm.refresh_proxies()
    # ... one implementation
```

Detection: `grep -c "from downloader import" *.py` — if > 2 files import
the same module and instantiate it the same way, they're likely duplicates.

## Hardcoded Business Data in Source

Literal URL lists, SSH host strings, hardcoded IP addresses, array-of-dicts
with repetitive structure:

```python
# BAD — 18 hardcoded URLs in source code
urls = [
    "https://www.eporner.com/video-RBKiUGHicss/chubby-vr-converted/",
    "https://www.eporner.com/video-yZmXyBMMCIY/hq4k-tk-d/",
    # ... 16 more
]
```

Fix: env var with file path, or pipe URLs via stdin / args.

```python
# GOOD
urls = [line.strip() for line in sys.stdin if line.strip()]
```

## Approach-Loop Bug Pattern

When iterating over multiple approaches (direct → proxy → retry), a naive
loop can produce referential oddities that silently break the backup plan:

```python
# BAD — approaches list is static but used in inner loop
approaches = [("direct", None), ("proxy", healthy)]
for label, proxy in approaches:
    # ... does work
    # If proxy fails and next approach succeeds, the for loop still
    # has one iteration left that retries the SAME approach (label=proxy)
    # with the same proxy, not a new one.
```

Fix: make the loop dynamic — push new approaches as they become available:

```python
# GOOD
approaches: list[tuple[str, str | None]] = [("direct", None)]
if healthy:
    approaches.append(("with proxy", healthy))

for label, proxy in approaches:
    success = ... # attempt
    if success:
        return True
    # get another proxy and push to approaches list for retry
    next_proxy = await pm.get_healthy_proxy()
    if next_proxy:
        approaches.append(("retry", next_proxy))
```

## Two-Venv / Stale Venv Cleanup

When a project has both `venv/` and `.venv/`, or `backend/venv/` and
`backend/.venv/`, keep the freshest one and delete the other. Check
whether the python3 binary actually exists in the venv:

```bash
ls -la .venv/bin/python* venv/bin/python* 2>/dev/null
# If binary is missing, the venv is stale — delete it
```

Also remove orphan `requirements.txt` files at the project root when
`backend/requirements.txt` (or similar) is the canonical one.

Detection: `find . -maxdepth 2 -name 'requirements.txt' -o -name 'venv' -o -name '.venv'`


## Subprocess Without Process Group Management

```python
# BAD — terminate() only kills the shell, not the child tool
process = subprocess.Popen(cmd, shell=True)
time.sleep(30)
process.terminate()  # hcxdumptool still running!
```

Fix: use `start_new_session=True` and `os.killpg()` to kill the whole tree.
